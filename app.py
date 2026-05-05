# app.py - Personal Betting Intelligence Dashboard
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from db_helper import get_connection
import os

st.set_page_config(page_title="Betting Intel", layout="wide")

# --- Debug: Show DATABASE_URL status ---
st.write("--- Debug Info ---")
st.write("DATABASE_URL present:", bool(os.getenv("DATABASE_URL")))
st.write("--- End Debug ---")

st.title("⚽ Personal Betting Intelligence Dashboard")
st.markdown("_For personal use only_")

# ---------- Helper Functions ----------
def load_upcoming_fixtures(days_ahead=14):
    """Load upcoming fixtures with predictions and odds."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        f.date,
                        h.name AS home,
                        a.name AS away,
                        p.predicted_winner,
                        p.win_probability,
                        p.advice,
                        o.bookmaker,
                        o.home_odds,
                        o.draw_odds,
                        o.away_odds
                    FROM fixtures f
                    JOIN teams h ON f.home_team_id = h.id
                    JOIN teams a ON f.away_team_id = a.id
                    LEFT JOIN predictions p ON f.id = p.fixture_id
                    LEFT JOIN odds o ON f.id = o.fixture_id
                    WHERE f.date > NOW()
                      AND f.date < NOW() + INTERVAL '%s days'
                    ORDER BY f.date ASC
                """, (days_ahead,))
                rows = cur.fetchall()
                return rows
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return []

def calculate_ev(probability, odds):
    if probability is None or odds is None:
        return None
    return (probability * odds) - (1 - probability)

# ---------- Sidebar ----------
st.sidebar.header("Filters")
days_ahead = st.sidebar.slider("Days ahead", 1, 30, 7)
show_value_only = st.sidebar.checkbox("Show only value bets", False)

# ---------- Load Data ----------
with st.spinner("Loading fixtures..."):
    fixtures = load_upcoming_fixtures(days_ahead)

if not fixtures:
    st.warning("No upcoming fixtures with predictions found. Please run `fetch_missing_predictions.py` first to populate predictions.")
    st.info("""
    **How to get predictions:**
    1. Ensure your PostgreSQL is running.
    2. Run: `python fetch_missing_predictions.py`
    3. Then refresh this page.
    """)
    st.stop()

# ---------- Process Data ----------
df = pd.DataFrame(fixtures)
df['date'] = pd.to_datetime(df['date'])
df['win_probability'] = df['win_probability'] * 100  # as percentage

# Calculate expected value for home win (example)
df['value_bet'] = df.apply(
    lambda row: calculate_ev(row['win_probability']/100, row['home_odds']) > 0.05 
    if pd.notna(row['win_probability']) and pd.notna(row['home_odds']) else False, axis=1
)

if show_value_only:
    df = df[df['value_bet'] == True]

if df.empty:
    st.info("No fixtures match the selected filters.")
    st.stop()

# ---------- Metrics ----------
col1, col2, col3 = st.columns(3)
col1.metric("Upcoming Fixtures", len(df))
col2.metric("With Predictions", df['predicted_winner'].notna().sum())
col3.metric("Value Bets Detected", df['value_bet'].sum())

# ---------- Table ----------
st.subheader("📋 Upcoming Matches")
display_df = df[['date', 'home', 'away', 'predicted_winner', 'win_probability', 'advice', 'value_bet']].copy()
display_df.columns = ['Date', 'Home', 'Away', 'Prediction', 'Confidence (%)', 'Advice', 'Value Bet?']
st.dataframe(display_df, use_container_width=True)

# ---------- Value Bets Highlight ----------
value_bets = df[df['value_bet'] == True]
if not value_bets.empty:
    st.subheader("🎯 Value Bet Opportunities")
    for _, row in value_bets.iterrows():
        st.success(f"**{row['home']} vs {row['away']}** – "
                   f"Predicted: {row['predicted_winner']} ({row['win_probability']:.0f}%) | "
                   f"Odds: {row['home_odds']} | Positive EV")

# ---------- Chart ----------
if df['win_probability'].notna().sum() > 0:
    st.subheader("📊 Prediction Confidence Distribution")
    fig = px.histogram(df.dropna(subset=['win_probability']), x='win_probability', nbins=20,
                       title="Confidence of Predictions (%)")
    st.plotly_chart(fig, use_container_width=True)