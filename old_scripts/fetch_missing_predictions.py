# fetch_missing_predictions.py
import requests
import os
import time
from dotenv import load_dotenv
from datetime import datetime
from db_helper import get_connection, insert_prediction

load_dotenv()

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
REQUEST_DELAY = 6  # seconds between requests (10/min = 1 every 6 secs)
MAX_REQUESTS_PER_RUN = 10  # conservative limit for free plan

def get_fixtures_missing_predictions(limit=20):
    """Return fixtures that have no prediction record."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.id as fixture_db_id, f.api_football_id, 
                       t1.name as home_team, t2.name as away_team,
                       f.date
                FROM fixtures f
                JOIN teams t1 ON f.home_team_id = t1.id
                JOIN teams t2 ON f.away_team_id = t2.id
                LEFT JOIN predictions p ON f.id = p.fixture_id
                WHERE p.id IS NULL
                AND f.date < NOW() + INTERVAL '30 days'
                ORDER BY f.date ASC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def fetch_prediction(api_fixture_id, fixture_db_id):
    """Fetch and store prediction for a single fixture."""
    url = "https://v3.football.api-sports.io/predictions"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    params = {"fixture": api_fixture_id}
    
    response = requests.get(url, headers=headers, params=params)
    time.sleep(REQUEST_DELAY)  # ⏱️ Respect rate limit
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    if data.get("errors"):
        return None
    
    if not data.get("response"):
        return None
    
    pred_data = data["response"][0]
    predictions = pred_data.get("predictions", {})
    winner = predictions.get("winner", {}).get("name")
    probability = predictions.get("win_probability")
    under_over = predictions.get("under_over")
    advice = predictions.get("advice")
    
    if winner:
        insert_prediction(fixture_db_id, winner, probability, under_over, advice)
        return {"winner": winner, "probability": probability}
    return None

def main():
    """Main execution loop."""
    print("🔍 Fetching missing predictions...")
    
    fixtures = get_fixtures_missing_predictions(limit=MAX_REQUESTS_PER_RUN)
    if not fixtures:
        print("✅ All fixtures have predictions already!")
        return
    
    print(f"📊 Found {len(fixtures)} fixtures without predictions.")
    
    for i, fix in enumerate(fixtures):
        print(f"\n  ({i+1}/{len(fixtures)}) {fix['home_team']} vs {fix['away_team']}")
        result = fetch_prediction(fix['api_football_id'], fix['fixture_db_id'])
        if result:
            print(f"    ✅ Stored prediction: {result['winner']} "
                  f"({result['probability']*100:.1f}%)")
        else:
            print(f"    ⚠️ No prediction available")
    
    print("\n✅ Done!")

if __name__ == "__main__":
    main()