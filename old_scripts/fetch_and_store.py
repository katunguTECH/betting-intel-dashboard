# fetch_and_store.py
import requests
import os
import time
from dotenv import load_dotenv
from datetime import datetime
from db_helper import insert_team, insert_fixture, insert_odds, insert_prediction

load_dotenv()

# ---------- Configuration ----------
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
ISPORTS_API_KEY = os.getenv("ISPORTS_API_KEY")  # optional, can be empty

# Correct league ID for FKF Premier League (Kenya)
KPL_LEAGUE_ID = 276
SEASON = 2024        # Free plan allows 2022-2024

# How many fixtures to fetch predictions for? (free plan: 100 req/day)
# Each prediction costs 1 request. Set to 0 to skip predictions entirely.
MAX_PREDICTIONS = 5

# Rate limit: 10 requests per minute → at least 6 seconds between calls
REQUEST_DELAY = 6    # seconds
# ----------------------------------

def fetch_fixtures():
    """Fetch all fixtures for the Kenyan Premier League season (no 'next' parameter)."""
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    params = {
        "league": KPL_LEAGUE_ID,
        "season": SEASON
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f"❌ Failed to fetch fixtures: HTTP {response.status_code}")
        print(response.text)
        return []
    
    data = response.json()
    if data.get("errors"):
        print("❌ API errors:", data["errors"])
        return []
    
    fixtures = data.get("response", [])
    print(f"✅ Retrieved {len(fixtures)} fixtures.")
    return fixtures

def process_fixtures(fixtures):
    """Insert teams and fixtures into DB; return list of fixture info."""
    fixture_map = []
    for fixture_data in fixtures:
        fixture = fixture_data["fixture"]
        home = fixture_data["teams"]["home"]
        away = fixture_data["teams"]["away"]
        
        # Insert teams (returns internal DB ID)
        home_id = insert_team(home["id"], home["name"])
        away_id = insert_team(away["id"], away["name"])
        
        # Parse the date (API returns ISO format with 'Z' = UTC)
        fixture_date = datetime.fromisoformat(fixture["date"].replace("Z", "+00:00"))
        
        # Insert fixture
        db_fixture_id = insert_fixture(
            fixture["id"],
            fixture_date,
            home_id,
            away_id,
            KPL_LEAGUE_ID,
            SEASON
        )
        
        if db_fixture_id:
            fixture_map.append({
                "db_id": db_fixture_id,
                "api_id": fixture["id"],
                "home": home["name"],
                "away": away["name"],
                "date": fixture_date
            })
            print(f"  📌 Stored: {home['name']} vs {away['name']} (DB ID: {db_fixture_id})")
        else:
            print(f"  ⚠️ Fixture {fixture['id']} already exists or could not be inserted.")
    
    return fixture_map

def fetch_odds(api_fixture_id):
    """
    Fetch odds from iSports API (optional).
    Returns None if API key missing or request fails.
    """
    if not ISPORTS_API_KEY:
        return None
    
    # Example endpoint – replace with actual iSports endpoint if available
    url = "https://api.isportsapi.com/sport/football/odds/main"
    params = {
        "api_key": ISPORTS_API_KEY,
        "matchId": api_fixture_id
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"    ⚠️ iSports odds fetch failed (HTTP {response.status_code})")
    except Exception as e:
        print(f"    ⚠️ iSports error: {e}")
    return None

def fetch_prediction(api_fixture_id):
    """Fetch prediction from API-Football (1 request per call)."""
    url = "https://v3.football.api-sports.io/predictions"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    params = {"fixture": api_fixture_id}
    response = requests.get(url, headers=headers, params=params)
    time.sleep(REQUEST_DELAY)   # Respect rate limit
    if response.status_code != 200:
        print(f"    ❌ Prediction request failed (HTTP {response.status_code})")
        return None
    data = response.json()
    if data.get("errors"):
        print(f"    ❌ Prediction API error: {data['errors']}")
        return None
    if data.get("response"):
        return data["response"][0]
    return None

def main():
    print("🚀 Starting betting data collection (free plan mode)...")
    
    # 1. Fetch fixtures (one API call)
    fixtures = fetch_fixtures()
    if not fixtures:
        print("No fixtures found. Exiting.")
        return
    
    # 2. Store teams & fixtures (no extra API calls)
    fixture_map = process_fixtures(fixtures)
    
    # 3. Optionally fetch predictions for a limited number of fixtures
    if MAX_PREDICTIONS > 0:
        print(f"\n🔮 Fetching predictions for first {MAX_PREDICTIONS} fixtures...")
        count = 0
        for f in fixture_map[:MAX_PREDICTIONS]:
            count += 1
            print(f"\n  ({count}/{MAX_PREDICTIONS}) {f['home']} vs {f['away']} (API ID: {f['api_id']})")
            
            # --- Odds (iSports) – optional, skip if no key ---
            if ISPORTS_API_KEY:
                odds_data = fetch_odds(f['api_id'])
                if odds_data and odds_data.get("data"):
                    odds = odds_data["data"]
                    home_odds = odds.get("homeOdds")
                    draw_odds = odds.get("drawOdds")
                    away_odds = odds.get("awayOdds")
                    if home_odds and draw_odds and away_odds:
                        insert_odds(f['db_id'], "iSports", home_odds, draw_odds, away_odds)
                        print("    💰 Odds stored.")
                    else:
                        print("    ⚠️ Incomplete odds data.")
                else:
                    print("    ⚠️ No odds data from iSports.")
            
            # --- Prediction (API-Football) ---
            pred = fetch_prediction(f['api_id'])
            if pred:
                predictions = pred.get("predictions", {})
                winner = predictions.get("winner", {}).get("name")
                probability = predictions.get("win_probability")
                under_over = predictions.get("under_over")
                advice = predictions.get("advice")
                if winner:
                    insert_prediction(f['db_id'], winner, probability, under_over, advice)
                    print("    🔮 Prediction stored.")
                else:
                    print("    ⚠️ No winner prediction available.")
            else:
                print("    ⚠️ No prediction data from API-Football.")
    else:
        print("\nℹ️ Skipping predictions (MAX_PREDICTIONS = 0).")
    
    print("\n✅ All done!")

if __name__ == "__main__":
    main()