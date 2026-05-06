import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
from datetime import datetime, timedelta

class FootballPredictor:
    def __init__(self):
        self.model = None
        self.team_encoder = LabelEncoder()
        
    def engineer_features(self, df):
        """Convert raw match data into features for the model"""
        features = []
        
        for idx, row in df.iterrows():
            # Team form features
            home_form = self.calculate_team_form(row['home_team'], df, row['date'], is_home=True)
            away_form = self.calculate_team_form(row['away_team'], df, row['date'], is_home=False)
            
            # Head-to-head features
            h2h_wins = self.get_h2h_stats(row['home_team'], row['away_team'], df, row['date'])
            
            # Home advantage feature
            home_advantage = 1.3 if row['is_home'] else 1.0
            
            features.append({
                'home_team': row['home_team'],
                'away_team': row['away_team'],
                'home_form': home_form,
                'away_form': away_form,
                'h2h_home_wins': h2h_wins['home_wins'],
                'h2h_away_wins': h2h_wins['away_wins'],
                'h2h_draws': h2h_wins['draws'],
                'home_advantage': home_advantage,
                'home_goals_avg': row.get('home_goals_avg', 0),
                'away_goals_avg': row.get('away_goals_avg', 0)
            })
        
        return pd.DataFrame(features)
    
    def calculate_team_form(self, team, df, current_date, is_home):
        """Calculate team form based on last 5 matches"""
        past_matches = df[(df['date'] < current_date) & 
                         ((df['home_team'] == team) | (df['away_team'] == team))]
        past_matches = past_matches.tail(5)
        
        if len(past_matches) == 0:
            return 0.5
        
        points = 0
        for _, match in past_matches.iterrows():
            if match['home_team'] == team:
                if match['winner'] == 'home':
                    points += 3
                elif match['winner'] == 'draw':
                    points += 1
            else:
                if match['winner'] == 'away':
                    points += 3
                elif match['winner'] == 'draw':
                    points += 1
        return points / (len(past_matches) * 3)
    
    def get_h2h_stats(self, home_team, away_team, df, current_date):
        """Get head-to-head statistics"""
        h2h_matches = df[(df['date'] < current_date) & 
                         ((df['home_team'] == home_team) & (df['away_team'] == away_team)) |
                         ((df['home_team'] == away_team) & (df['away_team'] == home_team))]
        
        stats = {'home_wins': 0, 'away_wins': 0, 'draws': 0}
        for _, match in h2h_matches.iterrows():
            if match['winner'] == 'home':
                stats['home_wins'] += 1
            elif match['winner'] == 'away':
                stats['away_wins'] += 1
            else:
                stats['draws'] += 1
        
        total = max(len(h2h_matches), 1)
        return {
            'home_wins': stats['home_wins'] / total,
            'away_wins': stats['away_wins'] / total,
            'draws': stats['draws'] / total
        }
    
    def train_model(self, training_data):
        """Train XGBoost model on historical match data"""
        # Prepare features
        features = self.engineer_features(training_data)
        X = features[['home_form', 'away_form', 'h2h_home_wins', 'h2h_away_wins', 
                    'h2h_draws', 'home_advantage', 'home_goals_avg', 'away_goals_avg']]
        
        # Encode targets (results)
        target_mapping = {'home': 0, 'draw': 1, 'away': 2}
        y = training_data['winner'].map(target_mapping).values
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train XGBoost classifier
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            objective='multi:softprob',
            random_state=42
        )
        self.model.fit(X_train, y_train)
        
        # Evaluate accuracy
        accuracy = self.model.score(X_test, y_test)
        print(f"Model accuracy: {accuracy:.2%}")
        
        return accuracy
    
    def predict_match(self, home_team, away_team, recent_df):
        """Predict outcome for a single match"""
        if self.model is None:
            return {'home': 0.33, 'draw': 0.33, 'away': 0.33}
        
        # Create a temporary DataFrame for this match
        match_data = pd.DataFrame([{
            'home_team': home_team,
            'away_team': away_team,
            'date': datetime.now(),
            'is_home': True
        }])
        
        features = self.engineer_features(match_data)
        X = features[['home_form', 'away_form', 'h2h_home_wins', 'h2h_away_wins', 
                    'h2h_draws', 'home_advantage', 'home_goals_avg', 'away_goals_avg']]
        
        # Get probabilities
        probabilities = self.model.predict_proba(X)[0]
        
        return {
            'home': round(probabilities[0] * 100, 1),
            'draw': round(probabilities[1] * 100, 1),
            'away': round(probabilities[2] * 100, 1)
        }
    
    def save_model(self, filepath='betting_model.pkl'):
        """Save the trained model"""
        joblib.dump(self.model, filepath)
        print(f"Model saved to {filepath}")
    
    def load_model(self, filepath='betting_model.pkl'):
        """Load a trained model"""
        self.model = joblib.load(filepath)
        print("Model loaded successfully")