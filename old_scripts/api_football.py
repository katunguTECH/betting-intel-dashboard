# api_football.py
import requests
from config import API_FOOTBALL_KEY
import time

class APIFootball:
    """Wrapper for the API-Football service."""
    
    def __init__(self):
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-apisports-key": API_FOOTBALL_KEY,
            "Accept": "application/json"
        }
        self.rate_limit = 100 # Requests per day for free tier monitoring

    def _make_request(self, endpoint, params=None):
        """Internal method to handle API requests and basic rate limiting."""
        # Simple rate limit check (in-memory, will reset on script restart)
        if hasattr(self, '_request_count'):
            self._request_count += 1
            if self._request_count >= self.rate_limit:
                print(f"⚠️ APPROACHING daily rate limit ({self.rate_limit}). Stopping.")
                return None
        else:
            self._request_count = 1
            print(f"📊 Request count: {self._request_count}")

        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            return None
    
    # --- Core Fetch Methods ---
    def get_leagues(self, name=None, country=None):
        """Fetch leagues, optionally filtering by name or country."""
        params = {}
        if name: params['name'] = name
        if country: params['country'] = country
        return self._make_request("leagues", params)

    def get_teams(self, league, season):
        """Fetch teams for a specific league and season."""
        params = {'league': league, 'season': season}
        return self._make_request("teams", params)

    def get_fixtures(self, league=None, season=None, team=None, date=None, last=None):
        """Fetch upcoming or past fixtures based on various parameters."""
        params = {}
        if league: params['league'] = league
        if season: params['season'] = season
        if team: params['team'] = team
        if date: params['date'] = date
        if last: params['last'] = last
        return self._make_request("fixtures", params)

    def get_odds(self, fixture, bookmaker=None, bet_type=None):
        """Fetch betting odds for a specific fixture."""
        params = {'fixture': fixture}
        if bookmaker: params['bookmaker'] = bookmaker
        if bet_type: params['bet'] = bet_type
        return self._make_request("odds", params)
    
    def get_predictions(self, fixture):
        """Fetch API-Football's own predictions for a fixture."""
        params = {'fixture': fixture}
        return self._make_request("predictions", params)