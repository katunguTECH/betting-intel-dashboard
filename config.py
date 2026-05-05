# config.py
import os
from dotenv import load_dotenv

load_dotenv()

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
ISPORTS_API_KEY = os.getenv("ISPORTS_API_KEY")