# fetch_odds.py
import os
import time
from dotenv import load_dotenv
from odds_api import OddsAPIClient
from db_helper import get_connection, insert_odds

load_dotenv()

ODDS_API_KEY = os.getenv("ODDS_API_KEY")
SPORT = "soccer"  # For Kenyan Premier League, use this

def get_fixtures_missing_odds(limit=15):
    """Return fixtures that have no odds records."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.id as fixture_db_id, f.api_football_id,
                       t1.name as home_team, t2.name as away_team,
                       f.date
                FROM fixtures f
                JOIN teams t1 ON f.home_team_id = t1.id
                JOIN teams t2 ON f.away_team_id = t2.id
                LEFT JOIN odds o ON f.id = o.fixture_id
                WHERE o.id IS NULL
                AND f.date > NOW()
                ORDER BY f.date ASC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def fetch_and_store_odds(sport, regions=["eu"], markets=["h2h"]):
    """Fetch odds for upcoming events and store in database."""
    with OddsAPIClient(api_key=ODDS_API_KEY) as client:
        # Get upcoming events with odds
        events = client.get_odds(
            sport=sport,
            regions=regions,
            markets=markets,
            odds_format="decimal"
        )
        
        print(f"📊 Retrieved {len(events)} events from The Odds API")
        
        for i, event in enumerate(events):
            print(f"\n  ({i+1}/{len(events)}) {event.away_team} @ {event.home_team}")
            
            # Find fixture by mapping teams (approximate match)
            fixture_id = find_fixture_by_teams(event.home_team, event.away_team)
            if not fixture_id:
                print(f"    ⚠️ Could not find fixture for {event.home_team} vs {event.away_team}")
                continue
            
            # Store odds from each bookmaker
            for bookie_key, markets_data in event.bookmakers.items():
                for market in markets_data:
                    if market.get('key') == 'h2h':
                        outcomes = market.get('outcomes', [])
                        if len(outcomes) >= 3:
                            home_odds = next((o['price'] for o in outcomes 
                                            if o['name'] == event.home_team), None)
                            draw_odds = next((o['price'] for o in outcomes 
                                            if o['name'] == 'Draw'), None)
                            away_odds = next((o['price'] for o in outcomes 
                                            if o['name'] == event.away_team), None)
                            
                            if home_odds and draw_odds and away_odds:
                                insert_odds(fixture_id, bookie_key, 
                                           home_odds, draw_odds, away_odds)
                                print(f"    💰 Odds from {bookie_key}: "
                                      f"{home_odds} | {draw_odds} | {away_odds}")
            
            time.sleep(1)  # Small delay between events

def find_fixture_by_teams(home_team_name, away_team_name, tolerance=3):
    """Find fixture by team names with fuzzy matching."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT f.id
                FROM fixtures f
                JOIN teams h ON f.home_team_id = h.id
                JOIN teams a ON f.away_team_id = a.id
                WHERE (f.status = 'pending' OR f.status = 'in_play')
                AND f.date > NOW()
                AND (
                    (h.name ILIKE %s AND a.name ILIKE %s)
                    OR (h.name ILIKE %s AND a.name ILIKE %s)
                )
                ORDER BY ABS(EXTRACT(EPOCH FROM (f.date - NOW()))) ASC
                LIMIT 1
            """, (f'%{home_team_name}%', f'%{away_team_name}%',
                  f'%{away_team_name}%', f'%{home_team_name}%'))
            row = cur.fetchone()
            return row['id'] if row else None

if __name__ == "__main__":
    fetch_and_store_odds(SPORT)