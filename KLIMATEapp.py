from __future__ import annotations

import datetime
import io
import os
import re
import pickle
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from streamlit_option_menu import option_menu
import chess
import chess.svg
import chess.pgn

import analytics
from data_engine import ChessComAPIError, fetch_player_games


# Force the masterclass pool path to be relative to this script file
current_dir = os.path.dirname(__file__)
POOL_PATH = os.path.join(current_dir, "masterclass_pool.pkl")

masterclass_pool: list[dict] = []
if os.path.exists(POOL_PATH):
    try:
        with open(POOL_PATH, "rb") as _f:
            loaded = pickle.load(_f)
        if isinstance(loaded, list):
            masterclass_pool = loaded
    except Exception as _exc:  # noqa: BLE001
        st.error(f"Critical Error: Failed to load the masterclass pool at {POOL_PATH}: {_exc}")
else:
    st.error(f"Critical Error: Cannot find the masterclass pool at {POOL_PATH}")


def _format_game_label(row) -> str:
    """Create a compact label for a game row."""
    white = str(row.get("white_player", "White"))
    black = str(row.get("black_player", "Black"))
    result = str(row.get("white_result", "") or row.get("result", "")).strip()
    tc = str(row.get("time_class", "")).strip()
    parts = [f"{white} vs {black}"]
    if tc:
        parts.append(tc)
    if result:
        parts.append(result)
    return " | ".join(parts)


