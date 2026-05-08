import time
import sys
import os
sys.path.insert(0, os.getcwd())
from old_scripts.fetch_and_store import fetch_fixtures, process_fixtures

LEAGUES = [
    (39, "Premier League", 2024),
    (140, "La Liga", 2024),
    (135, "Serie A", 2024),
    (78, "Bundesliga", 2024),
    (61, "Ligue 1", 2024),
]

def main():
    for league_id, name, season in LEAGUES:
        print(f"Importing {name} (ID {league_id}, {season})")
        # Monkey-patch the global variables used in fetch_and_store
        import old_scripts.fetch_and_store as fetcher
        fetcher.KPL_LEAGUE_ID = league_id
        fetcher.SEASON = season
        fixtures = fetch_fixtures()
        if fixtures:
            process_fixtures(fixtures)
            print(f"  Inserted {len(fixtures)} fixtures.")
        else:
            print(f"  No fixtures found (maybe check league ID).")
        time.sleep(2)

if __name__ == "__main__":
    main()