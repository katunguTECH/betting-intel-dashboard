# train_model.py
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from db_helper import get_connection

def main():
    print("Loading historical match data from database...")
    with get_connection() as conn:
        df = pd.read_sql("""
            SELECT 
                f.id,
                h.name as home,
                a.name as away,
                p.win_probability as api_prob,
                p.predicted_winner,
                r.home_score,
                r.away_score,
                CASE 
                    WHEN r.home_score > r.away_score THEN 'Home'
                    WHEN r.home_score < r.away_score THEN 'Away'
                    ELSE 'Draw'
                END as result
            FROM fixtures f
            JOIN teams h ON f.home_team_id = h.id
            JOIN teams a ON f.away_team_id = a.id
            LEFT JOIN predictions p ON f.id = p.fixture_id
            JOIN results r ON f.id = r.fixture_id
            WHERE r.is_finished = TRUE
        """, conn)

    if df.empty:
        print("No finished matches with results found. Please populate results table first.")
        return

    # Feature engineering: use API-Football's win probability as a feature
    # (If missing, default to 0.5)
    df['api_prob'] = df['api_prob'].fillna(0.5)
    features = df[['api_prob']]
    labels = df['result'].map({'Home': 0, 'Draw': 1, 'Away': 2})

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42)

    # Train model
    print("Training Random Forest classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy: {accuracy:.2f}")

    # Save model
    joblib.dump(model, 'betting_model.pkl')
    print("Model saved as 'betting_model.pkl'.")

if __name__ == "__main__":
    main()