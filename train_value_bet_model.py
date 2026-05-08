# train_value_bet_model.py
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
import joblib
from db_helper import get_connection

def load_training_data():
    query = """
    SELECT 
        o.home_odds,
        o.draw_odds,
        o.away_odds,
        r.home_score,
        r.away_score,
        CASE 
            WHEN r.home_score > r.away_score THEN 0
            WHEN r.away_score > r.home_score THEN 2
            ELSE 1
        END AS target
    FROM sportpesa_odds_history o
    JOIN sportpesa_matches m ON o.match_id = m.match_id
    JOIN fixtures f ON m.api_fixture_id = f.api_football_id
    JOIN results r ON f.id = r.fixture_id
    WHERE r.is_finished = TRUE
      AND o.home_odds IS NOT NULL
    """
    with get_connection() as conn:
        df = pd.read_sql(query, conn)
    return df

def engineer_features(df):
    df['home_implied'] = 1 / df['home_odds']
    df['draw_implied'] = 1 / df['draw_odds']
    df['away_implied'] = 1 / df['away_odds']
    df['total_implied'] = df['home_implied'] + df['draw_implied'] + df['away_implied']
    df['home_true'] = df['home_implied'] / df['total_implied']
    df['draw_true'] = df['draw_implied'] / df['total_implied']
    df['away_true'] = df['away_implied'] / df['total_implied']
    return df

def main():
    df = load_training_data()
    if df.empty:
        print("No training data. Ensure:")
        print("1. You have scraped SportPesa odds (sportpesa_odds_history).")
        print("2. sportpesa_matches.api_fixture_id is linked to fixtures.api_football_id.")
        print("3. The linked fixtures have results in the results table.")
        return
    df = engineer_features(df)
    features = ['home_true', 'draw_true', 'away_true']
    X = df[features]
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = xgb.XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.1,
                              objective='multi:softprob', num_class=3)
    model.fit(X_train, y_train)
    acc = model.score(X_test, y_test)
    print(f"Model accuracy on test set: {acc:.2%}")
    joblib.dump(model, 'value_bet_model.pkl')
    print("Model saved as value_bet_model.pkl")

if __name__ == "__main__":
    main()