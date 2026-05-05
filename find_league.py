# find_league.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_FOOTBALL_KEY")
print("Your API key (first 10 chars):", API_KEY[:10] if API_KEY else "NOT FOUND")

if not API_KEY:
    print("❌ API key not found. Check your .env file.")
    exit()

headers = {"x-apisports-key": API_KEY}

# Find Kenyan leagues
url_leagues = "https://v3.football.api-sports.io/leagues"
params = {"country": "Kenya"}

response = requests.get(url_leagues, headers=headers, params=params)
print(f"Status code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print("Response received.\n")
    if data.get("errors"):
        print("Errors:", data["errors"])
    leagues = data.get("response", [])
    if leagues:
        print("=== Kenyan Leagues ===")
        for league in leagues:
            print(f"ID: {league['league']['id']} - Name: {league['league']['name']}")
    else:
        print("No Kenyan leagues found. Check your API key or try a different country.")
else:
    print("Failed to fetch leagues.")