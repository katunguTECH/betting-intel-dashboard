# train_advanced.py (corrected)
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
import joblib
from db_helper import get_connection

# --- Load data (club + international) ---
def load_club_data():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.date, h.name AS home_team, a.name AS away_team,
                       COALESCE(p.win_probability, 0.5) AS api_prob,
                       r.home_score, r.away_score
                FROM fixtures f
                JOIN teams h ON f.home_team_id = h.id
                JOIN teams a ON f.away_team_id = a.id
                LEFT JOIN predictions p ON f.id = p.fixture_id
                JOIN results r ON f.id = r.fixture_id
                WHERE r.is_finished = TRUE
            """)
            rows = cur.fetchall()
    df = pd.DataFrame([dict(r) for r in rows])
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['tournament'] = None   # add column for club matches (no tournament info)
    return df

def load_international_data():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT date, home_team, away_team, home_score, away_score, tournament
                FROM international_results
                WHERE home_score IS NOT NULL AND away_score IS NOT NULL
            """)
            rows = cur.fetchall()
    if not rows:
        return pd.DataFrame()
    data = [{'date': r['date'], 'home_team': r['home_team'], 'away_team': r['away_team'],
             'home_score': r['home_score'], 'away_score': r['away_score'], 'tournament': r['tournament']} for r in rows]
    df = pd.DataFrame(data)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['api_prob'] = 0.5
    return df

def compute_target(row):
    if row['home_score'] > row['away_score']:
        return 0
    elif row['away_score'] > row['home_score']:
        return 2
    else:
        return 1

# --- ELO ---
def compute_elo(df, k=32, initial_elo=1500):
    elo = {}
    home_elo_before = []
    away_elo_before = []
    for _, match in df.iterrows():
        home = match['home_team']
        away = match['away_team']
        home_elo = elo.get(home, initial_elo)
        away_elo = elo.get(away, initial_elo)
        home_elo_before.append(home_elo)
        away_elo_before.append(away_elo)
        expected_home = 1 / (1 + 10 ** ((away_elo - home_elo) / 400))
        expected_away = 1 / (1 + 10 ** ((home_elo - away_elo) / 400))
        if match['home_score'] > match['away_score']:
            actual_home = 1.0
            actual_away = 0.0
        elif match['away_score'] > match['home_score']:
            actual_home = 0.0
            actual_away = 1.0
        else:
            actual_home = 0.5
            actual_away = 0.5
        elo[home] = home_elo + k * (actual_home - expected_home)
        elo[away] = away_elo + k * (actual_away - expected_away)
    df['home_elo'] = home_elo_before
    df['away_elo'] = away_elo_before
    df['elo_diff'] = df['home_elo'] - df['away_elo']
    return df

# --- Tournament importance ---
tournament_weights = {
    'FIFA World Cup': 5,
    'UEFA Euro': 4,
    'Copa América': 4,
    'Africa Cup of Nations': 4,
    'AFC Asian Cup': 4,
    'CONCACAF Gold Cup': 4,
    'UEFA Nations League': 3,
    'Friendly': 1,
}
def get_tournament_weight(tournament):
    if tournament is None or not isinstance(tournament, str):
        return 2   # default for club matches or missing
    for key in tournament_weights:
        if key in tournament:
            return tournament_weights[key]
    return 2

# --- Days since last match ---
def add_days_since_last_match(df):
    team_last_match = {}
    days_since_home = []
    days_since_away = []
    for idx, row in df.iterrows():
        home = row['home_team']
        away = row['away_team']
        match_date = row['date']
        if home in team_last_match:
            days_since_home.append((match_date - team_last_match[home]).days)
        else:
            days_since_home.append(30)
        if away in team_last_match:
            days_since_away.append((match_date - team_last_match[away]).days)
        else:
            days_since_away.append(30)
        team_last_match[home] = match_date
        team_last_match[away] = match_date
    df['days_since_home_match'] = days_since_home
    df['days_since_away_match'] = days_since_away
    df['days_since_home_norm'] = df['days_since_home_match'].clip(0, 60) / 60
    df['days_since_away_norm'] = df['days_since_away_match'].clip(0, 60) / 60
    return df

def add_basic_features(df):
    df = df.sort_values('date').reset_index(drop=True)
    df['target'] = df.apply(compute_target, axis=1)
    df['api_prob'] = df['api_prob'].astype(float).fillna(0.5).clip(0, 1)
    # Tournament weight (handles None or missing)
    if 'tournament' in df.columns:
        df['tournament_weight'] = df['tournament'].apply(get_tournament_weight)
    else:
        df['tournament_weight'] = 2
    return df

def main():
    print("Loading data...")
    club_df = load_club_data()
    intl_df = load_international_data()
    df = pd.concat([club_df, intl_df], ignore_index=True)
    print(f"Total matches: {len(df)}")
    df = add_basic_features(df)
    print("Computing ELO...")
    df = compute_elo(df)
    print("Adding days since last match...")
    df = add_days_since_last_match(df)
    
    # Select final features (you can add more like form if desired)
    features = [
        'api_prob',
        'home_elo', 'away_elo', 'elo_diff',
        'days_since_home_norm', 'days_since_away_norm',
        'tournament_weight'
    ]
    # Ensure no missing values
    for f in features:
        df[f] = pd.to_numeric(df[f], errors='coerce').fillna(0.5)
    
    X = df[features].astype(float)
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Hyperparameter tuning (reduced grid for speed; adjust as needed)
    param_grid = {
        'n_estimators': [100, 200],
        'max_depth': [4, 6],
        'learning_rate': [0.05, 0.1],
        'subsample': [0.8, 1.0],
        'colsample_bytree': [0.8, 1.0]
    }
    xgb_model = xgb.XGBClassifier(objective='multi:softprob', num_class=3, random_state=42)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    grid = GridSearchCV(xgb_model, param_grid, cv=cv, scoring='accuracy', n_jobs=-1, verbose=1)
    grid.fit(X_train, y_train)
    
    best_model = grid.best_estimator_
    print(f"Best parameters: {grid.best_params_}")
    print(f"Best CV accuracy: {grid.best_score_:.2%}")
    test_acc = best_model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc:.2%}")
    
    # Save model and features
    joblib.dump(best_model, 'betting_model.pkl')
    with open('features.txt', 'w') as f:
        f.write(','.join(features))
    print("Model saved.")

if __name__ == "__main__":
    main()