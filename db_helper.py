# db_helper.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

# Debug: print which variables are set
print("=== db_helper.py debug ===")
print("DATABASE_URL present:", bool(os.getenv("DATABASE_URL")))
print("DB_HOST present:", bool(os.getenv("DB_HOST")))

def get_connection():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        print("Using DATABASE_URL (Railway)")
        result = urllib.parse.urlparse(database_url)
        return psycopg2.connect(
            dbname=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            cursor_factory=RealDictCursor
        )
    else:
        print("Using individual DB_* variables (local fallback)")
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            cursor_factory=RealDictCursor
        )

def insert_team(api_id, name, country=None, founded=None, venue=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO teams (api_football_id, name, country, founded, venue_name)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (api_football_id) DO UPDATE
                SET name = EXCLUDED.name
                RETURNING id
            """, (api_id, name, country, founded, venue))
            result = cur.fetchone()
            conn.commit()
            return result['id']

def insert_fixture(api_id, date, home_team_id, away_team_id, league_id, season):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO fixtures (api_football_id, date, home_team_id, away_team_id, league_id, season)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (api_football_id) DO NOTHING
                RETURNING id
            """, (api_id, date, home_team_id, away_team_id, league_id, season))
            result = cur.fetchone()
            conn.commit()
            return result['id'] if result else None

def insert_odds(fixture_id, bookmaker, home_odds, draw_odds, away_odds):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO odds (fixture_id, bookmaker, home_odds, draw_odds, away_odds)
                VALUES (%s, %s, %s, %s, %s)
            """, (fixture_id, bookmaker, home_odds, draw_odds, away_odds))
            conn.commit()

def insert_prediction(fixture_id, winner, probability, under_over, advice):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO predictions (fixture_id, predicted_winner, win_probability, under_over, advice)
                VALUES (%s, %s, %s, %s, %s)
            """, (fixture_id, winner, probability, under_over, advice))
            conn.commit()