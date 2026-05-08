# fetch_results_daily.py
import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from db_helper import get_connection

load_dotenv()
API_KEY = os.getenv("API_FOOTBALL_KEY")
REQUESTS_PER_DAY = 100   # free plan limit
DELAY = 6  # seconds between requests

def get_fixtures_to_fetch(limit=100):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.id as fixture_db_id, f.api_football_id, f.date
                FROM fixtures f
                LEFT JOIN results r ON f.id = r.fixture_id
                WHERE r.id IS NULL
                  AND f.date < NOW() - INTERVAL '1 day'
                ORDER BY f.date ASC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def fetch_result(api_id):
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_KEY}
    params = {"id": api_id}
    try:
        response = requests.get(url, headers=headers, params=params)
        time.sleep(DELAY)
        if response.status_code != 200:
            return None
        data = response.json()
        if not data.get("response"):
            return None
        fixture = data["response"][0]
        goals = fixture.get("goals", {})
        home_score = goals.get("home")
        away_score = goals.get("away")
        if home_score is None or away_score is None:
            return None
        return home_score, away_score
    except Exception as e:
        print(f"Error: {e}")
        return None

def insert_result(db_id, home_score, away_score):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM results WHERE fixture_id = %s", (db_id,))
            if cur.fetchone():
                return
            winner = "Home" if home_score > away_score else "Away" if away_score > home_score else "Draw"
            cur.execute("""
                INSERT INTO results (fixture_id, home_score, away_score, winner, is_finished)
                VALUES (%s, %s, %s, %s, TRUE)
            """, (db_id, home_score, away_score, winner))
            conn.commit()

def main():
    print(f"{datetime.now()}: Starting daily result fetch")
    fixtures = get_fixtures_to_fetch(limit=REQUESTS_PER_DAY)
    if not fixtures:
        print("No fixtures missing results.")
        return
    print(f"Found {len(fixtures)} fixtures. Fetching...")
    for fix in fixtures:
        res = fetch_result(fix['api_football_id'])
        if res:
            insert_result(fix['fixture_db_id'], res[0], res[1])
            print(f"Inserted: {fix['date']} -> {res[0]}-{res[1]}")
        else:
            print(f"Failed or no result: {fix['api_football_id']}")
    print("Done.")

if __name__ == "__main__":
    main()