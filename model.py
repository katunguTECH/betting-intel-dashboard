# model.py - XGBoost Model for Football Prediction
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
import joblib
import os
from db_helper import get_connection

class FootballPredictor:
    def __init__(self):
        self.model = None
        self.accuracy = None
    
    def load_training_data(self):
        """Load historical matches with actual results from database"""
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT 
                    p.win_probability AS api_prob,
                    r.winner
                FROM results r
                JOIN fixtures f ON r.fixture_id = f.id
                LEFT JOIN predictions p ON f.id = p.fixture_id
                WHERE r.is_finished = TRUE
            """, conn)
        return df
    
    def train(self):
        df = self.load_training_data()
        if df.empty:
            print("No training data available yet. Use placeholder model.")
            return False
        
        # Prepare features: use API probability as the main feature
        df['api_prob'] = df['api_prob'].fillna(0.5)
        X = df[['api_prob']]
        y = df['winner'].map({'Home': 0, 'Draw': 1, 'Away': 2})
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.model = xgb.XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42)
        self.model.fit(X_train, y_train)
        
        self.accuracy = self.model.score(X_test, y_test)
        print(f"Model trained with accuracy: {self.accuracy:.2%}")
        return True
    
    def predict(self, api_prob):
        if self.model is None:
            # Placeholder: use simple logic (home advantage)
            return {'home': 45, 'draw': 30, 'away': 25}
        prob = self.model.predict_proba([[api_prob]])[0]
        return {'home': prob[0]*100, 'draw': prob[1]*100, 'away': prob[2]*100}
    
    def save(self, path='betting_model.pkl'):
        if self.model:
            joblib.dump(self.model, path)
    
    def load(self, path='betting_model.pkl'):
        if os.path.exists(path):
            self.model = joblib.load(path)
            return True
        return False