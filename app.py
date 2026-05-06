# app.py - Professional Betting Dashboard with XGBoost Model
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from db_helper import get_connection
from model import FootballPredictor
import os

st.set_page_config(page_title="Football Predictor Pro", layout="wide", initial_sidebar_state="expanded")

# Custom CSS (same as before)
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
    .prob-bar { height: 8px; border-radius: 4px; background: #e0e0e0; margin: 10px 0; }
    .prob-fill { height: 100%; border-radius: 4px; transition: width 0.3s ease; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'model' not in st.session_state:
    st.session_state.model = FootballPredictor()
    if not st.session_state.model.load():
        st.sidebar.warning("Model not loaded – using fallback predictions")
    else:
        st.sidebar.success("✅ Model loaded successfully")

if 'temp_fixtures' not in st.session_state:
    st.session_state.temp_fixtures = []

# Header
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
        acc = st.session_state.model.accuracy
        if acc is not None:
            st.success(f"Model loaded (accuracy: {acc:.1%})")
        else:
            st.info("Model loaded (accuracy pending)")
    else:
        st.warning("Model not trained. Run train_model_full.py locally?")
    st.markdown("---")
    st.markdown("### 🔗 Data Sources")
    st.caption("• API-Football (historical)")
    st.caption("• Manual fixture input")

# Helper functions
def load_recent_matches(days=7):
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

def load_upcoming_from_db():
    with get_connection() as conn:
        df = pd.read_sql("""
            SELECT f.date, h.name AS home, a.name AS away, p.win_probability
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
        if st.form_submit_button("Add Fixture"):
            st.session_state.temp_fixtures.append({
                'home': home_team,
                'away': away_team,
                'date': match_date,
                'api_prob': 0.5
            })
            st.success("Fixture added! Go to 'Upcoming Matches' view.")
    
    if st.session_state.temp_fixtures:
        st.markdown("### 📋 Custom Fixtures")
        for fix in st.session_state.temp_fixtures:
            st.write(f"{fix['date']} - {fix['home']} vs {fix['away']}")

elif view_mode == "Recent Matches":
    matches = load_recent_matches(days)
    if not matches:
        st.warning("No recent matches found.")
    else:
        st.markdown(f"## 📅 Recent Matches (last {days} days)")
        cols = st.columns(2)
        for idx, match in enumerate(matches):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f"""
                    <div class="match-card">
                        <h3 style="color: #333;">{match['home']} vs {match['away']}</h3>
                        <p style="color: #666;">📅 {match['date'].strftime('%Y-%m-%d %H:%M') if isinstance(match['date'], datetime) else match['date']}</p>
                    """, unsafe_allow_html=True)
                    if match.get('predicted_winner') and match.get('win_probability'):
                        prob = match['win_probability'] * 100
                        st.markdown(f"**API Prediction:** {match['predicted_winner']} ({prob:.0f}%)")
                    else:
                        st.markdown("*No API prediction available*")
                    st.markdown("</div>", unsafe_allow_html=True)

else:  # Upcoming matches (manual + any future DB fixtures)
    st.markdown("## 🔮 Upcoming Match Predictions")
    db_fixtures = load_upcoming_from_db()
    all_fixtures = db_fixtures + st.session_state.temp_fixtures
    
    if not all_fixtures:
        st.info("No upcoming fixtures. Use 'Add New Fixture' to create one.")
    else:
        cols = st.columns(2)
        for idx, match in enumerate(all_fixtures):
            with cols[idx % 2]:
                with st.container():
                    # Determine API probability (if any)
                    api_prob = match.get('win_probability', 0.5)
                    if isinstance(api_prob, float) and api_prob > 1:
                        api_prob = api_prob / 100
                    if api_prob is None:
                        api_prob = 0.5
                    # Use the model to predict outcome
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