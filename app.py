# app.py - Professional Betting Intelligence Dashboard (Recent + Upcoming)
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from db_helper import get_connection
import os

st.set_page_config(page_title="Betting Intel", layout="wide", initial_sidebar_state="expanded")

# ---------- Custom CSS for Professional SaaS Look ----------
st.markdown("""
<style>
    /* Main background and fonts */
    .main {
        background-color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    /* Header styling */
    h1 {
        color: #1e293b;
        font-weight: 700;
        font-size: 2.2rem;
    }
    /* Metric cards */
    .metric-card {
        background: white;
        border-radius: 1rem;
        padding: 1.2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        border-left: 4px solid #3b82f6;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.25rem;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    /* Dataframe styling */
    .dataframe {
        font-family: 'Inter', monospace;
        font-size: 0.9rem;
    }
    /* Badge for value bets */
    .value-badge {
        background-color: #10b981;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 2rem;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    /* Confidence bar */
    .confidence-bar {
        background-color: #e2e8f0;
        border-radius: 1rem;
        height: 0.5rem;
        width: 100%;
        overflow: hidden;
    }
    .confidence-fill {
        background-color: #3b82f6;
        height: 100%;
        border-radius: 1rem;
    }
    /* Footer */
    .footer {
        margin-top: 3rem;
        padding: 1rem;
        text-align: center;
        font-size: 0.75rem;
        color: #94a3b8;
        border-top: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# ---------- Helper Functions ----------
@st.cache_data(ttl=300)
def load_leagues():
    """Get distinct leagues from fixtures table."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT league_id, season
                FROM fixtures
                ORDER BY league_id, season DESC
            """)
            rows = cur.fetchall()
            return [{"id": row["league_id"], "season": row["season"]} for row in rows]

@st.cache_data(ttl=60)
def load_fixtures(league_id=None, days_ahead=14, days_back=7, mode="upcoming"):
    """
    Load fixtures based on mode:
    - 'upcoming': future matches within days_ahead
    - 'recent': past matches within days_back
    - 'both': combines both (but we'll handle separately)
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                if mode == "upcoming":
                    query = """
                        SELECT 
                            f.id,
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
                    """
                    params = [days_ahead]
                else:  # recent
                    query = """
                        SELECT 
                            f.id,
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
                        WHERE f.date > NOW() - INTERVAL '%s days'
                          AND f.date <= NOW()
                        ORDER BY f.date DESC
                    """
                    params = [days_back]

                if league_id:
                    if mode == "upcoming":
                        query += " AND f.league_id = %s"
                    else:
                        # For recent, add to WHERE clause (note: there's already a WHERE)
                        query = query.replace("WHERE", f"WHERE f.league_id = %s AND ")
                        params.insert(0, league_id)  # careful: adjust ordering
                        # Actually easier: rebuild for recent with league filter
                        # I'll restructure below for clarity
                        query = """
                            SELECT 
                                f.id,
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
                            WHERE f.league_id = %s
                              AND f.date > NOW() - INTERVAL '%s days'
                              AND f.date <= NOW()
                            ORDER BY f.date DESC
                        """
                        params = [league_id, days_back]

                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                return rows
    except Exception as e:
        st.error(f"Error loading fixtures: {e}")
        return []

def calculate_ev(probability, odds):
    if probability is None or odds is None:
        return None
    return (probability * odds) - (1 - probability)

def format_confidence(prob):
    if prob is None:
        return "N/A"
    pct = prob * 100
    color = "#10b981" if pct >= 70 else "#f59e0b" if pct >= 50 else "#ef4444"
    return f'<div class="confidence-bar"><div class="confidence-fill" style="width: {pct}%; background-color: {color};"></div></div><span style="font-size:0.8rem;">{pct:.0f}%</span>'

# ---------- Sidebar ----------
st.sidebar.image("https://img.icons8.com/fluency/96/football2.png", width=60)
st.sidebar.title("Controls")

leagues = load_leagues()
league_options = {f"{row['id']}_{row['season']}": f"League {row['id']} ({row['season']})" for row in leagues}
if not league_options:
    st.error("No leagues found in database. Please run data import first.")
    st.stop()

selected_league_key = st.sidebar.selectbox("Select League", options=list(league_options.keys()), format_func=lambda x: league_options[x])
selected_league_id = int(selected_league_key.split("_")[0])

# Toggle between upcoming and recent
view_mode = st.sidebar.radio("View Mode", ["Upcoming Matches", "Recent Matches"], index=0)

if view_mode == "Upcoming Matches":
    days_ahead = st.sidebar.slider("Days ahead", 1, 60, 7)
    days_back = None
else:
    days_back = st.sidebar.slider("Days past", 1, 60, 7)
    days_ahead = None

show_value_only = st.sidebar.checkbox("🔍 Show only value bets", value=False)
st.sidebar.markdown("---")
st.sidebar.info("Data refreshes every 60 seconds. Predictions from API‑Football.")

# ---------- Load Data ----------
mode = "upcoming" if view_mode == "Upcoming Matches" else "recent"
with st.spinner("Loading matches..."):
    if mode == "upcoming":
        fixtures = load_fixtures(league_id=selected_league_id, days_ahead=days_ahead, mode="upcoming")
    else:
        fixtures = load_fixtures(league_id=selected_league_id, days_back=days_back, mode="recent")

if not fixtures:
    st.warning(f"No {view_mode.lower()} found for this league. Try adjusting the time range or import more data.")
    st.stop()

# ---------- Process Data ----------
df = pd.DataFrame(fixtures)
df['date'] = pd.to_datetime(df['date'])
df['win_probability'] = df['win_probability'] * 100
df['ev'] = df.apply(lambda row: calculate_ev(row['win_probability']/100, row['home_odds']), axis=1)
df['value_bet'] = df['ev'] > 0.05 if df['ev'].notna().any() else False

if show_value_only:
    df = df[df['value_bet'] == True]
    if df.empty:
        st.info("No value bets in this league for the selected period.")
        st.stop()

# ---------- Metrics ----------
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-value">{len(df)}</div><div class="metric-label">{view_mode[:10]}</div></div>', unsafe_allow_html=True)
with col2:
    pred_count = df['predicted_winner'].notna().sum()
    st.markdown(f'<div class="metric-card"><div class="metric-value">{pred_count}</div><div class="metric-label">With Predictions</div></div>', unsafe_allow_html=True)
with col3:
    val_count = df[df['value_bet']].shape[0]
    st.markdown(f'<div class="metric-card"><div class="metric-value">{val_count}</div><div class="metric-label">Value Bets</div></div>', unsafe_allow_html=True)
with col4:
    avg_conf = df['win_probability'].mean()
    st.markdown(f'<div class="metric-card"><div class="metric-value">{avg_conf:.0f}%</div><div class="metric-label">Avg Confidence</div></div>', unsafe_allow_html=True)

# ---------- Tabs ----------
tab1, tab2, tab3 = st.tabs(["📋 Matches", "🎯 Value Bets", "📊 Statistics"])

with tab1:
    display_df = df[['date', 'home', 'away', 'predicted_winner', 'win_probability', 'advice', 'value_bet']].copy()
    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d %H:%M')
    display_df['win_probability'] = display_df['win_probability'].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else "N/A")
    display_df['value_bet'] = display_df['value_bet'].apply(lambda x: '<span class="value-badge">VALUE</span>' if x else "")
    display_df.columns = ['Date', 'Home', 'Away', 'Prediction', 'Confidence', 'Advice', '']
    st.markdown(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)

with tab2:
    val_df = df[df['value_bet']]
    if val_df.empty:
        st.info("No value bets found for this selection.")
    else:
        val_display = val_df[['date', 'home', 'away', 'predicted_winner', 'win_probability', 'home_odds', 'ev']].copy()
        val_display['date'] = val_display['date'].dt.strftime('%Y-%m-%d %H:%M')
        val_display['win_probability'] = val_display['win_probability'].apply(lambda x: f"{x:.0f}%")
        val_display['ev'] = val_display['ev'].apply(lambda x: f"+{x*100:.1f}%" if x else "N/A")
        val_display.columns = ['Date', 'Home', 'Away', 'Prediction', 'Confidence', 'Odds (Home)', 'Expected Value']
        st.dataframe(val_display, use_container_width=True)

with tab3:
    fig1 = px.histogram(df[df['win_probability'].notna()], x='win_probability', nbins=20,
                        title="Prediction Confidence Distribution",
                        labels={'win_probability': 'Confidence (%)'},
                        color_discrete_sequence=['#3b82f6'])
    fig1.update_layout(bargap=0.1, plot_bgcolor='white', title_font_size=16)
    st.plotly_chart(fig1, use_container_width=True)

    if val_count > 0:
        fig2 = px.bar(val_df, x='home', y='ev', title="Expected Value per Match",
                      labels={'ev': 'Expected Value (%)', 'home': 'Home Team'},
                      color='ev', color_continuous_scale='viridis')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No value bets to display in chart.")

# ---------- Footer ----------
st.markdown(f'<div class="footer">Data last refreshed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC | Powered by API‑Football &amp; Railway</div>', unsafe_allow_html=True)