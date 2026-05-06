import asyncio
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from flashscore import FlashscoreApi
import requests
from bs4 import BeautifulSoup
import re

class FootballDataCollector:
    def __init__(self):
        self.api = FlashscoreApi()
        
    async def get_upcoming_fixtures(self, days_ahead=30):
        """Get upcoming fixtures from Flashscore"""
        fixtures = []
        try:
            # Get today's matches and upcoming matches
            today_matches = self.api.get_today_matches()
            for match in today_matches:
                match.load_content()
                fixtures.append({
                    'home_team': match.home_team_name,
                    'away_team': match.away_team_name,
                    'date': match.date,
                    'league': match.league_name,
                    'match_id': match.id
                })
            return fixtures
        except Exception as e:
            print(f"Error fetching fixtures: {e}")
            return []
    
    def get_fixtures_from_football_data(self, api_key, league_code='PL', days_ahead=14):
        """Get fixtures from Football-Data.org API (free tier)"""
        url = f"https://api.football-data.org/v4/competitions/{league_code}/matches"
        headers = {'X-Auth-Token': api_key}
        params = {
            'dateFrom': datetime.now().strftime('%Y-%m-%d'),
            'dateTo': (datetime.now() + timedelta(days=days_ahead)).strftime('%Y-%m-%d'),
            'status': 'SCHEDULED'
        }
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                matches = []
                for match in data.get('matches', []):
                    matches.append({
                        'home_team': match['homeTeam']['name'],
                        'away_team': match['awayTeam']['name'],
                        'date': match['utcDate'],
                        'league': match['competition']['name']
                    })
                return matches
            return []
        except Exception as e:
            print(f"Football-Data.org error: {e}")
            return []
    
    def get_fixtures_from_sportmonks(self, api_key):
        """Get fixtures from Sportmonks (free tier available)"""
        url = f"https://soccer.sportmonks.com/api/v3/fixtures/between/{datetime.now().strftime('%Y-%m-%d')}/{ (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')}"
        params = {'api_token': api_key, 'include': 'localTeam,visitorTeam,league'}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                matches = []
                for match in data.get('data', []):
                    matches.append({
                        'home_team': match['localTeam']['name'],
                        'away_team': match['visitorTeam']['name'],
                        'date': match['starting_at'],
                        'league': match['league']['name']
                    })
                return matches
            return []
        except Exception as e:
            print(f"Sportmonks error: {e}")
            return []