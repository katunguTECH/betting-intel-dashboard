# db_helper.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

def get_connection():
    """Return a database connection using DATABASE_URL or individual params."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
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
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            cursor_factory=RealDictCursor
        )

def insert_team(api_id, name, country=None, founded=None, venue=None):
    """Insert a team if not exists, return its internal ID."""
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
    """Insert a fixture if not exists, return its internal ID."""
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
    """Insert odds for a fixture and bookmaker."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO odds (fixture_id, bookmaker, home_odds, draw_odds, away_odds)
                VALUES (%s, %s, %s, %s, %s)
            """, (fixture_id, bookmaker, home_odds, draw_odds, away_odds))
            conn.commit()

def insert_prediction(fixture_id, winner, probability, under_over, advice):
    """Insert a prediction."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO predictions (fixture_id, predicted_winner, win_probability, under_over, advice)
                VALUES (%s, %s, %s, %s, %s)
            """, (fixture_id, winner, probability, under_over, advice))
            conn.commit()