# check_db_status.py
from db_helper import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM predictions")
        pred_cnt = cur.fetchone()['cnt']
        
        cur.execute("SELECT COUNT(*) as cnt FROM odds")
        odds_cnt = cur.fetchone()['cnt']
        
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM fixtures f
            JOIN predictions p ON f.id = p.fixture_id
            LEFT JOIN odds o ON f.id = o.fixture_id
            WHERE o.id IS NULL
        """)
        missing_odds = cur.fetchone()['cnt']
        
        cur.execute("""
            SELECT f.date, h.name as home, a.name as away, 
                   p.predicted_winner, p.win_probability,
                   o.home_odds, o.bookmaker
            FROM fixtures f
            JOIN teams h ON f.home_team_id = h.id
            JOIN teams a ON f.away_team_id = a.id
            JOIN predictions p ON f.id = p.fixture_id
            LEFT JOIN odds o ON f.id = o.fixture_id
            WHERE f.date > NOW()
            LIMIT 5
        """)
        upcoming = cur.fetchall()
        
print(f"📊 Predictions: {pred_cnt}")
print(f"📊 Odds records: {odds_cnt}")
print(f"📊 Fixtures with predictions but no odds: {missing_odds}")
print("\n📅 Upcoming fixtures with predictions (first 5):")
for row in upcoming:
    print(f"  {row['date']} - {row['home']} vs {row['away']}")
    print(f"     Predicted: {row['predicted_winner']} ({row['win_probability']*100:.1f}%)")
    print(f"     Odds: {row.get('home_odds', 'MISSING')} from {row.get('bookmaker', 'N/A')}")