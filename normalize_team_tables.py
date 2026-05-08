from db_helper import get_connection
import unicodedata

def normalize(text):
    if not text:
        return text
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    return text.lower().strip()

def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Add normalized column to teams if missing
            cur.execute("ALTER TABLE teams ADD COLUMN IF NOT EXISTS name_normalized VARCHAR(100);")
            # Update teams
            cur.execute("SELECT id, name FROM teams")
            rows = cur.fetchall()
            for row in rows:
                norm = normalize(row['name'])
                cur.execute("UPDATE teams SET name_normalized = %s WHERE id = %s", (norm, row['id']))
            # Add normalized columns to sportpesa_matches
            cur.execute("""
                ALTER TABLE sportpesa_matches ADD COLUMN IF NOT EXISTS home_team_norm VARCHAR(100);
                ALTER TABLE sportpesa_matches ADD COLUMN IF NOT EXISTS away_team_norm VARCHAR(100);
            """)
            cur.execute("SELECT match_id, home_team, away_team FROM sportpesa_matches")
            sm_rows = cur.fetchall()
            for row in sm_rows:
                home_norm = normalize(row['home_team'])
                away_norm = normalize(row['away_team'])
                cur.execute("""
                    UPDATE sportpesa_matches
                    SET home_team_norm = %s, away_team_norm = %s
                    WHERE match_id = %s
                """, (home_norm, away_norm, row['match_id']))
            conn.commit()
            print("Normalization complete.")

if __name__ == "__main__":
    main()