"""Strategic Blindspots page and the Opening Masterclass dialog."""
from __future__ import annotations

import json
from pathlib import Path

import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import chess
import chess.svg
import chess.pgn
from ga import queue_event
from ui_common import format_opening_label


POOL_PATH = Path(__file__).parent / "masterclass_pool.json"


@st.cache_resource(show_spinner=False)
def load_masterclass_pool() -> list[dict]:
    """Precomputed opening masterclasses (JSON, loaded once per server process)."""
    try:
        data = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        st.error(f"Could not load the masterclass pool at {POOL_PATH}: {exc}")
        return []
    return data if isinstance(data, list) else []


@st.dialog("🎓 Opening Masterclass", width="large")
def show_opening_masterclass(opening_name: str, entry: dict | None = None) -> None:
    """Modal dialog: Opening Masterclass using precomputed local pool + YouTube link."""
    st.header(opening_name)

    # If a specific pool entry was provided (from Strategic Blindspots), use it directly.
    if entry is None:
        if not load_masterclass_pool():
            st.info("Masterclass data is not available yet. Please try again later.")
            return

        opening_lower = opening_name.lower()
        # Exact match first, then substring match as a fallback.
        entry = next((e for e in load_masterclass_pool() if str(e.get("name", "")).lower() == opening_lower), None)
        if entry is None:
            entry = next(
                (
                    e
                    for e in load_masterclass_pool()
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


def render_strategic_blindspots(games_df: pd.DataFrame, username: str) -> None:
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
    df = df[df["opening_key"] != "Unknown"]

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
    blindspots_df["Opening"] = blindspots_df["opening_raw"].apply(format_opening_label)

    # 1. Smarter Fuzzy Matcher
    def clean_opening_name(text: object) -> str:
        # If it's a URL, get the last part
        t = str(text or "").split("/")[-1]
        # Replace all non-alphanumeric characters (hyphens, apostrophes, commas) with spaces
        t = re.sub(r"[^a-zA-Z0-9]", " ", t).lower()
        # Remove extra whitespace
        return " ".join(t.split())

    def get_matching_pool_item(user_opening: object) -> dict | None:
        if not load_masterclass_pool():
            return None

        user_clean = clean_opening_name(user_opening)
        if not user_clean:
            return None

        for item in load_masterclass_pool():
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
        "These are your Elo leaks. Stop playing these openings on autopilot! 👇 "
        "**Scroll down to unlock a personalized AI Masterclass. Learn the core plans before you try them again in Rated games.**"
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
                queue_event("masterclass_opened", opening_name=str(pool_item.get("name", opening_name)))
                # Directly show the dialog using the matched pool entry (no API calls).
                show_opening_masterclass(str(pool_item.get("name", opening_name)), entry=pool_item)
