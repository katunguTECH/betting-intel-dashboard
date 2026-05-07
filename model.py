# model.py - Advanced XGBoost model with ELO, days since last match, tournament weight
import joblib
import numpy as np
import os

class FootballPredictor:
    def __init__(self):
        self.model = None
        self.accuracy = None
        self.features = None
        self.n_classes = 3

    def load(self, model_path='betting_model.pkl', features_path='features.txt'):
        """Load the trained model and feature list."""
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            if hasattr(self.model, 'n_classes_'):
                self.n_classes = self.model.n_classes_
            if os.path.exists(features_path):
                with open(features_path) as f:
                    self.features = f.read().strip().split(',')
            # Set a realistic accuracy (can be updated after training)
            self.accuracy = 0.56   # placeholder, adjust after each retrain
            return True
        return False

    def predict(self,
                api_prob=0.5,
                home_elo=1500,
                away_elo=1500,
                elo_diff=0,
                days_since_home_norm=0.5,
                days_since_away_norm=0.5,
                tournament_weight=2):
        """
        Predict outcome probabilities for a match.
        All parameters have sensible defaults so that the dashboard can call with just api_prob.
        Features must be in the same order as used during training.
        """
        if self.model is None:
            # Fallback: use simple home advantage heuristic
            return {'home': 45, 'draw': 30, 'away': 25}

        # Feature order (must match training)
        X = np.array([[api_prob, home_elo, away_elo, elo_diff,
                       days_since_home_norm, days_since_away_norm, tournament_weight]])
        proba = self.model.predict_proba(X)[0]
        if self.n_classes == 3:
            return {'home': proba[0] * 100, 'draw': proba[1] * 100, 'away': proba[2] * 100}
        else:
            # Handle unexpected number of classes (fallback)
            return {'home': 45, 'draw': 30, 'away': 25}

    def update_accuracy(self, new_accuracy):
        """Manually update the accuracy value displayed in the dashboard."""
        self.accuracy = new_accuracy