# model.py - Load trained XGBoost model
import joblib
import numpy as np
import os

class FootballPredictor:
    def __init__(self):
        self.model = None
        self.accuracy = None
        self.features = None
    
    def load(self, model_path='betting_model.pkl', features_path='features.txt'):
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            if os.path.exists(features_path):
                with open(features_path) as f:
                    self.features = f.read().strip().split(',')
            # Set a placeholder accuracy (could be computed from test set)
            self.accuracy = 0.60   # default; adjust if you have better estimate
            return True
        return False
    
    def predict(self, api_prob=0.5, h2h_home_win_rate=0.33, h2h_away_win_rate=0.33, h2h_draw_rate=0.33):
        if self.model is None:
            # fallback to simple home bias (45% home, 30% draw, 25% away)
            return {'home': 45, 'draw': 30, 'away': 25}
        # Prepare input in order of features
        # features: ['api_prob', 'h2h_home_win_rate', 'h2h_away_win_rate', 'h2h_draw_rate', 'home_advantage']
        X = np.array([[api_prob, h2h_home_win_rate, h2h_away_win_rate, h2h_draw_rate, 1.0]])
        proba = self.model.predict_proba(X)[0]
        return {'home': proba[0]*100, 'draw': proba[1]*100, 'away': proba[2]*100}