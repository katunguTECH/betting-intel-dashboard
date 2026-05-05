# test_api.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
KPL_LEAGUE_ID = 134605
SEASON = 2025

url = "https://v3.football.api-sports.io/fixtures"
headers = {"x-apisports-key": API_KEY}
params = {
    "league": KPL_LEAGUE_ID,
    "season": SEASON,
    "next": 10
}

response = requests.get(url, headers=headers, params=params)
print("Status code:", response.status_code)
print("Response JSON:", response.json())