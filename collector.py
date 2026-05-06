# collector.py - Simplified: uses database fixtures
import pandas as pd
from db_helper import get_connection

class FootballDataCollector:
    def __init__(self):
        pass
    
    def get_upcoming_fixtures_from_db(self, league_id=None, days_ahead=14):
        """Retrieve upcoming fixtures from the database"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT 
                        f.id,
                        f.date,
                        h.name AS home_team,
                        a.name AS away_team,
                        f.league_id,
                        p.predicted_winner,
                        p.win_probability
                    FROM fixtures f
                    JOIN teams h ON f.home_team_id = h.id
                    JOIN teams a ON f.away_team_id = a.id
                    LEFT JOIN predictions p ON f.id = p.fixture_id
                    WHERE f.date > NOW()
                """
                params = []
                if league_id:
                    query += " AND f.league_id = %s"
                    params.append(league_id)
                if days_ahead:
                    query += " AND f.date < NOW() + INTERVAL '%s days'"
                    params.append(days_ahead)
                query += " ORDER BY f.date ASC"
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return [dict(row) for row in rows]