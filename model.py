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
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            if hasattr(self.model, 'n_classes_'):
                self.n_classes = self.model.n_classes_
            if os.path.exists(features_path):
                with open(features_path) as f:
                    self.features = f.read().strip().split(',')
            self.accuracy = 0.5245  # from latest training
            return True
        return False
    
    def predict(self, api_prob=0.5, home_form=0.33, away_form=0.33,
                home_gf_avg=1.0, home_ga_avg=1.0, away_gf_avg=1.0, away_ga_avg=1.0,
                h2h_home_win_rate=0.33, h2h_away_win_rate=0.33, h2h_draw_rate=0.33):
        """
        Predict outcome probabilities. Accepts all 10 features.
        When called with only api_prob (from dashboard), defaults for others.
        """
        if self.model is None:
            return {'home': 45, 'draw': 30, 'away': 25}
        
        # Construct feature vector in the exact order expected by the model
        # Order from features.txt: ['api_prob', 'home_form', 'away_form', 'home_gf_avg', 'home_ga_avg', 'away_gf_avg', 'away_ga_avg', 'h2h_home_win_rate', 'h2h_away_win_rate', 'h2h_draw_rate']
        X = np.array([[api_prob, home_form, away_form, home_gf_avg, home_ga_avg,
                       away_gf_avg, away_ga_avg, h2h_home_win_rate, h2h_away_win_rate, h2h_draw_rate]])
        proba = self.model.predict_proba(X)[0]
        return {'home': proba[0]*100, 'draw': proba[1]*100, 'away': proba[2]*100}