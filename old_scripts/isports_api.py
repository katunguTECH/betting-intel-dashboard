# isports_api.py
import requests
from config import ISPORTS_API_KEY

class ISportsAPI:
    """Wrapper for the iSports API service, focusing on odds."""
    
    def __init__(self):
        self.base_url = "https://api.isportsapi.com/sport/football"
        # API key can be passed as a parameter or in headers, adjust to iSports docs
        self.default_params = {
            'api_key': ISPORTS_API_KEY
        }
    
    def get_odds(self, match_id=None, company_id=None):
        """Fetch main market odds (handicap, europeOdds, overUnder)."""
        endpoint = "/odds/main"
        params = self.default_params.copy()
        if match_id:
            params['matchId'] = match_id
        if company_id:
            params['companyId'] = company_id
        
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ iSports API request failed: {e}")
            return None
    
    # --- Additional methods can be added based on iSports API documentation ---
    def get_live_odds(self, match_id=None, company_id=None):
        """Fetch live in-play odds."""
        endpoint = "/odds/live"
        # Similar implementation as get_odds()
        pass