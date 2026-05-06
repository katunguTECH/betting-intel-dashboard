# app.py - Professional Betting Dashboard (no external scraping)
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from db_helper import get_connection
from collector import FootballDataCollector
from model import FootballPredictor
import os

st.set_page_config(page_title="Football Predictor Pro", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .match-card { background: rgba(255,255,255,0.95); border-radius: 15px; padding: 20px; margin-bottom: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); transition: transform 0.3s; }
    .match-card:hover { transform: translateY(-5px); }
    .prediction-badge { display: inline-block; padding: 8px 16px; border-radius: 25px; font-weight: bold; margin: 5px; }
    .home-badge { background: linear-gradient(135deg, #667eea, #764ba2); color: white; }
    .draw-badge { background: linear-gradient(135deg, #f093fb, #f5576c); color: white; }
    .away-badge { background: linear-gradient(135deg, #4facfe, #00f2fe); color: white; }
    h1, h2, h3 { color: white !important; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'model' not in st.session_state:
    st.session_state.model = FootballPredictor()
    if not st.session_state.model.load():
        st.session_state.model.train()
        st.session_state.model.save()

# Title
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.title("⚽ Football Predictor Pro")
    st.markdown("<p style='text-align: center; color: white;'>AI-powered predictions using XGBoost</p>", unsafe_allow_html=True)

# Sidebar controls
with st.sidebar:
    st.markdown("## 🔧 Controls")
    view_mode = st.radio("View Mode", ["Recent Matches", "Upcoming Matches (manual input)", "Add New Fixture"])
    days = st.slider("Days range", 1, 60, 7)
    st.markdown("---")
    st.markdown("### 📊 Model Status")
    if st.session_state.model.model:
        st.success(f"Model loaded (accuracy: {st.session_state.model.accuracy:.1%})")
    else:
        st.warning("Model not trained. Add results to train.")
    st.markdown("---")
    st.markdown("### 🔗 Data Sources")
    st.caption("• API-Football (historical)")
    st.caption("• Manual fixture input")

# Helper to load fixtures
def load_fixtures_from_db(mode="recent", league_id=None, days=7):
    collector = FootballDataCollector()
    if mode == "recent":
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT f.date, h.name AS home, a.name AS away, p.predicted_winner, p.win_probability
                FROM fixtures f
                JOIN teams h ON f.home_team_id = h.id
                JOIN teams a ON f.away_team_id = a.id
                LEFT JOIN predictions p ON f.id = p.fixture_id
                WHERE f.date > NOW() - INTERVAL '%s days' AND f.date <= NOW()
                ORDER BY f.date DESC
            """, conn, params=(days,))
            return df.to_dict('records')
    else:
        # upcoming matches from database (if any)
        with get_connection() as conn:
            df = pd.read_sql("""
                SELECT f.date, h.name AS home, a.name AS away, p.predicted_winner, p.win_probability
                FROM fixtures f
                JOIN teams h ON f.home_team_id = h.id
                JOIN teams a ON f.away_team_id = a.id
                LEFT JOIN predictions p ON f.id = p.fixture_id
                WHERE f.date > NOW()
                ORDER BY f.date ASC
                LIMIT 20
            """, conn)
            return df.to_dict('records')

# Main content
if view_mode == "Add New Fixture":
    st.markdown("---")
    st.markdown("## ➕ Add a Custom Fixture")
    with st.form("new_fixture"):
        col1, col2 = st.columns(2)
        with col1:
            home_team = st.text_input("Home Team")
        with col2:
            away_team = st.text_input("Away Team")
        match_date = st.date_input("Match Date", datetime.now())
        if st.form_submit_button("Add Fixture (for prediction only)"):
            # Store in session state as temporary fixture list
            if 'temp_fixtures' not in st.session_state:
                st.session_state.temp_fixtures = []
            st.session_state.temp_fixtures.append({
                'home': home_team,
                'away': away_team,
                'date': match_date,
                'api_prob': 0.5  # default
            })
            st.success("Fixture added! Go to 'Upcoming Matches' view.")
    
    # Display temp fixtures
    if st.session_state.get('temp_fixtures'):
        st.markdown("### 📋 Custom Fixtures")
        for fix in st.session_state.temp_fixtures:
            st.write(f"{fix['date']} - {fix['home']} vs {fix['away']}")

elif view_mode == "Recent Matches":
    fixtures = load_fixtures_from_db(mode="recent", days=days)
    if not fixtures:
        st.warning("No recent matches found.")
    else:
        st.markdown(f"## 📅 Recent Matches (last {days} days)")
        cols = st.columns(2)
        for idx, match in enumerate(fixtures):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f"""
                    <div class="match-card">
                        <h3 style="color: #333;">{match['home']} vs {match['away']}</h3>
                        <p style="color: #666;">📅 {match['date'].strftime('%Y-%m-%d %H:%M')}</p>
                    """, unsafe_allow_html=True)
                    if match['predicted_winner'] and match['win_probability']:
                        prob = match['win_probability'] * 100
                        st.markdown(f"**API Prediction:** {match['predicted_winner']} ({prob:.0f}%)")
                    else:
                        st.markdown("*No API prediction available*")
                    st.markdown("</div>", unsafe_allow_html=True)

else:  # Upcoming matches (manual + any future db fixtures)
    st.markdown("## 🔮 Upcoming Match Predictions")
    # Combine DB fixtures (future) and temp fixtures
    db_fixtures = load_fixtures_from_db(mode="upcoming", days=days)
    temp_fixtures = st.session_state.get('temp_fixtures', [])
    all_fixtures = db_fixtures + temp_fixtures
    
    if not all_fixtures:
        st.info("No upcoming fixtures. Use 'Add New Fixture' to create one.")
    else:
        cols = st.columns(2)
        for idx, match in enumerate(all_fixtures):
            with cols[idx % 2]:
                with st.container():
                    api_prob = match.get('win_probability', 0.5) if isinstance(match, dict) else 0.5
                    if isinstance(api_prob, float) and api_prob > 1:
                        api_prob = api_prob / 100
                    pred = st.session_state.model.predict(api_prob)
                    max_key = max(pred, key=pred.get)
                    badge_class = "home-badge" if max_key == 'home' else ("draw-badge" if max_key == 'draw' else "away-badge")
                    
                    st.markdown(f"""
                    <div class="match-card">
                        <h3 style="color: #333;">{match['home']} vs {match['away']}</h3>
                        <p style="color: #666;">📅 {match['date'] if 'date' in match else 'TBD'}</p>
                        <div class="prob-bar"><div class="prob-fill" style="width: {pred['home']}%; background: #667eea;"></div></div>
                        <p><strong>🏠 Home win:</strong> {pred['home']:.1f}%</p>
                        <div class="prob-bar"><div class="prob-fill" style="width: {pred['draw']}%; background: #f093fb;"></div></div>
                        <p><strong>🤝 Draw:</strong> {pred['draw']:.1f}%</p>
                        <div class="prob-bar"><div class="prob-fill" style="width: {pred['away']}%; background: #4facfe;"></div></div>
                        <p><strong>✈️ Away win:</strong> {pred['away']:.1f}%</p>
                        <div class="prediction-badge {badge_class}">🎯 Prediction: {max_key.title()} ({pred[max_key]:.1f}%)</div>
                    </div>
                    """, unsafe_allow_html=True)