# app.py - Complete Betting Dashboard with Value Bets
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from db_helper import get_connection
from model import FootballPredictor
import os
import joblib

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
    .prob-bar { height: 8px; border-radius: 4px; background: #e0e0e0; margin: 10px 0; }
    .prob-fill { height: 100%; border-radius: 4px; transition: width 0.3s ease; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'model' not in st.session_state:
    st.session_state.model = FootballPredictor()
    if not st.session_state.model.load():
        st.sidebar.warning("Main model not loaded. Run train_combined_fixed.py first.")
    else:
        st.sidebar.success("✅ Main model loaded")

if 'temp_fixtures' not in st.session_state:
    st.session_state.temp_fixtures = []

# Header
col1, col2, col3 = st.columns([1,2,1])
with col2:
    st.title("⚽ Football Predictor Pro")
    st.markdown("<p style='text-align: center; color: white;'>AI‑powered predictions + Live odds from SportPesa</p>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 🔧 Controls")
    view_mode = st.radio("View Mode", ["Recent Matches", "Upcoming Matches (manual)", "Add New Fixture"])
    days = st.slider("Days range", 1, 60, 7)
    st.markdown("---")
    if st.session_state.model.model:
        acc = st.session_state.model.accuracy
        st.success(f"Main model loaded (accuracy: {acc:.1%})" if acc else "Main model loaded")
    else:
        st.warning("Main model not trained")
    st.markdown("---")
    st.caption("Data sources: API‑Football, Kaggle International, SportPesa odds")

# ---------- Helper Functions ----------
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

@st.cache_data(ttl=300)
def load_value_bet_model():
    if os.path.exists("value_bet_model.pkl"):
        return joblib.load("value_bet_model.pkl")
    return None

@st.cache_data(ttl=60)
def get_latest_odds():
    with get_connection() as conn:
        df = pd.read_sql("""
            SELECT DISTINCT ON (m.match_id)
                m.match_id,
                m.home_team,
                m.away_team,
                o.recorded_at,
                o.home_odds,
                o.draw_odds,
                o.away_odds,
                o.over_under_25_odds_over,
                o.over_under_25_odds_under,
                o.btts_odds_yes,
                o.btts_odds_no
            FROM sportpesa_matches m
            JOIN sportpesa_odds_history o ON m.match_id = o.match_id
            ORDER BY m.match_id, o.recorded_at DESC
        """, conn)
    return df

# ---------- Tabs ----------
tab1, tab2, tab3, tab4 = st.tabs(["📅 Recent/Upcoming", "➕ Add Fixture", "📊 Stats", "💰 Value Bets"])

# Tab 1: Recent and upcoming
with tab1:
    if view_mode == "Add New Fixture":
        st.info("Switch to 'Add Fixture' tab to manually add matches.")
    else:
        matches = load_recent_matches(days) if view_mode == "Recent Matches" else load_upcoming_from_db()
        if not matches:
            st.warning("No matches found.")
        else:
            cols = st.columns(2)
            for idx, m in enumerate(matches):
                with cols[idx % 2]:
                    st.markdown(f"""
                    <div class="match-card">
                        <h3 style="color:#333;">{m['home']} vs {m['away']}</h3>
                        <p>📅 {m['date'].strftime('%Y-%m-%d %H:%M') if isinstance(m['date'], datetime) else m['date']}</p>
                    """, unsafe_allow_html=True)
                    if 'predicted_winner' in m and m['predicted_winner']:
                        st.markdown(f"**API Prediction:** {m['predicted_winner']} ({m['win_probability']*100:.0f}%)")
                    else:
                        st.markdown("*No API prediction*")
                    st.markdown("</div>", unsafe_allow_html=True)

# Tab 2: Add custom fixture
with tab2:
    st.markdown("## ➕ Add Custom Fixture")
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
            st.success("Fixture added! Go to 'Upcoming Matches (manual)' view.")
    if st.session_state.temp_fixtures:
        st.markdown("### 📋 Custom Fixtures")
        for fix in st.session_state.temp_fixtures:
            st.write(f"{fix['date']} - {fix['home']} vs {fix['away']}")

# Tab 3: Statistics (simple)
with tab3:
    st.subheader("Prediction Confidence Distribution (historical)")
    with get_connection() as conn:
        df_conf = pd.read_sql("SELECT win_probability FROM predictions WHERE win_probability IS NOT NULL LIMIT 1000", conn)
    if not df_conf.empty:
        fig = px.histogram(df_conf, x='win_probability', nbins=20, title="API‑Football Prediction Confidence")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No prediction data available yet.")

# Tab 4: Value Bets from SportPesa
with tab4:
    st.subheader("⚡ Live Odds & Value Bets (SportPesa)")
    st.caption("Positive Expected Value (EV) indicates a potentially profitable bet based on our XGBoost model trained on odds history.")
    model_vb = load_value_bet_model()
    odds_df = get_latest_odds()
    if odds_df.empty:
        st.info("No odds data. Run the SportPesa scraper first.")
    elif model_vb is None:
        st.error("Value bet model not found. Train with train_value_bet_model.py after collecting odds and results.")
    else:
        results = []
        for _, row in odds_df.iterrows():
            # Implied probabilities with margin
            impl_home = 1 / row['home_odds']
            impl_draw = 1 / row['draw_odds']
            impl_away = 1 / row['away_odds']
            total = impl_home + impl_draw + impl_away
            # True probabilities (what the bookmaker thinks)
            true_home = impl_home / total
            true_draw = impl_draw / total
            true_away = impl_away / total
            # Model prediction
            proba = model_vb.predict_proba([[true_home, true_draw, true_away]])[0]
            ev_home = proba[0] - true_home
            ev_draw = proba[1] - true_draw
            ev_away = proba[2] - true_away
            best_ev = max(ev_home, ev_draw, ev_away)
            best_idx = [ev_home, ev_draw, ev_away].index(best_ev)
            best_market = ["Home", "Draw", "Away"][best_idx]
            advice = f"🎯 **Value Bet on {best_market}** (EV: {best_ev:.1%})" if best_ev > 0.02 else "No clear value bet"
            results.append({
                "home": row['home_team'],
                "away": row['away_team'],
                "home_odds": row['home_odds'],
                "draw_odds": row['draw_odds'],
                "away_odds": row['away_odds'],
                "model_home": proba[0],
                "model_draw": proba[1],
                "model_away": proba[2],
                "ev_home": ev_home,
                "ev_draw": ev_draw,
                "ev_away": ev_away,
                "advice": advice,
                "best_ev": best_ev
            })
        # Display matches in grid
        cols = st.columns(2)
        for idx, match in enumerate(results):
            with cols[idx % 2]:
                st.markdown(f"""
                <div style="background:#f0f2f6; border-radius:12px; padding:16px; margin-bottom:16px;">
                    <h4>{match['home']} 🆚 {match['away']}</h4>
                    <div style="display:flex; gap:12px; margin:12px 0;">
                        <div style="flex:1; text-align:center; background:white; border-radius:8px; padding:8px;">
                            <b>Home</b><br>{match['home_odds']}<br>
                            <small>Model: {match['model_home']:.1%}</small><br>
                            <span style="color:{'green' if match['ev_home']>0 else 'red'}">EV: {match['ev_home']:+.1%}</span>
                        </div>
                        <div style="flex:1; text-align:center; background:white; border-radius:8px; padding:8px;">
                            <b>Draw</b><br>{match['draw_odds']}<br>
                            <small>Model: {match['model_draw']:.1%}</small><br>
                            <span style="color:{'green' if match['ev_draw']>0 else 'red'}">EV: {match['ev_draw']:+.1%}</span>
                        </div>
                        <div style="flex:1; text-align:center; background:white; border-radius:8px; padding:8px;">
                            <b>Away</b><br>{match['away_odds']}<br>
                            <small>Model: {match['model_away']:.1%}</small><br>
                            <span style="color:{'green' if match['ev_away']>0 else 'red'}">EV: {match['ev_away']:+.1%}</span>
                        </div>
                    </div>
                    <div style="background:#e8eaf6; border-radius:8px; padding:10px; text-align:center;">
                        {match['advice']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        # Top value bets summary
        st.subheader("🏆 Top Value Bets")
        top = sorted(results, key=lambda x: x['best_ev'], reverse=True)[:5]
        if top:
            for t in top:
                st.write(f"**{t['home']} vs {t['away']}** → {t['advice']}")
        else:
            st.info("No value bets found at this moment.")

# Footer
st.markdown("---")
st.markdown(f'<div class="footer">Data refreshes every 60 seconds | Powered by XGBoost, API‑Football, SportPesa</div>', unsafe_allow_html=True)