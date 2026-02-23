import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator, RegressorMixin

class BaselineRegressor:
    """
    Baseline ensemble model to capture general property value based on 
    features like sqft, beds, and baths.
    """
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()

    def fit(self, X, y):
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

class OverfitPerceptron:
    """
    A Multi-layer Perceptron designed to 'aggressively overfit' local 
    cluster data as requested by the user.
    """
    def __init__(self):
        # High depth/width and iterations to maximize fitting on small local datasets
        self.model = MLPRegressor(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            max_iter=5000,
            alpha=0.0001, # Low regularization
            random_state=42
        )
        self.scaler = StandardScaler()

    def fit(self, X, y):
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)

    def predict(self, X):
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)

class TimeTrendRegressor:
    """
    Calculates the appreciation trend over time.
    """
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)

    def fit(self, days_since_start, residuals):
        # We fit residuals from the baseline against time
        self.model.fit(days_since_start.reshape(-1, 1), residuals)

    def predict(self, days_since_start):
        return self.model.predict(days_since_start.reshape(-1, 1))
