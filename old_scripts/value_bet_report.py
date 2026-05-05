# value_bet_report.py
from db_helper import get_connection

def calculate_expected_value(probability_decimal, odds_decimal):
    """
    EV = (Probability × Odds) − (1 − Probability)
    Positive EV = value bet.
    """
    if probability_decimal is None or odds_decimal is None:
        return None
    return (probability_decimal * odds_decimal) - (1 - probability_decimal)

def get_value_bets(min_expected_value=0.05):
    """Find all value bets where expected value exceeds threshold."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    f.id,
                    f.date,
                    h.name AS home_team,
                    a.name AS away_team,
                    p.predicted_winner,
                    p.win_probability,
                    o.bookmaker,
                    o.home_odds,
                    o.draw_odds,
                    o.away_odds
                FROM fixtures f
                JOIN teams h ON f.home_team_id = h.id
                JOIN teams a ON f.away_team_id = a.id
                JOIN predictions p ON f.id = p.fixture_id
                JOIN odds o ON f.id = o.fixture_id
                WHERE f.date > NOW()
                AND f.date <= NOW() + INTERVAL '14 days'
                AND p.win_probability IS NOT NULL
                AND o.home_odds IS NOT NULL
                ORDER BY f.date ASC, p.win_probability DESC
            """)
            
            opportunities = []
            for row in cur.fetchall():
                # Determine which team the predictor favors
                if row['predicted_winner'] == row['home_team']:
                    prob = row['win_probability']
                    odds = row['home_odds']
                elif row['predicted_winner'] == row['away_team']:
                    prob = row['win_probability']
                    odds = row['away_odds']
                else:
                    prob = None  # Draw is not our focus
                    odds = row['draw_odds']
                
                if prob and odds:
                    expected_value = calculate_expected_value(prob, odds)
                    if expected_value > min_expected_value:
                        opportunities.append({
                            'home_team': row['home_team'],
                            'away_team': row['away_team'],
                            'predicted_winner': row['predicted_winner'],
                            'probability_pct': prob * 100,
                            'bookmaker': row['bookmaker'],
                            'odds_decimal': odds,
                            'expected_value': expected_value * 100,  # as percentage
                            'match_date': row['date']
                        })
            
            return opportunities

def main():
    value_bets = get_value_bets(min_expected_value=0.05)  # 5% edge
    
    if not value_bets:
        print("📭 No value bets found.")
        return
    
    print(f"🎯 Found {len(value_bets)} value betting opportunities:")
    print("-" * 70)
    
    for vb in value_bets:
        print(f"\n⚽ {vb['home_team']} vs {vb['away_team']}")
        print(f"   📅 Date: {vb['match_date'].strftime('%Y-%m-%d %H:%M')}")
        print(f"   🔮 Predicted: {vb['predicted_winner']} to win "
              f"({vb['probability_pct']:.1f}%)")
        print(f"   📊 Bookmaker: {vb['bookmaker']}")
        print(f"   💰 Odds: {vb['odds_decimal']}")
        print(f"   📈 Expected Value: +{vb['expected_value']:.1f}%")
        print("   ✅ V A L U E   B E T !")

if __name__ == "__main__":
    main()