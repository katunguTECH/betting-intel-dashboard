from db_helper import get_connection

def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Update matches where normalized team names match (ignoring date for now)
            cur.execute("""
                UPDATE sportpesa_matches sm
                SET api_fixture_id = f.api_football_id
                FROM fixtures f
                JOIN teams h ON f.home_team_id = h.id
                JOIN teams a ON f.away_team_id = a.id
                WHERE sm.home_team_norm = h.name_normalized
                  AND sm.away_team_norm = a.name_normalized
                  AND sm.api_fixture_id IS NULL
            """)
            updated = cur.rowcount
            conn.commit()
            print(f"Linked {updated} matches using normalized names.")

if __name__ == "__main__":
    main()