# fetch_all_leagues.py
import os
import time
import sys
from dotenv import load_dotenv

load_dotenv()

# Ensure the current directory is in path for imports
sys.path.insert(0, os.getcwd())

# Import the necessary functions from old_scripts
import old_scripts.fetch_and_store as fetcher
import old_scripts.fetch_missing_predictions as predictor

# List of leagues to fetch (id, name, season) – using 2024 because free plan only allows up to 2024
LEAGUES = [
    {"id": 39, "name": "Premier League", "season": 2024},
    {"id": 140, "name": "La Liga", "season": 2024},
    {"id": 135, "name": "Serie A", "season": 2024},
    {"id": 78, "name": "Bundesliga", "season": 2024},
    {"id": 61, "name": "Ligue 1", "season": 2024},
]

def fetch_and_process_league(league_id, league_name, season):
    """Fetch fixtures for a single league and insert into DB."""
    print(f"\n📌 Processing {league_name} (ID {league_id}, season {season})")
    # Override the global constants in fetch_and_store module
    fetcher.KPL_LEAGUE_ID = league_id
    fetcher.SEASON = season
    # Re-import the functions to ensure they see the new globals? Actually they read the globals at call time, so it's fine.
    fixtures = fetcher.fetch_fixtures()
    if not fixtures:
        print(f"   ⚠️ No fixtures found")
        return 0
    fixture_map = fetcher.process_fixtures(fixtures)
    print(f"   ✅ Inserted {len(fixture_map)} fixtures")
    return len(fixture_map)

def main():
    print("🚀 Multi‑league data import started")
    print(f"Using DATABASE_URL: {'present' if os.getenv('DATABASE_URL') else 'missing'}")
    
    total_fixtures = 0
    for league in LEAGUES:
        total_fixtures += fetch_and_process_league(league["id"], league["name"], league["season"])
        time.sleep(2)  # Small delay between leagues to avoid rate limiting
    
    print(f"\n✅ Imported {total_fixtures} fixtures across all leagues.")
    
    # Now fetch predictions for missing fixtures (respecting rate limits)
    print("\n🔮 Fetching missing predictions for all leagues...")
    # Run the main function from fetch_missing_predictions.py
    # Ensure it uses the same DB connection (already configured via db_helper)
    predictor.main()

if __name__ == "__main__":
    main()