# main.py
import json
import time
from api_football import APIFootball
from isports_api import ISportsAPI
import config

def main():
    print("🚀 Starting Kenyan Betting Intel App...")
    
    # 1. Initialize API Clients
    api_football = APIFootball()
    isports_api = ISportsAPI()
    
    # 2. Find Kenyan Premier League ID (You may need to find this first run)
    # Uncomment the block below and run once to find the ID, then hardcode it.
    # print("🔍 Searching for Kenyan Premier League ID...")
    # leagues = api_football.get_leagues(country="Kenya")
    # if leagues and leagues.get('response'):
    #     for league in leagues['response']:
    #         if 'Kenyan Premier League' in league['league']['name']:
    #             KPL_LEAGUE_ID = league['league']['id']
    #             print(f"✅ Found Kenyan Premier League: ID {KPL_LEAGUE_ID}")
    # else:
    #     print("❌ Could not find KPL. Using default ID 134605 (verify).")
    #     KPL_LEAGUE_ID = 134605
    
    # Hardcoded KPL League ID after one-time search (Double-check this number)
    KPL_LEAGUE_ID = 134605  
    SEASON = 2025
    
    # 3. Fetch Upcoming Fixtures
    print(f"\n📅 Fetching upcoming fixtures for KPL {SEASON}...")
    fixtures = api_football.get_fixtures(league=KPL_LEAGUE_ID, season=SEASON)
    
    if not fixtures or not fixtures.get('response'):
        print("❌ No upcoming fixtures found. Check League ID and Season.")
        return
    
    # Take the first fixture as an example
    first_fixture = fixtures['response'][0]['fixture']
    fixture_id = first_fixture['id']
    home_team = fixtures['response'][0]['teams']['home']['name']
    away_team = fixtures['response'][0]['teams']['away']['name']
    event_date = first_fixture['date']
    
    print(f"\n⚽ Selected Fixture: {home_team} vs {away_team} (ID: {fixture_id})")
    print(f"   Date: {event_date}\n")
    
    # 4. Fetch Odds from iSports API for this Fixture
    print("💰 Fetching pre-match odds from iSports API...")
    odds_data = isports_api.get_odds(match_id=fixture_id)
    
    if odds_data and 'data' in odds_data:
        print("\n📊 iSports Odds Data:")
        # Parse odds_data as per iSports API structure
        # This is a simplified display; adapt based on actual response
        print(json.dumps(odds_data, indent=2)[:500] + "...")  # Print first 500 chars
    else:
        print("⚠️ No odds data returned from iSports API. Check match ID and API key.")
    
    # 5. Fetch Built-in Predictions from API-Football
    print("\n🔮 Fetching API-Football's predictions...")
    predictions = api_football.get_predictions(fixture_id)
    
    if predictions and predictions.get('response'):
        pred = predictions['response'][0]
        print("\n🎯 Predicted Winner:", pred['predictions']['winner']['name'])
        print("   Win Probability:", pred['predictions']['win_probability'])
        print("   Under/Over 2.5:", pred['predictions']['under_over'])
        print("   Goals (Home/Away):", pred['predictions']['goals']['home'], "/", pred['predictions']['goals']['away'])
        print("   Advice:", pred['predictions']['advice'])
    else:
        print("⚠️ No prediction data available.")
    
    print("\n✨ App demo complete.")

if __name__ == "__main__":
    main()