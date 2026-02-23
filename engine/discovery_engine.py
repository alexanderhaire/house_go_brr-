import pandas as pd
import numpy as np
from datetime import datetime
import os
from engine.models import BaselineRegressor, OverfitPerceptron, TimeTrendRegressor
from engine.llm_evaluator import LLMPropertyEvaluator

class UndervaluationEngine:
    def __init__(self, data=None, data_path=None):
        if data is not None:
            self.df = data.copy()
        elif data_path is not None:
            self.df = pd.read_csv(data_path)
        else:
            raise ValueError("Must provide either data or data_path")

        self.df['date'] = pd.to_datetime(self.df['date'])
        self.start_date = self.df['date'].min()
        self.df['days_since_start'] = (self.df['date'] - self.start_date).dt.days
        
        self.baseline = BaselineRegressor()
        self.time_trend = TimeTrendRegressor()
        self.local_models = {}

    def run_pipeline(self):
        print("Starting pipeline: Training Baseline...")
        # Features for baseline: sqft, beds, baths, neighborhood
        X_baseline = self.df[['sqft', 'beds', 'baths', 'neighborhood_id']]
        y = self.df['price']
        self.baseline.fit(X_baseline, y)
        
        # Calculate Resids
        baseline_pred = self.baseline.predict(X_baseline)
        residuals = y - baseline_pred
        
        print("Training Time Trend...")
        self.time_trend.fit(self.df['days_since_start'].values, residuals)
        
        # Local Overfitting
        print("Training Local Perceptrons (Neighborhood Clusters)...")
        for nb_id in self.df['neighborhood_id'].unique():
            nb_data = self.df[self.df['neighborhood_id'] == nb_id]
            
            if len(nb_data) < 5:
                continue
            
            local_model = OverfitPerceptron()
            # Local models
            X_local = nb_data[['sqft', 'beds', 'baths', 'days_since_start']]
            y_local = nb_data['price']
            
            local_model.fit(X_local, y_local)
            self.local_models[nb_id] = local_model
            
        print("Pipeline execution complete.")

    def evaluate_candidates(self, candidates_df, top_n=10):
        """
        Evaluate a set of 'Live' candidates from the API against the trained models.
        """
        candidates = candidates_df.copy()
        candidates['date'] = pd.to_datetime(candidates['date'])
        candidates['days_since_start'] = (candidates['date'] - self.start_date).dt.days
        
        predictions = []
        for idx, row in candidates.iterrows():
            # Get baseline
            base_p = self.baseline.predict(row[['sqft', 'beds', 'baths', 'neighborhood_id']].values.reshape(1, -1))[0]
            
            # Get time adjustment
            time_p = self.time_trend.predict(np.array([row['days_since_start']]))[0]
            
            # Get local model prediction (default to baseline+time if no local cluster)
            nb_id = row['neighborhood_id']
            if nb_id in self.local_models:
                local_p = self.local_models[nb_id].predict(row[['sqft', 'beds', 'baths', 'days_since_start']].values.reshape(1, -1))[0]
                final_pred = (base_p + time_p) * 0.3 + local_p * 0.7
            else:
                final_pred = base_p + time_p
                
            predictions.append(final_pred)
            
        candidates['predicted_price'] = predictions
        
        # Financial Modeling: 100% Debt & Total Carrying Cost
        # Assume an interest rate on a 30-year fixed mortgage based on MORGAGE_INTEREST_RATE env (default 6%)
        # Mortgage math: M = P [ i(1 + i)^n ] / [ (1 + i)^n - 1 ]
        mortgage_rate = float(os.getenv("MORTGAGE_INTEREST_RATE", "0.06"))
        monthly_interest_rate = mortgage_rate / 12
        num_payments = 30 * 12
        
        # Calculate monthly mortgage payment for 100% of the listed price
        candidates['monthly_mortgage'] = candidates['price'] * (
            monthly_interest_rate * (1 + monthly_interest_rate)**num_payments
        ) / ((1 + monthly_interest_rate)**num_payments - 1)
        
        # Total carrying cost = Mortgage + HOA
        candidates['total_monthly_cost'] = candidates['monthly_mortgage'] + candidates['hoa_fee']
        
        # FIX THE FATAL ERROR: Mortgage principal builds equity, while HOA is a 100% sunk cost.
        # We only capitalize the HOA fee. Every $1/mo in HOA reduces buying power by ~$150.
        candidates['fee_capitalized_cost'] = candidates['hoa_fee'] * 150
        
        # Adjusted Fair Value = AI Predicted Value minus the Sunk Cost burden of the HOA
        candidates['fee_adjusted_value'] = candidates['predicted_price'] - candidates['fee_capitalized_cost']
        
        # Undervaluation Amount = How much True Value you get above the Listed Price
        candidates['undervaluation_amount'] = candidates['fee_adjusted_value'] - candidates['price']
        
        # Percentage margin of safety (Positive % = Good Deal)
        candidates['undervaluation_pct'] = (candidates['undervaluation_amount'] / candidates['price']) * 100
        
        # Sort to get the preliminary top N
        results = candidates.sort_values('undervaluation_pct', ascending=False)
        top_preliminary = results.head(top_n).copy()
        
        # Now apply the LLM Condition/Risk Evaluation on the top candidates
        llm = LLMPropertyEvaluator()
        
        updated_rows = []
        for idx, row in top_preliminary.iterrows():
            eval_result = llm.evaluate_property(row.to_dict())
            
            # Apply the multiplier to the predicted baseline price
            updated_predicted_price = row['predicted_price'] * eval_result['risk_multiplier']
            
            # Recalculate everything downstream
            updated_fee_adjusted = updated_predicted_price - row['fee_capitalized_cost']
            updated_underv_amt = updated_fee_adjusted - row['price']
            updated_underv_pct = (updated_underv_amt / row['price']) * 100 if row['price'] != 0 else 0
            
            row['predicted_price'] = updated_predicted_price
            row['fee_adjusted_value'] = updated_fee_adjusted
            row['undervaluation_amount'] = updated_underv_amt
            row['undervaluation_pct'] = updated_underv_pct
            row['llm_risk_multiplier'] = eval_result['risk_multiplier']
            row['llm_reasoning'] = eval_result['reasoning']
            
            updated_rows.append(row)
            
        final_results = pd.DataFrame(updated_rows)
        # Re-sort in case the LLM significantly penalized the old #1
        final_results = final_results.sort_values('undervaluation_pct', ascending=False)
        
        return final_results

    def find_undervalued_homes(self, top_n=20):
        # Compatibility wrapper for internal historical data
        latest_entries = self.df.sort_values('date').groupby('house_id').tail(1).copy()
        return self.evaluate_candidates(latest_entries, top_n=top_n)