def _render_engine_deep_dive(games_df, username: str) -> None:
    """Engine Deep Dive: External cloud eval + visual coaching."""
    st.markdown("### Engine Deep Dive")

    if games_df is None or getattr(games_df, "empty", True):
        st.info("No games available to analyze yet.")
        return
    if "pgn" not in games_df.columns:
        st.info("This dataset doesn't include PGNs, so engine analysis is unavailable.")
        return

    df = games_df.copy().reset_index(drop=True)
    df["label"] = df.apply(_format_game_label, axis=1)

    options = list(range(len(df)))
    selected_idx = st.selectbox(
        "Select a game",
        options,
        format_func=lambda i: df.loc[i, "label"],
        key="engine_deep_dive_game_idx",
    )

    selected_pgn = df.loc[selected_idx, "pgn"]
    if not isinstance(selected_pgn, str) or not selected_pgn.strip():
        st.warning("Selected game has no PGN to analyze.")
        return

    if st.button("Analyze Game", width="stretch"):
        st.session_state["analyzed_pgn"] = selected_pgn

    # Persist UI across reruns (e.g., selectbox changes)
    if st.session_state.get("analyzed_pgn") != selected_pgn:
        return

    with st.spinner("It could take a moment, but it's worth it ⏳"):
        eval_df = analytics.analyze_game_with_chess_api(selected_pgn, max_plies=40)

    if eval_df.empty or "evaluation" not in eval_df.columns:
        st.info("No evaluation data returned for this game (yet).")
        return

    # Golden Chart: area eval + blunder markers
    eval_plot = eval_df.copy()
    eval_plot["evaluation"] = pd.to_numeric(eval_plot["evaluation"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=eval_plot["ply"],
            y=eval_plot["evaluation"].fillna(0.0),
            mode="lines",
            fill="tozeroy",
            name="Evaluation",
            line=dict(color="#06B6D4", width=2),
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(229,231,235,0.35)")

    blunders = analytics.get_all_blunders(eval_df, selected_pgn, username)
    if blunders:
        blunder_plies = [b.get("ply") for b in blunders if b.get("ply") is not None]
        blunder_vals = []
        for p in blunder_plies:
            try:
                v = float(eval_plot.loc[eval_plot["ply"] == int(p), "evaluation"].iloc[0])
            except Exception:
                v = 0.0
            blunder_vals.append(v)
        fig.add_trace(
            go.Scatter(
                x=blunder_plies,
                y=blunder_vals,
                mode="markers",
                name="Blunder",
                marker=dict(symbol="x", color="#EF4444", size=12),
            )
        )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis_title="Ply",
        yaxis_title="Evaluation (pawns)",
    )

    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # Blunder Explorer
    if not blunders:
        st.info("No blunders detected yet — try analyzing more plies or a different game.")
        return

    blunders_list = list(blunders)
    selected_idx = st.selectbox(
        "🔍 Select a Key Moment (Mistakes & Blunders):",
        options=list(range(len(blunders_list))),
        format_func=lambda i: f"Move {(int(blunders_list[i].get('ply', 0)) + 1)//2} - Swing: {float(blunders_list[i].get('eval_swing', 0.0)):.2f} pawns",
        key="blunder_explorer_select",
    )

    b = blunders_list[int(selected_idx)]
    ply = int(b.get("ply", 0) or 0)
    move_number = (ply + 1) // 2 if ply > 0 else 0
    color_to_move = "White" if ply % 2 != 0 else "Black"
    eval_swing = float(b.get("eval_swing", 0.0) or 0.0)
    critical_fen = str(b.get("critical_fen", "") or "").strip()
    actual_san = str(b.get("actual_san", "") or "").strip()

    col1, col2 = st.columns([1, 3])
    with col1:
        if not critical_fen:
            st.info("No board position available for this blunder.")
        else:
            try:
                arrows = []
                try:
                    if b.get("actual_move_uci"):
                        m1 = chess.Move.from_uci(b["actual_move_uci"])
                        arrows.append(
                            chess.svg.Arrow(
                                m1.from_square, m1.to_square, color="#EF4444"
                            )
                        )  # RED ARROW
                    if b.get("best_move_uci"):
                        m2 = chess.Move.from_uci(b["best_move_uci"])
                        arrows.append(
                            chess.svg.Arrow(
                                m2.from_square, m2.to_square, color="#10B981"
                            )
                        )  # GREEN ARROW
                except ValueError:
                    pass

                # Orient board to the user's side (since blunders are filtered to user's moves).
                board_orientation = chess.WHITE if (ply % 2 != 0) else chess.BLACK
                svg_data = chess.svg.board(
                    board=chess.Board(b["critical_fen"]),
                    arrows=arrows,
                    orientation=board_orientation,
                    size=350,
                )
                st.write(svg_data, unsafe_allow_html=True)
            except Exception:
                st.info("Failed to render this blunder board.")

    with col2:
        actual = b.get("actual_san") or b.get("actual_move_uci") or "Unknown"
        best = b.get("best_move_san") or b.get("best_move_uci") or "Unknown"

        with st.spinner("🤖 AI Coach is analyzing the position..."):
            explanation = analytics.get_gemini_coach_explanation(
                b["critical_fen"], actual, best, eval_swing
            )
        st.info(f"**🤖 Your AI Coach:**\n\n{explanation}")


def _inject_global_styles() -> None:
    """Inject custom CSS for the Slate & Cyan Bento Box dark theme."""
    st.markdown(
        """
        <style>
        /* Global page styling */
        body, .stApp {
            background-color: #0F172A;
            color: #E5E7EB;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        /* Global label styling (e.g. filter labels) */
        label {
            color: #F8FAFC !important;
            font-weight: 600;
        }

        /* Hero section */
        .klimate-hero-title {
            font-size: 2.4rem;
            font-weight: 700;
            letter-spacing: 0.05em;
            color: #E5E7EB;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .klimate-hero-subtitle {
            font-size: 1.2rem;
            color: #F8FAFC;
            text-align: center;
            margin-bottom: 1.5rem;
            font-weight: 600;
        }

        /* Bento cards */
        .klimate-card {
            background: #1E293B;
            border-radius: 15px;
            padding: 20px 22px;
            border: 1px solid #334155;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.8);
        }
        .klimate-metric-label {
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #F8FAFC;
            margin-bottom: 0.3rem;
            font-weight: 600;
        }
        .klimate-metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #E5E7EB;
        }
        .klimate-metric-value--success {
            color: #10B981;
        }
        .klimate-metric-value--danger {
            color: #EF4444;
        }
        .klimate-metric-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.95rem;
            font-weight: 600;
            margin-top: 0.4rem;
        }
        .badge-neutral {
            background: rgba(148, 163, 184, 0.16);
            color: #F8FAFC;
        }
        .badge-success {
            background: rgba(16, 185, 129, 0.14);
            color: #F8FAFC;
        }
        .badge-danger {
            background: rgba(239, 68, 68, 0.14);
            color: #F8FAFC;
        }

        /* Input styling */
        .stTextInput > div > div > input {
            background-color: #020617;
            color: #E5E7EB;
            border-radius: 999px;
            border: 1px solid #1F2937;
        }
        .stTextInput > div > div > input:focus {
            border-color: #06B6D4;
            box-shadow: 0 0 0 1px #06B6D4;
        }
        .stButton > button {
            border-radius: 999px;
            background: linear-gradient(90deg, #06B6D4, #10B981);
            color: #0F172A;
            font-weight: 600;
            border: none;
            padding: 0.55rem 1.8rem;
        }
        .stButton > button:hover {
            filter: brightness(1.05);
        }

        /* Plotly card */
        .klimate-card-plot {
            background: #1E293B;
            border-radius: 15px;
            padding: 16px 18px 6px 18px;
            border: 1px solid #334155;
        }

        /* Custom tooltip for metric cards */
        .custom-tooltip {
            position: relative;
            display: inline-block;
            cursor: pointer;
            float: right;
            opacity: 0.7;
            font-size: 16px;
        }
        .custom-tooltip:hover {
            opacity: 1;
        }
        .custom-tooltip .tooltip-text {
            visibility: hidden;
            width: 260px;
            background-color: #1E293B;
            color: #E2E8F0;
            text-align: left;
            border-radius: 8px;
            padding: 12px;
            position: absolute;
            z-index: 999;
            top: 130%;
            right: 0;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 13px;
            font-weight: 400;
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
            border: 1px solid #334155;
            line-height: 1.5;
        }
        .custom-tooltip:hover .tooltip-text {
            visibility: visible;
            opacity: 1;
        }

        /* Brighter alert/insight text (e.g. Spatial Analysis insights) */
        div[data-testid="stAlert"] {
            color: #F8FAFC !important;
            font-weight: 600;
        }
        div[data-testid="stAlert"] p {
            color: #F8FAFC !important;
            font-weight: 600;
        }

        /* Heatmaps: Label and Title Styling */
        .plotly-graph-div .g-gtitle text,
        .plotly-graph-div .g-axis text,
        .plotly-graph-div .g-legend text {
            fill: #F8FAFC !important; /* very light grey / off-white */
        }

        /* Custom Plotly Tooltip Styling for a modern look (e.g. Opening DNA) */
        .plotly-graph-div .hoverlayer .hovertext rect {
            fill: #1E293B !important;  /* dark Bento background */
            stroke: none !important;   /* no outline */
            rx: 8px !important;        /* rounded corners (x-radius) */
            ry: 8px !important;        /* rounded corners (y-radius) */
        }
        .plotly-graph-div .hoverlayer .hovertext text {
            fill: #F1F5F9 !important;  /* off-white text */
        }

        /* Tabs (Activity Map / Vulnerability Map) */
        .stTabs [role="tab"] {
            color: #F8FAFC !important;
            font-weight: 600;
        }
        .stTabs [role="tab"][aria-selected="true"] {
            border-bottom: 2px solid rgba(16, 185, 129, 0.9);
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.6);
        }

        .masterpiece-card {
            background: radial-gradient(circle at top left, #1E293B, #020617);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-top: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 20px;
            padding: 2.5rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 30px rgba(6, 182, 212, 0.15);
            text-align: center;
            margin-bottom: 2rem;
            color: #F8FAFC;
        }
        .mp-header { color: #F8FAFC; font-size: 1.15rem; letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 0.5rem; font-weight: 600; }
        .mp-username { 
            font-size: 2.8rem; font-weight: 800; margin: 0; 
            background: linear-gradient(90deg, #06B6D4, #10B981);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            text-transform: uppercase;
        }
        .mp-date { color: #F8FAFC; font-size: 1.05rem; margin-bottom: 2rem; font-weight: 600; }
        .mp-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; text-align: left; }
        .mp-stat-box { background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.01)); border-radius: 16px; padding: 1.5rem; border: 1px solid rgba(255, 255, 255, 0.08); transition: transform 0.3s ease, box-shadow 0.3s ease; }
        .mp-stat-box:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3);
            border-color: rgba(6, 182, 212, 0.4);
        }
        .mp-icon { font-size: 1.5rem; margin-bottom: 0.5rem; }
        .mp-label { color: #F8FAFC; font-size: 1.05rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem; font-weight: 600; }
        .mp-value { color: #FFFFFF; font-size: 1.5rem; font-weight: 800; margin-top: 0.3rem; letter-spacing: 0.02em; }
        .mp-footer { margin-top: 2rem; font-size: 1.05rem; color: #F8FAFC; letter-spacing: 0.1em; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _format_opening_label(raw: str) -> str:
    """
    Clean up a raw opening label that might be a URL or slug.

    - If it contains '/', keep only the last segment.
    - Replace '-' and '_' with spaces.
    - Strip and title-case.
    """
    if not isinstance(raw, str):
        return "Unknown"

    segment = raw.rsplit("/", 1)[-1]
    segment = re.sub(r"[-_]+", " ", segment)
    segment = segment.strip()
    if not segment:
        return "Unknown"
    return segment.title()


def _render_wrapped_card(username: str, live_ratings: dict, games_df) -> None:
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    wrapped = analytics.get_wrapped_data(games_df, username, live_ratings)

    import json

    # The HTML for the card itself (must have id='klimate-masterpiece-card')
    card_html = f"""
    <div id="klimate-masterpiece-card" class="masterpiece-card" style="position: relative; background: radial-gradient(circle at 50% 0%, #1E293B, #020617 80%); padding: 3rem 2rem; border-radius: 24px; color: white; text-align: center; font-family: sans-serif;">
        <div style="color: #F8FAFC; letter-spacing: 0.2em; font-size: 0.9rem; margin-bottom: 0.5rem; font-weight: 600;">KLIMATE CHESS DNA</div>
        <h1 style="font-size: 3.2rem; margin: 0; background: linear-gradient(90deg, #06B6D4, #10B981); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{username.upper()}</h1>
        <div style="color: #E2E8F0; font-weight: 600; margin-top: 0.5rem; text-transform: uppercase;">{wrapped.get('player_persona', 'Tactician')}</div>
        <div style="color: #F8FAFC; font-size: 1.05rem; margin-bottom: 2rem; font-weight: 600;">{current_date}</div>
        
        <div style="background: rgba(15,23,42,0.6); border: 1px solid rgba(16,185,129,0.4); border-radius: 20px; padding: 2rem; margin-bottom: 1.5rem;">
            <div style="font-size: 4rem; font-weight: 900; color: #10B981;">{wrapped['top_rating']}</div>
            <div style="color: #F8FAFC; font-size: 0.9rem; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600;">👑 Peak Rating</div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div style="background: rgba(255,255,255,0.05); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 0.8rem; color: #F8FAFC; text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem;">🏆 Win Rate</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: white;">{wrapped['win_percentage']}</div>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 0.8rem; color: #F8FAFC; text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem;">🗡️ Best Opening</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: white;">{wrapped['deadliest_opening']}</div>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 0.8rem; color: #F8FAFC; text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem;">⚡ Prime Time</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: white;">{wrapped['golden_hour']}</div>
            </div>
            <div style="background: rgba(255,255,255,0.05); padding: 1.2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);">
                <div style="font-size: 0.8rem; color: #F8FAFC; text-transform: uppercase; font-weight: 600; margin-bottom: 0.3rem;">♟️ Plays Like</div>
                <div style="font-size: 1.3rem; font-weight: 800; color: #10B981;">{wrapped['gm_match']}</div>
            </div>
        </div>
    </div>
    """

    # 1. Define the viral text
    app_url = "https://klimate.streamlit.app/" 
    share_text = f"""🚀 I just analyzed my Chess DNA with Klimate.AI! 

Here are my stats as an official {wrapped.get('player_persona', 'Tactician')}:
👑 Peak Rating: {wrapped['top_rating']}
🏆 Win Rate: {wrapped['win_percentage']}
🗡️ Deadliest Weapon: {wrapped['deadliest_opening']}
⚡ Prime Time: {wrapped['golden_hour']}
♟️ Playstyle Match: {wrapped['gm_match']}

Discover your own hidden chess psychology and strategic blindspots here: {app_url}

#Klimate #Chess #DataScience #AI #ProductAnalytics
"""

    import json
    js_share_text = json.dumps(share_text)

    # 2. The Copy & Open Script
    share_script = f"""
    <div style="display: flex; justify-content: center; margin-top: 30px; margin-bottom: 20px;">
        <button onclick='shareToLinkedIn()' style="background: linear-gradient(90deg, #0A66C2, #004182); color: white; padding: 14px 28px; border: none; border-radius: 12px; font-weight: 700; font-size: 1.1rem; cursor: pointer; box-shadow: 0 8px 15px rgba(10, 102, 194, 0.4); transition: transform 0.2s; display: flex; align-items: center; gap: 10px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
            Copy Data & Open LinkedIn
        </button>
    </div>

    <script>
    function shareToLinkedIn() {{
        const tempTextArea = document.createElement("textarea");
        tempTextArea.value = {js_share_text};
        document.body.appendChild(tempTextArea);
        tempTextArea.select();
        tempTextArea.setSelectionRange(0, 99999); 
        
        try {{
            document.execCommand("copy");
            const btn = document.querySelector('button');
            const originalText = btn.innerHTML;
            btn.innerHTML = '✅ Copied! Opening LinkedIn...';
            
            setTimeout(() => {{
                window.open('https://www.linkedin.com/feed/', '_blank');
                btn.innerHTML = originalText;
            }}, 1500);
            
        }} catch (err) {{
            console.error('Oops, unable to copy', err);
            alert('Unable to copy automatically. Please copy manually.');
        }}
        
        document.body.removeChild(tempTextArea);
    }}
    </script>
    """

    # Render everything using components.html to ensure JS context is whole
    import streamlit.components.v1 as components
    components.html(card_html + share_script, height=750, scrolling=True)


@st.dialog("Your Chess DNA", width="large")
def _show_klimate_masterpiece(username: str, games_df) -> None:
    live_ratings = analytics.get_real_time_ratings(username)
    _render_wrapped_card(username, live_ratings, games_df)


def _render_metric_card(
    title: str,
    value_str: str,
    badge_text: Optional[str] = None,
    badge_variant: str = "neutral",
    value_class: str = "",
) -> None:
    """Render a single Bento-style metric card."""
    badge_class = {
        "neutral": "badge-neutral",
        "success": "badge-success",
        "danger": "badge-danger",
    }.get(badge_variant, "badge-neutral")

    badge_html = (
        f'<div class="klimate-metric-badge {badge_class}">{badge_text}</div>'
        if badge_text
        else ""
    )

    value_css = f" klimate-metric-value {value_class}".strip() if value_class else "klimate-metric-value"

    st.markdown(
        f"""
        <div class="klimate-card">
            <div class="klimate-metric-label">{title}</div>
            <div class="{value_css}">{value_str}</div>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_dashboard_metric_card(title: str, value_str: str) -> None:
    """Render a Bento-style metric card (title + value only, no badge)."""
    st.markdown(
        f"""
        <div class="klimate-card">
            <div class="klimate-metric-label">{title}</div>
            <div class="klimate-metric-value">{value_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Minimum games per hour to show win rate on the line (statistically robust)
MIN_GAMES_FOR_WIN_RATE_LINE = 2


def _render_cognitive_clock_chart(time_of_day_df):
    """
    Dual-axis chart: stacked bars (Wins/Draws/Losses) on primary Y-axis,
    True Win Rate line on secondary Y-axis. Slate dark theme with unified hover.
    """
    if time_of_day_df.empty or time_of_day_df["total_games"].sum() == 0:
        st.info("Not enough data to show time-of-day performance yet.")
        return

    df = time_of_day_df.copy()
    df["hour_label"] = df["hour"].apply(lambda h: f"{h:02d}:00")

    # For win-rate line: only hours with enough games to avoid misleading 0% dips
    df_line = df[df["total_games"] >= MIN_GAMES_FOR_WIN_RATE_LINE].copy()
    df_line = df_line.sort_values("hour").reset_index(drop=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Primary Y-axis: stacked bars (Wins, Draws, Losses)
    fig.add_trace(
        go.Bar(
            x=df["hour_label"],
            y=df["wins"],
            name="Wins",
            marker_color="#10B981",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df["hour_label"],
            y=df["draws"],
            name="Draws",
            marker_color="#64748B",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df["hour_label"],
            y=df["losses"],
            name="Losses",
            marker_color="#EF4444",
        ),
        secondary_y=False,
    )
    # Secondary Y-axis: True Win Rate line
    if not df_line.empty:
        fig.add_trace(
            go.Scatter(
                x=df_line["hour_label"],
                y=df_line["true_win_rate"],
                name="True Win Rate",
                mode="lines+markers",
                line=dict(color="#06B6D4", width=2),
                marker=dict(size=8, color="#06B6D4"),
            ),
            secondary_y=True,
        )

    fig.update_layout(
        barmode="stack",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color="#E5E7EB"),
        ),
    )
    fig.update_xaxes(title_text="Hour of the Day", gridcolor="rgba(148, 163, 184, 0.2)")
    fig.update_yaxes(
        title_text="Games (Wins / Draws / Losses)",
        secondary_y=False,
        gridcolor="rgba(148, 163, 184, 0.2)",
    )
    fig.update_yaxes(
        title_text="True Win Rate",
        secondary_y=True,
        tickformat=".0%",
        range=[0, 1.02],
        gridcolor="rgba(148, 163, 184, 0.15)",
    )

    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # Text insights below the chart
    df_with_games = df[df["total_games"] >= MIN_GAMES_FOR_WIN_RATE_LINE]
    if not df_with_games.empty:
        peak_row = df_with_games.loc[df_with_games["true_win_rate"].idxmax()]
        peak_hour = int(peak_row["hour"])
        peak_pct = peak_row["true_win_rate"] * 100
        st.markdown(
            f"**Peak Performance:** Your highest win rate is at **{peak_hour:02d}:00**, "
            f"where you win **{peak_pct:.1f}%** of your games."
        )
    volume_row = df.loc[df["total_games"].idxmax()]
    volume_hour = int(volume_row["hour"])
    st.markdown(
        f"**Volume:** You play the most games at **{volume_hour:02d}:00**. "
        "Is this when you are at your best?"
    )


def _render_overview_page(games_df, username: str) -> None:
    """Overview Dashboard: live stats + metrics + Opening DNA chart."""
    username_lc = username.strip().lower()
    df_user = games_df.copy()
    is_white = df_user["white_player"].astype(str).str.lower() == username_lc
    df_user["user_rating"] = np.where(is_white, df_user["white_rating"], df_user["black_rating"])
    df_user["user_result"] = np.where(is_white, df_user["white_result"], df_user["black_result"])

    live_ratings = analytics.get_real_time_ratings(username)
    _, streak = analytics.get_current_profile_stats(df_user)

    # Spacer to avoid top clipping under header
    st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)

    # Live ratings + streak row
    metric_cols = st.columns(4)
    with metric_cols[0]:
        _render_dashboard_metric_card(title="Rapid Rating", value_str=str(live_ratings.get("rapid", "N/A")))
    with metric_cols[1]:
        _render_dashboard_metric_card(title="Blitz Rating", value_str=str(live_ratings.get("blitz", "N/A")))
    with metric_cols[2]:
        _render_dashboard_metric_card(title="Bullet Rating", value_str=str(live_ratings.get("bullet", "N/A")))
    with metric_cols[3]:
        _render_dashboard_metric_card(title="Current Streak", value_str=streak)

    st.divider()

    # Aggregate performance metrics
    twr = analytics.calculate_true_win_rate(games_df, username)
    perf = analytics.calculate_performance_rating(games_df, username)
    tilt_stats = analytics.calculate_tilt_index(games_df, username)
    tilt_drop_pct = tilt_stats.get("tilt_drop_percentage", 0.0)

    metric_cols = st.columns(3)
    with metric_cols[0]:
        twr_pct_str = f"{twr * 100:.1f}%" if twr == twr else "—"
        twr_good = twr >= 0.5 if twr == twr else False
        _render_metric_card(
            title=(
                "True Win Rate "
                "<div class='custom-tooltip'>❔"
                "<span class='tooltip-text'>Measures your decisive win percentage, excluding draws. "
                "Helps identify if your playstyle is sharp and effective.</span>"
                "</div>"
            ),
            value_str=twr_pct_str,
            badge_text="Healthy" if twr_good else "Growth Edge",
            badge_variant="success" if twr_good else "neutral",
            value_class="klimate-metric-value--success" if twr_good else "",
        )
    with metric_cols[1]:
        perf_str = f"{perf:.0f}" if perf == perf else "—"
        _render_metric_card(
            title=(
                "Performance Rating "
                "<div class='custom-tooltip'>❔"
                "<span class='tooltip-text'>Your effective Elo in this specific dataset. "
                "Calculated based on your opponents ratings and your success rate against them.</span>"
                "</div>"
            ),
            value_str=perf_str,
            badge_text="On the Rise" if perf == perf else "Need More Data",
            badge_variant="neutral",
        )
    with metric_cols[2]:
        tilt_str = f"{tilt_drop_pct:.1f}%" if tilt_drop_pct == tilt_drop_pct else "—"
        is_tilting = tilt_drop_pct > 0
        _render_metric_card(
            title=(
                "Tilt Index (Post-Loss Drop) "
                "<div class='custom-tooltip'>❔"
                "<span class='tooltip-text'>Measures emotional resilience. Shows the percentage of times "
                "a loss is immediately followed by another loss (Post-Loss Drop).</span>"
                "</div>"
            ),
            value_str=tilt_str,
            badge_text="Tilt Detected" if is_tilting else "Resilient",
            badge_variant="danger" if is_tilting else "success",
            value_class="klimate-metric-value--danger" if is_tilting else "",
        )

    st.markdown("")
    st.markdown("### Opening DNA")
    openings_df = analytics.analyze_openings(games_df, username)
    if openings_df.empty:
        st.info("Not enough data to analyze openings yet.")
        return
    openings_df = openings_df.copy()
    openings_df["opening_clean"] = openings_df["opening"].apply(_format_opening_label)
    top_openings = openings_df.head(10)
    fig = px.bar(
        top_openings,
        x="opening_clean",
        y="total_games",
        color="true_win_rate",
        color_continuous_scale=["#0EA5E9", "#22C55E"],
        labels={"opening_clean": "Opening", "total_games": "Total Games"},
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        margin=dict(l=20, r=20, t=30, b=20),
        coloraxis_colorbar=dict(title="True Win Rate", tickformat=".0%"),
    )
    fig.update_yaxes(gridcolor="rgba(148, 163, 184, 0.25)")
    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


@st.dialog("🎓 Opening Masterclass", width="large")
def show_opening_masterclass(opening_name: str, entry: dict | None = None) -> None:
    """Modal dialog: Opening Masterclass using precomputed local pool + YouTube link."""
    st.header(opening_name)

    # If a specific pool entry was provided (from Strategic Blindspots), use it directly.
    if entry is None:
        if not masterclass_pool:
            st.info("Masterclass data is not available yet. Please try again later.")
            return

        opening_lower = opening_name.lower()
        # Exact match first, then substring match as a fallback.
        entry = next((e for e in masterclass_pool if str(e.get("name", "")).lower() == opening_lower), None)
        if entry is None:
            entry = next(
                (
                    e
                    for e in masterclass_pool
                    if opening_lower in str(e.get("name", "")).lower()
                    or str(e.get("name", "")).lower() in opening_lower
                ),
                None,
            )
        if entry is None:
            # Silent failure in this rare path; Strategic Blindspots already filters strictly.
            st.info("Masterclass data is not available yet for this opening.")
            return

    explanation = str(entry.get("analysis", "") or "").strip()
    if not explanation:
        st.info("Masterclass text is not available for this opening yet.")
        return

    fen = str(entry.get("fen", "") or "").strip()
    try:
        board = chess.Board(fen) if fen else chess.Board()
    except Exception:
        board = chess.Board()

    col1, col2 = st.columns([1, 1.5])
    with col1:
        try:
            svg_data = chess.svg.board(board=board, size=320)
            st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
            st.write(svg_data, unsafe_allow_html=True)
            st.caption("Representative position from your games with this opening.")
            st.markdown("<div style='margin-top: 0.5rem;'></div>", unsafe_allow_html=True)
        except Exception:
            st.info("Board visualization unavailable.")

        formatted = opening_name.replace(" ", "+").strip()
        yt_url = f"https://www.youtube.com/results?search_query=chess+opening+{formatted}"
        st.markdown(
            f'<br><a href="{yt_url}" target="_blank" rel="noopener noreferrer" '
            'style="display: block; text-align: center; padding: 0.6rem 1rem; background: #06B6D4; '
            'color: #0F172A; border-radius: 8px; text-decoration: none; font-weight: 600;">'
            "🎥 Watch Video Masterclass</a>",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"<div style='font-size: 1.15rem; font-weight: 600; line-height: 1.7;'>\n\n{explanation}\n</div>",
            unsafe_allow_html=True,
        )
        st.divider()


def _render_strategic_blindspots(games_df: pd.DataFrame, username: str) -> None:
    """Analyze openings where the user statistically struggles the most."""
    username_lc = username.strip().lower()
    df = games_df.copy()
    if df.empty:
        st.info("No games loaded yet.")
        return

    is_white = df["white_player"].astype(str).str.lower() == username_lc
    df["user_result_raw"] = np.where(is_white, df["white_result"], df["black_result"])

    loss_results = {"checkmated", "timeout", "resigned", "abandoned", "lose", "loss"}

    def _outcome(res: object) -> str:
        r = str(res or "").strip().lower()
        if r == "win":
            return "Win"
        if r in loss_results:
            return "Loss"
        return "Draw"

    df["user_outcome"] = df["user_result_raw"].map(_outcome)

    # Opening key similar to analyze_openings: prefer 'opening', fallback 'eco'
    opening_series = df.get("opening", pd.Series(index=df.index, dtype="object")).fillna("")
    eco_series = df.get("eco", pd.Series(index=df.index, dtype="object")).fillna("")
    opening_key = opening_series.where(opening_series.str.len() > 0, eco_series)
    opening_key = opening_key.replace("", "Unknown")
    df["opening_key"] = opening_key

    # Aggregate results per opening
    agg = (
        df.groupby(["opening_key", "user_outcome"])
        .size()
        .unstack(fill_value=0)
    )
    agg["Total"] = agg.sum(axis=1)
    # Filter to openings seen at least 3 times
    agg = agg[agg["Total"] >= 3]
    if agg.empty:
        st.info("Not enough opening data yet to identify strategic blindspots.")
        return

    # Ensure all columns exist
    for col in ["Win", "Loss", "Draw"]:
        if col not in agg.columns:
            agg[col] = 0

    agg["WinRate"] = agg["Win"] / agg["Total"]
    agg["LossRate"] = agg["Loss"] / agg["Total"]
    agg["DrawRate"] = agg["Draw"] / agg["Total"]

    # Build the FULL openings performance table
    blindspots_df = agg.reset_index().rename(columns={"opening_key": "opening_raw"}).copy()
    blindspots_df["Opening"] = blindspots_df["opening_raw"].apply(_format_opening_label)

    # 1. Smarter Fuzzy Matcher
    def clean_opening_name(text: object) -> str:
        # If it's a URL, get the last part
        t = str(text or "").split("/")[-1]
        # Replace all non-alphanumeric characters (hyphens, apostrophes, commas) with spaces
        t = re.sub(r"[^a-zA-Z0-9]", " ", t).lower()
        # Remove extra whitespace
        return " ".join(t.split())

    def get_matching_pool_item(user_opening: object) -> dict | None:
        if not masterclass_pool:
            return None

        user_clean = clean_opening_name(user_opening)
        if not user_clean:
            return None

        for item in masterclass_pool:
            pool_name = item.get("name", "")
            pool_clean = clean_opening_name(pool_name)
            if not pool_clean:
                continue

            # Check full exact match after cleaning
            if pool_clean in user_clean or user_clean in pool_clean:
                return item

            # Check base match (first two words)
            pool_words = pool_clean.split()
            if len(pool_words) >= 2:
                base_pool = f"{pool_words[0]} {pool_words[1]}"
                if base_pool in user_clean:
                    return item

        return None

    # 2. Filter the ENTIRE dataframe against our masterclass pool FIRST
    blindspots_df["pool_match"] = blindspots_df["Opening"].apply(get_matching_pool_item)
    matched_openings_df = blindspots_df[blindspots_df["pool_match"].notnull()].copy()

    if matched_openings_df.empty:
        st.info(
            "You play very unique openings! Play more standard openings to unlock deep-dive Masterclasses."
        )
        return

    # 3. Sort ONLY the matched openings by worst performance (ascending win rate)
    worst_matched_df = matched_openings_df.sort_values(by="WinRate", ascending=True)

    # 4. Take the Top 3 from this sorted, matched list
    final_display_df = worst_matched_df.head(3).copy()

    if final_display_df.empty:
        st.info(
            "You play very unique openings! Play more standard openings to unlock deep-dive Masterclasses."
        )
        return

    blindspots = final_display_df

    st.header("Strategic Blindspots")
    st.info(
        "These are the openings where you drop the most rating points—your strategic blindspots. 👇 "
        "**Scroll to the bottom of this page to unlock a personalized AI Masterclass and turn these weaknesses into weapons!**"
    )

    # Horizontal stacked bar chart of Win/Loss/Draw rates
    openings = blindspots["Opening"]
    win_pct = blindspots["WinRate"]
    loss_pct = blindspots["LossRate"]
    draw_pct = blindspots["DrawRate"]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=openings,
            x=win_pct,
            name="Win",
            orientation="h",
            marker_color="#22C55E",
        )
    )
    fig.add_trace(
        go.Bar(
            y=openings,
            x=draw_pct,
            name="Draw",
            orientation="h",
            marker_color="#64748B",
        )
    )
    fig.add_trace(
        go.Bar(
            y=openings,
            x=loss_pct,
            name="Loss",
            orientation="h",
            marker_color="#EF4444",
        )
    )

    fig.update_layout(
        barmode="stack",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(title="Result share", tickformat=".0%"),
        yaxis=dict(title="Opening"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_layout(legend=dict(font=dict(color="#E5E7EB")))

    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### 🎓 Deep Dive into your Blindspots")
    records = blindspots[["Opening", "pool_match"]].to_dict("records")
    num_openings = len(records)
    cols = st.columns(max(1, num_openings))

    for i, row in enumerate(records):
        opening_name = str(row["Opening"])
        pool_item = row["pool_match"]
        with cols[i]:
            if st.button(f"Analyze {opening_name}", key=f"blindspot_btn_{i}", width="stretch"):
                # Directly show the dialog using the matched pool entry (no API calls).
                show_opening_masterclass(str(pool_item.get("name", opening_name)), entry=pool_item)

def main() -> None:
    """Main entry point for the Klimate Streamlit app."""
    st.set_page_config(
        page_title="Klimate AI",
        page_icon="♟️",
        layout="wide",
    )

    _inject_global_styles()

    data_loaded = st.session_state.get("data_loaded", False)

    # Landing page: logo + input only; no sidebar content
    if not data_loaded:
        _, logo_col, _ = st.columns([1, 2, 1])
        with logo_col:
            st.image("logo.png", width="stretch")
        st.markdown(
            "<p style='text-align: center; color: #D1D5DB; font-size: 1.2rem; "
            "font-weight: 300; margin-top: -15px; margin-bottom: 40px; letter-spacing: 1px;'>"
            "Decode Your Chess DNA. Elevate Your Mental Game.</p>",
            unsafe_allow_html=True,
        )

        # Centered search-style username input & button
        col_left, col_center, col_right = st.columns([1, 2, 1])
        with col_center:
            username_input = st.text_input(
                "Chess.com Username", placeholder="e.g. oriyakli1"
            )
            analyze_clicked = st.button("Analyze DNA", width="stretch")

        if analyze_clicked and username_input.strip():
            username = username_input.strip()
            with st.spinner("Analyzing your chess DNA..."):
                try:
                    games_df = fetch_player_games(username, max_games=100)
                except ChessComAPIError as exc:
                    st.error(f"Failed to fetch games for '{username}': {exc}")
                else:
                    if games_df.empty:
                        st.warning(
                            f"No recent games found for '{username}'. "
                            "Play a few games on Chess.com and try again."
                        )
                    else:
                        st.session_state["games_df"] = games_df
                        st.session_state["username"] = username
                        st.session_state["data_loaded"] = True
                        st.rerun()

        return

    # Dashboard mode: sidebar menu + main content
    games_df = st.session_state["games_df"]
    username = st.session_state["username"]

    with st.sidebar:
        st.image("logo.png", width="stretch")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🎁 Generate My Klimate Masterpiece", type="primary"):
            _show_klimate_masterpiece(username, games_df)
        selection = option_menu(
            menu_title="KLIMATE",
            options=[
                "Overview",
                "Cognitive Clock",
                "Spatial Analysis",
                "Strategic Blindspots",
                "Engine Deep Dive",
            ],
            icons=["house", "clock-history", "bullseye", "bullseye", "cpu"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#06B6D4", "font-size": "18px"},
                "nav-link": {
                    "font-size": "15px",
                    "text-align": "left",
                    "margin": "0px",
                    "--hover-color": "rgba(6, 182, 212, 0.1)",
                },
                "nav-link-selected": {"background-color": "#06B6D4", "font-weight": "bold"},
            },
        )

    # Top emblem in main content area
    st.markdown(
        "<div style='margin-top: 45px; display: flex; align-items: center; gap: 10px; "
        "margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);'>"
        "<span style='font-size: 1.2rem; opacity: 0.8;'>♟️</span>"
        "<span style='font-weight: 700; color: #E2E8F0; letter-spacing: 2px; font-size: 1.1rem;'>KLIMATE</span>"
        "<span style='color: #06B6D4; font-size: 0.85rem; font-weight: 600; letter-spacing: 1px;'>| COMMAND CENTER</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if selection == "Overview":
        _render_overview_page(games_df, username)

    elif selection == "Cognitive Clock":
        st.markdown("### Cognitive Performance (Time of Day)")
        time_of_day_df = analytics.analyze_time_of_day(games_df, username)
        _render_cognitive_clock_chart(time_of_day_df)

    elif selection == "Spatial Analysis":
        st.markdown("### Spatial Analysis")
        piece_options = [
            "All Pieces",
            "Pawn",
            "Knight",
            "Bishop",
            "Rook",
            "Queen",
            "King",
        ]
        piece_filter = st.selectbox(
            "Filter by piece type",
            piece_options,
            index=0,
            key="spatial_piece_filter",
        )
        activity_map, vulnerability_map = analytics.generate_spatial_heatmaps(
            games_df, username, piece_filter=piece_filter
        )
        files = ["a", "b", "c", "d", "e", "f", "g", "h"]
        ranks = ["1", "2", "3", "4", "5", "6", "7", "8"]

        # Insights: max-activity and max-vulnerability squares (row, col) -> chess notation
        def _row_col_to_square(row: int, col: int) -> str:
            return chr(col + ord("a")) + str(row + 1)

        act_max = float(np.max(activity_map)) if activity_map.size else 0
        vuln_max = float(np.max(vulnerability_map)) if vulnerability_map.size else 0
        if act_max > 0:
            ar, ac = np.unravel_index(np.argmax(activity_map), activity_map.shape)
            activity_square = _row_col_to_square(int(ar), int(ac))
        else:
            activity_square = None
        if vuln_max > 0:
            vr, vc = np.unravel_index(
                np.argmax(vulnerability_map), vulnerability_map.shape
            )
            vulnerability_square = _row_col_to_square(int(vr), int(vc))
        else:
            vulnerability_square = None

        piece_label = piece_filter.lower() if piece_filter != "All Pieces" else "pieces"

        tab1, tab2 = st.tabs(["🟢 Activity Map", "🔴 Vulnerability Map"])

        with tab1:
            if activity_square:
                st.success(
                    f"**Insight:** Your most active square for **{piece_label}** is **{activity_square}**."
                )
            else:
                st.info("No activity data for this filter yet.")
            fig_act = px.imshow(
                activity_map,
                x=files,
                y=ranks,
                aspect="equal",
                origin="lower",
                color_continuous_scale=["#0F172A", "#06B6D4", "#22D3EE"],
            )
            fig_act.update_layout(
                title=dict(
                    text="Where do you move your pieces?",
                    font=dict(color="#F8FAFC", size=18),
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E5E7EB"),
                width=550,
                height=550,
            )
            fig_act.update_xaxes(showgrid=False, showticklabels=True)
            fig_act.update_yaxes(
                showgrid=False, showticklabels=True, scaleanchor="x", scaleratio=1
            )
            st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
            st.plotly_chart(fig_act, width="content", config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            if vulnerability_square:
                st.warning(
                    f"**Insight:** Watch out! You lose your **{piece_label}** most frequently on square **{vulnerability_square}**."
                )
            else:
                st.info("No vulnerability data for this filter yet.")
            fig_vuln = px.imshow(
                vulnerability_map,
                x=files,
                y=ranks,
                aspect="equal",
                origin="lower",
                color_continuous_scale=["#0F172A", "#EF4444", "#F87171"],
                title="Where do you lose your pieces?",
            )
            fig_vuln.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E5E7EB"),
                width=550,
                height=550,
            )
            fig_vuln.update_xaxes(showgrid=False, showticklabels=True)
            fig_vuln.update_yaxes(
                showgrid=False, showticklabels=True, scaleanchor="x", scaleratio=1
            )
            st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
            st.plotly_chart(fig_vuln, width="content", config={"displayModeBar": False})
            st.markdown("</div>", unsafe_allow_html=True)

    elif selection == "Strategic Blindspots":
        _render_strategic_blindspots(games_df, username)

    elif selection == "Engine Deep Dive":
        _render_engine_deep_dive(games_df, username)


if __name__ == "__main__":
    main()

