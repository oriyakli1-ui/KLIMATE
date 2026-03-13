from __future__ import annotations

import re
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

import analytics
from data_engine import ChessComAPIError, fetch_player_games


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

    if st.button("Analyze Game", use_container_width=True):
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
    st.plotly_chart(fig, use_container_width=True)
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

    col1, col2 = st.columns([1, 1.5])
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
                b["critical_fen"], actual, best
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
            font-size: 1rem;
            color: #9CA3AF;
            text-align: center;
            margin-bottom: 1.5rem;
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
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #9CA3AF;
            margin-bottom: 0.3rem;
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
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 500;
            margin-top: 0.4rem;
        }

        .badge-neutral {
            background: rgba(148, 163, 184, 0.16);
            color: #E5E7EB;
        }

        .badge-success {
            background: rgba(16, 185, 129, 0.14);
            color: #6EE7B7;
        }

        .badge-danger {
            background: rgba(239, 68, 68, 0.14);
            color: #FCA5A5;
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


# Minimum games per hour to show win rate on the line (statistically robust)
MIN_GAMES_FOR_WIN_RATE_LINE = 2


def _render_cognitive_clock_chart(time_of_day_df):
    """
    Dual-axis combo chart: bars = total_games (right), line = true_win_rate (left).
    Win rate line uses only hours with total_games > MIN_GAMES_FOR_WIN_RATE_LINE
    so the line does not misleadingly dip to 0%.
    """
    if time_of_day_df.empty or time_of_day_df["total_games"].sum() == 0:
        st.info("Not enough data to show time-of-day performance yet.")
        return

    df = time_of_day_df.copy()
    df["hour_label"] = df["hour"].apply(lambda h: f"{h:02d}:00")

    # Insight: filter hours with >= 2 games, then find best/worst by true_win_rate
    df_robust = df[df["total_games"] >= 2]
    if not df_robust.empty:
        best_idx = df_robust["true_win_rate"].idxmax()
        worst_idx = df_robust["true_win_rate"].idxmin()
        best_row = df_robust.loc[best_idx]
        worst_row = df_robust.loc[worst_idx]
        best_hour = int(best_row["hour"])
        worst_hour = int(worst_row["hour"])
        max_wr_pct = best_row["true_win_rate"] * 100
        min_wr_pct = worst_row["true_win_rate"] * 100
        st.success(
            f"**Insight:** Your peak performance is at **{best_hour:02d}:00** with a **{max_wr_pct:.1f}%** win rate. "
            f"You tend to struggle around **{worst_hour:02d}:00** ({min_wr_pct:.1f}% win rate)."
        )
    else:
        st.info("Play more games at different hours to see time-of-day insights.")

    # For the line: only hours with enough games (avoid misleading 0% dips)
    df_line = df[df["total_games"] >= MIN_GAMES_FOR_WIN_RATE_LINE].copy()
    df_line = df_line.sort_values("hour").reset_index(drop=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Bars: total games (primary = left by default; we'll put bars on primary and line on secondary, or vice versa — spec: bars right, line left)
    fig.add_trace(
        go.Bar(
            x=df["hour_label"],
            y=df["total_games"],
            name="Games",
            marker_color="#334155",
        ),
        secondary_y=True,
    )
    # Line: true win rate (only where we have enough games)
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
            secondary_y=False,
        )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(title_text="Hour of the Day", gridcolor="rgba(148, 163, 184, 0.25)")
    fig.update_yaxes(
        title_text="True Win Rate",
        secondary_y=False,
        tickformat=".0%",
        range=[0, 1.02],
        gridcolor="rgba(148, 163, 184, 0.25)",
    )
    fig.update_yaxes(
        title_text="Total Games",
        secondary_y=True,
        gridcolor="rgba(148, 163, 184, 0.15)",
    )

    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


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
    live_cols = st.columns(4)
    with live_cols[0]:
        st.metric("Rapid Rating", live_ratings.get("rapid", "N/A"))
    with live_cols[1]:
        st.metric("Blitz Rating", live_ratings.get("blitz", "N/A"))
    with live_cols[2]:
        st.metric("Bullet Rating", live_ratings.get("bullet", "N/A"))
    with live_cols[3]:
        st.metric("Current Streak", streak)

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
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


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

    # Blindspots: openings with the highest loss rate
    blindspots = agg.sort_values(["LossRate", "WinRate"], ascending=[False, True]).head(5)

    # Prepare display labels using existing formatter
    blindspots = blindspots.reset_index().rename(columns={"opening_key": "opening_raw"})
    blindspots["Opening"] = blindspots["opening_raw"].apply(_format_opening_label)

    st.header("Strategic Blindspots")
    st.info(
        "These are the openings where you lose the most rating points. "
        "This is your strategic blindspot."
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

    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
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
            st.image("logo.png", use_container_width=True)
        st.markdown(
            "<p style='text-align: center; color: #9CA3AF; font-size: 1.2rem; "
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
            analyze_clicked = st.button("Analyze DNA", use_container_width=True)

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
        st.image("logo.png", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)
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
                title="Where do you move your pieces?",
            )
            fig_act.update_layout(
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
            st.plotly_chart(fig_act, use_container_width=False)
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
            st.plotly_chart(fig_vuln, use_container_width=False)
            st.markdown("</div>", unsafe_allow_html=True)

    elif selection == "Strategic Blindspots":
        _render_strategic_blindspots(games_df, username)

    elif selection == "Engine Deep Dive":
        _render_engine_deep_dive(games_df, username)


if __name__ == "__main__":
    main()

