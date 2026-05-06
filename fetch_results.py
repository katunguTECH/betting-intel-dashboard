# fetch_results.py
import requests
import os
import time
from dotenv import load_dotenv
from db_helper import get_connection

load_dotenv()
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
REQUEST_DELAY = 6  # seconds (10 requests/min)

def get_finished_fixtures_without_results(limit=50):
    """Get fixtures that are finished but have no result stored."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.id as fixture_db_id, f.api_football_id, 
                       f.date, h.name as home, a.name as away
                FROM fixtures f
                JOIN teams h ON f.home_team_id = h.id
                JOIN teams a ON f.away_team_id = a.id
                LEFT JOIN results r ON f.id = r.fixture_id
                WHERE r.id IS NULL
                  AND f.date < NOW() - INTERVAL '1 day'
                ORDER BY f.date DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def fetch_fixture_result(api_fixture_id):
    """Fetch final score for a given fixture ID."""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    params = {"id": api_fixture_id}
    response = requests.get(url, headers=headers, params=params)
    time.sleep(REQUEST_DELAY)
    if response.status_code != 200:
        return None
    data = response.json()
    if not data.get("response"):
        return None
    fixture = data["response"][0]
    goals = fixture.get("goals", {})
    home_score = goals.get("home")
    away_score = goals.get("away")
    winner = None
    if home_score is not None and away_score is not None:
        if home_score > away_score:
            winner = fixture["teams"]["home"]["name"]
        elif away_score > home_score:
            winner = fixture["teams"]["away"]["name"]
        else:
            winner = "Draw"
    return {"home_score": home_score, "away_score": away_score, "winner": winner}

def insert_result(fixture_db_id, home_score, away_score, winner):
    """Insert result into the results table."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO results (fixture_id, home_score, away_score, winner, is_finished)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT (fixture_id) DO NOTHING
            """, (fixture_db_id, home_score, away_score, winner))
            conn.commit()

def main():
    print("Fetching finished fixtures without results...")
    fixtures = get_finished_fixtures_without_results(limit=20)  # Start small
    if not fixtures:
        print("All fixtures already have results or no completed fixtures.")
        return
    
    print(f"Found {len(fixtures)} fixtures without results.")
    for fix in fixtures:
        print(f"Processing: {fix['home']} vs {fix['away']} (API ID: {fix['api_football_id']})")
        result = fetch_fixture_result(fix['api_football_id'])
        if result and result['home_score'] is not None:
            insert_result(fix['fixture_db_id'], result['home_score'], result['away_score'], result['winner'])
            print(f"  Stored result: {result['home_score']} - {result['away_score']} ({result['winner']})")
        else:
            print("  No result available (maybe not finished yet).")
    print("Done.")

if __name__ == "__main__":
    main()