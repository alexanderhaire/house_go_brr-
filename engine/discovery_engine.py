import pandas as pd
import numpy as np
from datetime import datetime
from engine.models import BaselineRegressor, OverfitPerceptron, TimeTrendRegressor

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
        # Features for baseline: sqft, beds, baths, neighborhood, and HOA fee
        X_baseline = self.df[['sqft', 'beds', 'baths', 'neighborhood_id', 'hoa_fee']]
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
            # Local models also take HOA into account
            X_local = nb_data[['sqft', 'beds', 'baths', 'days_since_start', 'hoa_fee']]
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
            base_p = self.baseline.predict(row[['sqft', 'beds', 'baths', 'neighborhood_id', 'hoa_fee']].values.reshape(1, -1))[0]
            
            # Get time adjustment
            time_p = self.time_trend.predict(np.array([row['days_since_start']]))[0]
            
            # Get local model prediction (default to baseline+time if no local cluster)
            nb_id = row['neighborhood_id']
            if nb_id in self.local_models:
                local_p = self.local_models[nb_id].predict(row[['sqft', 'beds', 'baths', 'days_since_start', 'hoa_fee']].values.reshape(1, -1))[0]
                final_pred = (base_p + time_p) * 0.3 + local_p * 0.7
            else:
                final_pred = base_p + time_p
                
            predictions.append(final_pred)
            
        candidates['predicted_price'] = predictions
        
        # Financial Modeling: 100% Debt & Total Carrying Cost
        # Assume 6.0% interest rate on a 30-year fixed mortgage (0.06 / 12 monthly rate)
        # Based on current Feb 2026 market rates for Florida with 720+ credit score
        # Mortgage math: M = P [ i(1 + i)^n ] / [ (1 + i)^n - 1 ]
        monthly_interest_rate = 0.06 / 12
        num_payments = 30 * 12
        
        # Calculate monthly mortgage payment for 100% of the listed price
        candidates['monthly_mortgage'] = candidates['price'] * (
            monthly_interest_rate * (1 + monthly_interest_rate)**num_payments
        ) / ((1 + monthly_interest_rate)**num_payments - 1)
        
        # Total carrying cost = Mortgage + HOA
        candidates['total_monthly_cost'] = candidates['monthly_mortgage'] + candidates['hoa_fee']
        
        # Recalculate 'fee_capitalized_cost' as the total sunk carrying cost impact
        # Every $1 in total monthly cost represents ~$150 in lost buying power
        candidates['fee_capitalized_cost'] = candidates['total_monthly_cost'] * 150
        
        candidates['fee_adjusted_value'] = candidates['predicted_price'] - candidates['fee_capitalized_cost']
        
        candidates['undervaluation_amount'] = candidates['fee_adjusted_value'] - candidates['price']
        
        # FIX: Use absolute value in the denominator so that negative adjusted values don't flip the sign
        candidates['undervaluation_pct'] = (candidates['undervaluation_amount'] / candidates['fee_adjusted_value'].abs()) * 100
        
        results = candidates.sort_values('undervaluation_pct', ascending=False)
        return results.head(top_n)

    def find_undervalued_homes(self, top_n=20):
        # Compatibility wrapper for internal historical data
        latest_entries = self.df.sort_values('date').groupby('house_id').tail(1).copy()
        return self.evaluate_candidates(latest_entries, top_n=top_n)
