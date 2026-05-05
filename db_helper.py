# db_helper.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

def get_connection():
    """Return a database connection using either DATABASE_URL or individual params."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # For Railway: parse the URL
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
        # Local development
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            cursor_factory=RealDictCursor
        )