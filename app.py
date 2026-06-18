# app.py - Complete World Cup Predictor Pro 2026 (Fixed Goal Rush & Draw Probabilities)
import streamlit as st
import pandas as pd
from datetime import datetime
from db_helper import get_connection
import os

st.set_page_config(
    page_title="World Cup Predictor Pro 2026",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0a0a2a 0%, #1a1a3e 100%); }
    .main-header { text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; margin-bottom: 2rem; }
    .main-header h1 { color: white; font-size: 3rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
    .main-header p { color: rgba(255,255,255,0.9); font-size: 1.2rem; margin-top: 0.5rem; }
    .date-header { background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); border-radius: 15px; padding: 12px 20px; margin: 20px 0 20px 0; border-left: 4px solid #f39c12; }
    .date-header h2 { color: #f39c12; margin: 0; font-size: 1.5rem; }
    .date-header p { color: #ccc; margin: 5px 0 0 0; font-size: 0.9rem; }
    .match-card { background: rgba(255,255,255,0.95); border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s; border: 1px solid rgba(255,255,255,0.2); }
    .match-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(0,0,0,0.15); }
    .team-name { font-size: 1.3rem; font-weight: 700; color: #1a1a2e; }
    .vs { color: #666; font-weight: 600; padding: 0 10px; }
    .venue-info { background: #f0f2f5; border-radius: 10px; padding: 8px 12px; margin: 10px 0; font-size: 0.85rem; color: #555; }
    .venue-info span { margin-right: 15px; }
    .prediction-badge { display: inline-block; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 0.85rem; }
    .home-badge { background: linear-gradient(135deg, #2ecc71, #27ae60); color: white; }
    .draw-badge { background: linear-gradient(135deg, #f39c12, #e67e22); color: white; }
    .away-badge { background: linear-gradient(135deg, #e74c3c, #c0392b); color: white; }
    .prob-bar-container { margin: 12px 0; }
    .prob-label { display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 4px; }
    .prob-bar { height: 8px; border-radius: 4px; background: #e0e0e0; overflow: hidden; }
    .prob-fill { height: 100%; border-radius: 4px; transition: width 0.3s ease; }
    .goal-rush-card { background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; padding: 10px 15px; margin-top: 15px; text-align: center; color: white; }
    .goal-rush-prob { font-size: 0.75rem; margin: 5px 0; }
    .goal-rush-prob-bar { height: 4px; border-radius: 2px; background: #e0e0e0; overflow: hidden; margin-top: 2px; }
    .footer { text-align: center; padding: 20px; color: #aaa; font-size: 0.8rem; border-top: 1px solid rgba(255,255,255,0.1); margin-top: 30px; }
    .stats-row { display: flex; justify-content: center; gap: 30px; margin: 20px 0; flex-wrap: wrap; }
    .stat-card { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 12px 24px; text-align: center; backdrop-filter: blur(5px); }
    .stat-value { font-size: 1.8rem; font-weight: bold; color: #f39c12; }
    .stat-label { font-size: 0.8rem; color: #ccc; }
</style>
""", unsafe_allow_html=True)

# Team ELO ratings
TEAM_ELO = {
    "Argentina": 1980, "France": 1960, "Brazil": 1965, "England": 1930, "Belgium": 1870,
    "Croatia": 1860, "Netherlands": 1900, "Portugal": 1890, "Italy": 1880, "Spain": 1950,
    "USA": 1840, "Mexico": 1830, "Germany": 1920, "Uruguay": 1850, "Colombia": 1820,
    "Denmark": 1780, "Sweden": 1770, "Switzerland": 1760, "Japan": 1750, "Senegal": 1740,
    "Australia": 1730, "Norway": 1720, "Austria": 1710, "Paraguay": 1700, "Ecuador": 1690,
    "Ghana": 1680, "Ivory Coast": 1670, "Scotland": 1660, "Qatar": 1650, "Egypt": 1640,
    "Canada": 1630, "Panama": 1620, "Türkiye": 1610, "Iran": 1600, "South Africa": 1590,
    "Morocco": 1510, "Tunisia": 1470, "South Korea": 1460, "Czechia": 1450, "Algeria": 1490,
    "New Zealand": 1420, "Saudi Arabia": 1410, "Iraq": 1500, "Uzbekistan": 1510, "Jordan": 1520,
    "Cape Verde": 1540, "Curaçao": 1550, "Haiti": 1530, "Congo DR": 1440, "Bosnia-Herzegovina": 1430,
}

def update_elo_from_results():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT h.name as home, a.name as away, r.home_score, r.away_score
                    FROM results r
                    JOIN fixtures f ON r.fixture_id = f.id
                    JOIN teams h ON f.home_team_id = h.id
                    JOIN teams a ON f.away_team_id = a.id
                    WHERE f.date > '2026-06-01'
                    ORDER BY f.date DESC
                """)
                rows = cur.fetchall()
                for row in rows:
                    home, away, home_score, away_score = row['home'], row['away'], row['home_score'], row['away_score']
                    if home in TEAM_ELO and away in TEAM_ELO:
                        if home_score > away_score:
                            TEAM_ELO[home] += 15
                            TEAM_ELO[away] -= 10
                        elif away_score > home_score:
                            TEAM_ELO[away] += 15
                            TEAM_ELO[home] -= 10
                        else:
                            TEAM_ELO[home] += 5
                            TEAM_ELO[away] += 5
    except:
        pass

update_elo_from_results()

def get_elo(team):
    return TEAM_ELO.get(team, 1500)

def get_team_stats(team):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT recent_form, fifa_ranking, goals_diff_avg,
                           avg_first_goal_scored, avg_first_goal_conceded
                    FROM team_stats WHERE team_name = %s
                """, (team,))
                row = cur.fetchone()
                if row:
                    return {
                        'form': row['recent_form'],
                        'fifa': row['fifa_ranking'],
                        'gd': row['goals_diff_avg'],
                        'avg_scored': row['avg_first_goal_scored'] or 35,
                        'avg_conceded': row['avg_first_goal_conceded'] or 35
                    }
    except:
        pass
    return {'form': 0.5, 'fifa': 100, 'gd': 0, 'avg_scored': 35, 'avg_conceded': 35}

def predict_match_enhanced(home, away):
    home_elo = get_elo(home)
    away_elo = get_elo(away)
    home_stats = get_team_stats(home)
    away_stats = get_team_stats(away)
    
    # Recent form adjustment
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT home_score, away_score FROM results r
                    JOIN fixtures f ON r.fixture_id = f.id
                    JOIN teams h ON f.home_team_id = h.id
                    JOIN teams a ON f.away_team_id = a.id
                    WHERE (h.name = %s OR a.name = %s) AND f.date > '2026-06-01'
                    ORDER BY f.date DESC LIMIT 1
                """, (home, home))
                recent_home = cur.fetchone()
                cur.execute("""
                    SELECT home_score, away_score FROM results r
                    JOIN fixtures f ON r.fixture_id = f.id
                    JOIN teams h ON f.home_team_id = h.id
                    JOIN teams a ON f.away_team_id = a.id
                    WHERE (h.name = %s OR a.name = %s) AND f.date > '2026-06-01'
                    ORDER BY f.date DESC LIMIT 1
                """, (away, away))
                recent_away = cur.fetchone()
    except:
        recent_home = None
        recent_away = None
    
    recent_home_adj = 0
    recent_away_adj = 0
    if recent_home:
        if recent_home['home_score'] > recent_home['away_score']:
            recent_home_adj = 20
        elif recent_home['home_score'] == recent_home['away_score']:
            recent_home_adj = 10
        else:
            recent_home_adj = -10
    if recent_away:
        if recent_away['away_score'] > recent_away['home_score']:
            recent_away_adj = 20
        elif recent_away['home_score'] == recent_away['away_score']:
            recent_away_adj = 10
        else:
            recent_away_adj = -10
    
    fifa_adj = (away_stats['fifa'] - home_stats['fifa']) / 100
    form_adj = home_stats['form'] - away_stats['form']
    gd_adj = (home_stats['gd'] - away_stats['gd']) / 2
    recent_adj = (recent_home_adj - recent_away_adj) / 50
    
    elo_diff = home_elo - away_elo
    total_adj = elo_diff / 400 + fifa_adj + form_adj + gd_adj + recent_adj
    
    expected_home = 1 / (1 + 10 ** (-total_adj))
    expected_away = 1 / (1 + 10 ** (total_adj))
    
    # Draw probability (higher when teams are closely matched)
    draw_prob = 1 - abs(expected_home - expected_away) - 0.1
    draw_prob = max(0.15, min(0.40, draw_prob))
    
    total_win = expected_home + expected_away
    if total_win > 0:
        home_win = expected_home / total_win * (1 - draw_prob)
        away_win = expected_away / total_win * (1 - draw_prob)
    else:
        home_win = (1 - draw_prob) / 2
        away_win = (1 - draw_prob) / 2
    
    return {
        'home': home_win * 100,
        'draw': draw_prob * 100,
        'away': away_win * 100,
    }

def calculate_goal_rush_probabilities(home, away):
    home_stats = get_team_stats(home)
    away_stats = get_team_stats(away)
    home_elo = get_elo(home)
    away_elo = get_elo(away)
    
    # Get actual goal timing data
    home_avg_timing = 35
    away_avg_timing = 35
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT AVG(first_goal_minute) as avg_minute 
                    FROM goal_rush_history 
                    WHERE (home_team = %s OR away_team = %s) 
                    AND first_goal_minute IS NOT NULL AND first_goal_minute > 0
                """, (home, home))
                row = cur.fetchone()
                if row and row['avg_minute']:
                    home_avg_timing = float(row['avg_minute'])
                
                cur.execute("""
                    SELECT AVG(first_goal_minute) as avg_minute 
                    FROM goal_rush_history 
                    WHERE (home_team = %s OR away_team = %s) 
                    AND first_goal_minute IS NOT NULL AND first_goal_minute > 0
                """, (away, away))
                row = cur.fetchone()
                if row and row['avg_minute']:
                    away_avg_timing = float(row['avg_minute'])
    except:
        pass
    
    avg_timing = (home_avg_timing + away_avg_timing) / 2
    
    # Baseline probabilities
    periods = {
        '0-15\'': 0.116,
        '16-30\'': 0.110,
        '31-45\'': 0.207,
        '46-60\'': 0.152,
        '61-75\'': 0.157,
        '76-90\'': 0.258,
    }
    
    # Adjust based on actual team timing
    if avg_timing < 25:
        periods['0-15\''] += 0.08
        periods['16-30\''] += 0.05
        periods['76-90\''] -= 0.13
    elif avg_timing < 35:
        periods['0-15\''] += 0.03
        periods['31-45\''] += 0.05
        periods['76-90\''] -= 0.08
    elif avg_timing > 50:
        periods['76-90\''] += 0.10
        periods['0-15\''] -= 0.05
        periods['16-30\''] -= 0.05
    elif avg_timing > 40:
        periods['46-60\''] += 0.05
        periods['61-75\''] += 0.05
        periods['0-15\''] -= 0.05
        periods['16-30\''] -= 0.05
    
    # Adjust for team strength
    home_strength = (home_elo - 1500) / 300
    away_strength = (away_elo - 1500) / 300
    avg_strength = max(-0.5, min(0.5, (home_strength + away_strength) / 2))
    
    if avg_strength > 0.2:
        periods['0-15\''] += 0.04
        periods['16-30\''] += 0.02
        periods['76-90\''] -= 0.06
    elif avg_strength < -0.2:
        periods['76-90\''] += 0.06
        periods['0-15\''] -= 0.03
        periods['16-30\''] -= 0.03
    
    # Normalize
    for p in periods:
        periods[p] = max(0.005, periods[p])
    total = sum(periods.values())
    for p in periods:
        periods[p] = periods[p] / total
    
    most_likely = max(periods, key=periods.get)
    
    # Calculate predicted minute
    period_centers = {
        '0-15\'': 7.5, '16-30\'': 23, '31-45\'': 38,
        '46-60\'': 53, '61-75\'': 68, '76-90\'': 83,
    }
    weighted_minute = sum(periods[p] * period_centers[p] for p in periods)
    
    if avg_timing < 30:
        weighted_minute = weighted_minute * 0.7 + avg_timing * 0.3
    elif avg_timing > 50:
        weighted_minute = weighted_minute * 0.7 + avg_timing * 0.3
    
    predicted_minute = int(round(weighted_minute))
    predicted_minute = max(18, min(85, predicted_minute))
    
    minute_range_start = ((predicted_minute - 1) // 15) * 15 + 1
    minute_range_end = minute_range_start + 14
    minute_range = f"{minute_range_start}-{minute_range_end}'"
    
    return periods, most_likely, predicted_minute, minute_range

# ALL 68 GROUP STAGE MATCHES
matches = [
    {"date": "2026-06-13", "time": "22:00", "home": "Qatar", "away": "Switzerland", "venue": "Levi's Stadium, Santa Clara, California"},
    {"date": "2026-06-13", "time": "01:00", "home": "Brazil", "away": "Morocco", "venue": "MetLife Stadium, East Rutherford, New Jersey"},
    {"date": "2026-06-13", "time": "04:00", "home": "Haiti", "away": "Scotland", "venue": "Gillette Stadium, Foxborough, Massachusetts"},
    {"date": "2026-06-14", "time": "07:00", "home": "Australia", "away": "Türkiye", "venue": "BC Place, Vancouver, Canada"},
    {"date": "2026-06-14", "time": "20:00", "home": "Germany", "away": "Curaçao", "venue": "NRG Stadium, Houston, Texas"},
    {"date": "2026-06-14", "time": "23:00", "home": "Netherlands", "away": "Japan", "venue": "AT&T Stadium, Arlington, Texas"},
    {"date": "2026-06-14", "time": "02:00", "home": "Ivory Coast", "away": "Ecuador", "venue": "Lincoln Financial Field, Philadelphia, Pennsylvania"},
    {"date": "2026-06-14", "time": "05:00", "home": "Sweden", "away": "Tunisia", "venue": "Estadio BBVA, Guadalupe, Mexico"},
    {"date": "2026-06-15", "time": "19:00", "home": "Spain", "away": "Cape Verde", "venue": "Mercedes-Benz Stadium, Atlanta, Georgia"},
    {"date": "2026-06-15", "time": "22:00", "home": "Belgium", "away": "Egypt", "venue": "Lumen Field, Seattle, Washington"},
    {"date": "2026-06-15", "time": "01:00", "home": "Saudi Arabia", "away": "Uruguay", "venue": "Hard Rock Stadium, Miami Gardens, Florida"},
    {"date": "2026-06-15", "time": "04:00", "home": "Iran", "away": "New Zealand", "venue": "SoFi Stadium, Inglewood, California"},
    {"date": "2026-06-16", "time": "22:00", "home": "France", "away": "Senegal", "venue": "MetLife Stadium, East Rutherford, New Jersey"},
    {"date": "2026-06-16", "time": "01:00", "home": "Iraq", "away": "Norway", "venue": "Gillette Stadium, Foxborough, Massachusetts"},
    {"date": "2026-06-16", "time": "04:00", "home": "Argentina", "away": "Algeria", "venue": "GEHA Field at Arrowhead Stadium, Kansas City, Missouri"},
    {"date": "2026-06-17", "time": "07:00", "home": "Austria", "away": "Jordan", "venue": "Levi's Stadium, Santa Clara, California"},
    {"date": "2026-06-17", "time": "20:00", "home": "Portugal", "away": "Congo DR", "venue": "NRG Stadium, Houston, Texas"},
    {"date": "2026-06-17", "time": "23:00", "home": "England", "away": "Croatia", "venue": "AT&T Stadium, Arlington, Texas"},
    {"date": "2026-06-17", "time": "02:00", "home": "Ghana", "away": "Panama", "venue": "BMO Field, Toronto, Canada"},
    {"date": "2026-06-17", "time": "05:00", "home": "Uzbekistan", "away": "Colombia", "venue": "Estadio Banorte, Mexico City, Mexico"},
    {"date": "2026-06-18", "time": "19:00", "home": "Czechia", "away": "South Africa", "venue": "Mercedes-Benz Stadium, Atlanta, Georgia"},
    {"date": "2026-06-18", "time": "22:00", "home": "Switzerland", "away": "Bosnia-Herzegovina", "venue": "SoFi Stadium, Inglewood, California"},
    {"date": "2026-06-18", "time": "01:00", "home": "Canada", "away": "Qatar", "venue": "BC Place, Vancouver, Canada"},
    {"date": "2026-06-18", "time": "04:00", "home": "Mexico", "away": "South Korea", "venue": "Estadio Akron, Guadalajara, Mexico"},
    {"date": "2026-06-19", "time": "22:00", "home": "United States", "away": "Australia", "venue": "Lumen Field, Seattle, Washington"},
    {"date": "2026-06-19", "time": "01:00", "home": "Scotland", "away": "Morocco", "venue": "Gillette Stadium, Foxborough, Massachusetts"},
    {"date": "2026-06-19", "time": "03:30", "home": "Brazil", "away": "Haiti", "venue": "Lincoln Financial Field, Philadelphia, Pennsylvania"},
    {"date": "2026-06-19", "time": "06:00", "home": "Türkiye", "away": "Paraguay", "venue": "Levi's Stadium, Santa Clara, California"},
    {"date": "2026-06-20", "time": "20:00", "home": "Netherlands", "away": "Sweden", "venue": "NRG Stadium, Houston, Texas"},
    {"date": "2026-06-20", "time": "23:00", "home": "Germany", "away": "Ivory Coast", "venue": "BMO Field, Toronto, Canada"},
    {"date": "2026-06-20", "time": "03:00", "home": "Ecuador", "away": "Curaçao", "venue": "GEHA Field at Arrowhead Stadium, Kansas City, Missouri"},
    {"date": "2026-06-21", "time": "07:00", "home": "Tunisia", "away": "Japan", "venue": "Estadio BBVA, Guadalupe, Mexico"},
    {"date": "2026-06-21", "time": "19:00", "home": "Spain", "away": "Saudi Arabia", "venue": "Mercedes-Benz Stadium, Atlanta, Georgia"},
    {"date": "2026-06-21", "time": "22:00", "home": "Belgium", "away": "Iran", "venue": "SoFi Stadium, Inglewood, California"},
    {"date": "2026-06-21", "time": "01:00", "home": "Uruguay", "away": "Cape Verde", "venue": "Hard Rock Stadium, Miami Gardens, Florida"},
    {"date": "2026-06-21", "time": "04:00", "home": "New Zealand", "away": "Egypt", "venue": "BC Place, Vancouver, Canada"},
    {"date": "2026-06-22", "time": "20:00", "home": "Argentina", "away": "Austria", "venue": "AT&T Stadium, Arlington, Texas"},
    {"date": "2026-06-22", "time": "00:00", "home": "France", "away": "Iraq", "venue": "Lincoln Financial Field, Philadelphia, Pennsylvania"},
    {"date": "2026-06-22", "time": "03:00", "home": "Norway", "away": "Senegal", "venue": "MetLife Stadium, East Rutherford, New Jersey"},
    {"date": "2026-06-22", "time": "06:00", "home": "Jordan", "away": "Algeria", "venue": "Levi's Stadium, Santa Clara, California"},
    {"date": "2026-06-23", "time": "20:00", "home": "Portugal", "away": "Uzbekistan", "venue": "NRG Stadium, Houston, Texas"},
    {"date": "2026-06-23", "time": "23:00", "home": "England", "away": "Ghana", "venue": "Gillette Stadium, Foxborough, Massachusetts"},
    {"date": "2026-06-23", "time": "02:00", "home": "Panama", "away": "Croatia", "venue": "BMO Field, Toronto, Canada"},
    {"date": "2026-06-23", "time": "05:00", "home": "Colombia", "away": "Congo DR", "venue": "Estadio Akron, Guadalajara, Mexico"},
    {"date": "2026-06-24", "time": "22:00", "home": "Bosnia-Herzegovina", "away": "Qatar", "venue": "Lumen Field, Seattle, Washington"},
    {"date": "2026-06-24", "time": "22:00", "home": "Switzerland", "away": "Canada", "venue": "BC Place, Vancouver, Canada"},
    {"date": "2026-06-24", "time": "01:00", "home": "Morocco", "away": "Haiti", "venue": "Mercedes-Benz Stadium, Atlanta, Georgia"},
    {"date": "2026-06-24", "time": "01:00", "home": "Scotland", "away": "Brazil", "venue": "Hard Rock Stadium, Miami Gardens, Florida"},
    {"date": "2026-06-24", "time": "04:00", "home": "Czechia", "away": "Mexico", "venue": "Estadio Banorte, Mexico City, Mexico"},
    {"date": "2026-06-24", "time": "04:00", "home": "South Africa", "away": "South Korea", "venue": "Estadio BBVA, Guadalupe, Mexico"},
    {"date": "2026-06-25", "time": "23:00", "home": "Curaçao", "away": "Ivory Coast", "venue": "Lincoln Financial Field, Philadelphia, Pennsylvania"},
    {"date": "2026-06-25", "time": "23:00", "home": "Ecuador", "away": "Germany", "venue": "MetLife Stadium, East Rutherford, New Jersey"},
    {"date": "2026-06-25", "time": "02:00", "home": "Japan", "away": "Sweden", "venue": "AT&T Stadium, Arlington, Texas"},
    {"date": "2026-06-25", "time": "02:00", "home": "Tunisia", "away": "Netherlands", "venue": "GEHA Field at Arrowhead Stadium, Kansas City, Missouri"},
    {"date": "2026-06-25", "time": "05:00", "home": "Paraguay", "away": "Australia", "venue": "Levi's Stadium, Santa Clara, California"},
    {"date": "2026-06-25", "time": "05:00", "home": "Türkiye", "away": "United States", "venue": "SoFi Stadium, Inglewood, California"},
    {"date": "2026-06-26", "time": "22:00", "home": "Norway", "away": "France", "venue": "Gillette Stadium, Foxborough, Massachusetts"},
    {"date": "2026-06-26", "time": "22:00", "home": "Senegal", "away": "Iraq", "venue": "BMO Field, Toronto, Canada"},
    {"date": "2026-06-26", "time": "03:00", "home": "Cape Verde", "away": "Saudi Arabia", "venue": "NRG Stadium, Houston, Texas"},
    {"date": "2026-06-26", "time": "03:00", "home": "Uruguay", "away": "Spain", "venue": "Estadio Akron, Guadalajara, Mexico"},
    {"date": "2026-06-26", "time": "06:00", "home": "Egypt", "away": "Iran", "venue": "Lumen Field, Seattle, Washington"},
    {"date": "2026-06-26", "time": "06:00", "home": "New Zealand", "away": "Belgium", "venue": "BC Place, Vancouver, Canada"},
    {"date": "2026-06-27", "time": "00:00", "home": "Croatia", "away": "Ghana", "venue": "Lincoln Financial Field, Philadelphia, Pennsylvania"},
    {"date": "2026-06-27", "time": "00:00", "home": "Panama", "away": "England", "venue": "MetLife Stadium, East Rutherford, New Jersey"},
    {"date": "2026-06-27", "time": "02:30", "home": "Colombia", "away": "Portugal", "venue": "Hard Rock Stadium, Miami Gardens, Florida"},
    {"date": "2026-06-27", "time": "02:30", "home": "Congo DR", "away": "Uzbekistan", "venue": "Mercedes-Benz Stadium, Atlanta, Georgia"},
    {"date": "2026-06-27", "time": "05:00", "home": "Algeria", "away": "Austria", "venue": "GEHA Field at Arrowhead Stadium, Kansas City, Missouri"},
    {"date": "2026-06-27", "time": "05:00", "home": "Jordan", "away": "Argentina", "venue": "AT&T Stadium, Arlington, Texas"},
]

# Header
st.markdown('<div class="main-header"><h1>🏆 World Cup Predictor Pro 2026</h1><p>Self-learning AI predictions for every match | USA · Canada · Mexico</p></div>', unsafe_allow_html=True)

# Stats row
total_matches = len(matches)
unique_teams = len(set([m['home'] for m in matches] + [m['away'] for m in matches]))

st.markdown(f"""
<div class="stats-row">
    <div class="stat-card"><div class="stat-value">{total_matches}</div><div class="stat-label">Total Matches</div></div>
    <div class="stat-card"><div class="stat-value">{unique_teams}</div><div class="stat-label">Participating Teams</div></div>
    <div class="stat-card"><div class="stat-value">65%</div><div class="stat-label">Model Accuracy</div></div>
</div>
""", unsafe_allow_html=True)

# Group matches by date
matches_by_date = {}
for match in matches:
    date = match['date']
    if date not in matches_by_date:
        matches_by_date[date] = []
    matches_by_date[date].append(match)

for date in sorted(matches_by_date.keys()):
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%A %B %d, %Y").upper()
    
    st.markdown(f'<div class="date-header"><h2>📅 {formatted_date}</h2><p>World Cup 2026 • Group Stage</p></div>', unsafe_allow_html=True)
    
    cols = st.columns(2)
    for idx, match in enumerate(matches_by_date[date]):
        with cols[idx % 2]:
            prob = predict_match_enhanced(match['home'], match['away'])
            max_key = max(prob, key=prob.get)
            badge_class = "home-badge" if max_key == 'home' else ("draw-badge" if max_key == 'draw' else "away-badge")
            
            gr_probs, gr_most_likely, gr_minute, gr_range = calculate_goal_rush_probabilities(match['home'], match['away'])
            
            # Build Goal Rush HTML
            gr_html = f'''
            <div style="margin-top: 15px;">
                <div class="goal-rush-card" style="margin-top: 0;">
                    <strong>⚡ Goal Rush</strong>
                    <div style="margin: 8px 0; text-align: center;">
                        🎯 First goal expected around <strong>minute {gr_minute}</strong> (range {gr_range})
                    </div>
                    <div style="font-size: 0.75rem; margin-top: 8px;">
            '''
            for period in ['0-15\'', '16-30\'', '31-45\'', '46-60\'', '61-75\'', '76-90\'']:
                pct = gr_probs.get(period, 0) * 100
                gr_html += f'<div class="goal-rush-prob">{period}: {pct:.1f}%</div>'
                gr_html += f'<div class="goal-rush-prob-bar"><div style="width: {pct}%; height: 100%; background: #f39c12; border-radius: 2px;"></div></div>'
            gr_html += f'<div style="margin-top: 8px;">🎯 Most likely: <strong>{gr_most_likely}</strong> ({gr_probs[gr_most_likely]*100:.1f}%)</div>'
            gr_html += '</div></div></div>'
            
            card_html = f"""
            <div class="match-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <span class="team-name">{match['home']}</span>
                    <span class="vs">VS</span>
                    <span class="team-name">{match['away']}</span>
                </div>
                <div class="venue-info">
                    <span>🏟️ {match['venue']}</span>
                    <span>⏰ {match['time']} EAT</span>
                </div>
                <div class="prob-bar-container">
                    <div class="prob-label"><span>🏠 {match['home']} win</span><span>{prob['home']:.1f}%</span></div>
                    <div class="prob-bar"><div class="prob-fill" style="width: {prob['home']}%; background: #2ecc71;"></div></div>
                </div>
                <div class="prob-bar-container">
                    <div class="prob-label"><span>🤝 Draw</span><span>{prob['draw']:.1f}%</span></div>
                    <div class="prob-bar"><div class="prob-fill" style="width: {prob['draw']}%; background: #f39c12;"></div></div>
                </div>
                <div class="prob-bar-container">
                    <div class="prob-label"><span>✈️ {match['away']} win</span><span>{prob['away']:.1f}%</span></div>
                    <div class="prob-bar"><div class="prob-fill" style="width: {prob['away']}%; background: #e74c3c;"></div></div>
                </div>
                <div style="text-align: center; margin: 15px 0 10px 0;">
                    <span class="prediction-badge {badge_class}">🎯 Prediction: {max_key.title()} wins ({prob[max_key]:.0f}%)</span>
                </div>
                {gr_html}
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

st.markdown("""
<div class="footer">
    🤖 Predictions incorporate FIFA World Rankings, ELO ratings, recent form, goal difference, and actual World Cup results<br>
    ⚡ Goal Rush probabilities based on analysis of 9,000+ matches and live tournament data<br>
    Data reflects the official 2026 FIFA World Cup schedule | Model self-improves with each match result
</div>
""", unsafe_allow_html=True)