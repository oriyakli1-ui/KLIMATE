"""Strategic Blindspots page and the Opening Masterclass dialog."""
from __future__ import annotations

import json
from pathlib import Path

import re
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import chess
import chess.svg
import chess.pgn
import insights
from ga import queue_event
from metrics import significantly_different


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

        entry = match_pool(opening_name)
        if entry is None:
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
            st.caption("A typical position in this opening (not taken from your games).")
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


def _norm(name: object) -> str:
    """Lower-case letters/digits only, parenthesised extras removed ('Ruy Lopez (Spanish Opening)' -> 'ruylopez')."""
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\(.*?\)", "", str(name or "")).lower())


def match_pool(opening: object) -> dict | None:
    """The masterclass for an opening family: exact name match only (no fuzzy guessing)."""
    key = _norm(opening)
    if not key:
        return None
    return next((e for e in load_masterclass_pool() if _norm(e.get("name")) == key), None)


MIN_OPENING_GAMES = 8


def render_strategic_blindspots(g: pd.DataFrame, username: str) -> None:
    """Openings that score worse than the player's own average (``g`` = enriched games)."""
    st.header("Strategic Blindspots")
    ops = insights.opening_summary(g, MIN_OPENING_GAMES)
    if ops.empty or g.empty:
        st.info(f"Not enough data: an opening needs at least {MIN_OPENING_GAMES} games to be judged.")
        return

    n_all, base = len(g), float(g["score"].mean())
    ops = ops.assign(
        gap=ops["score"] - base,
        leak=[
            s < base and significantly_different(int(n), float(s), n_all, base)
            for n, s in zip(ops["games"], ops["score"])
        ],
    ).sort_values("score")
    leaks = ops[ops["leak"]]
    shown = (leaks if not leaks.empty else ops).head(3)

    if leaks.empty:
        st.info(
            f"**No opening is reliably worse than your average ({base:.0%}).** Differences between openings of "
            f"{MIN_OPENING_GAMES}+ games are within what chance produces. Here are the lowest scoring ones so far, "
            "with their uncertainty. Treat them as hints, not verdicts."
        )
    else:
        st.info(
            f"These openings score significantly below your average of {base:.0%}. "
            "The bars show the result split; the table shows the 95% interval of the score."
        )

    # result split per displayed opening, from the same enriched data
    split = {}
    for name in shown["opening"]:
        sub = g[g["opening"] == name]
        split[name] = [(sub["outcome"] == k).mean() for k in ("win", "draw", "loss")]
    fig = go.Figure()
    for i, (label, colour) in enumerate((("Win", "#22C55E"), ("Draw", "#64748B"), ("Loss", "#EF4444"))):
        fig.add_trace(go.Bar(y=[f"{n} (n={int(c)})" for n, c in zip(shown["opening"], shown["games"])],
                             x=[split[n][i] for n in shown["opening"]], name=label, orientation="h", marker_color=colour))
    fig.update_layout(
        barmode="stack", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#E5E7EB"),
        margin=dict(l=40, r=40, t=40, b=40), xaxis=dict(title="Result share", tickformat=".0%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    table = shown.assign(
        Score=shown["score"].map(lambda x: f"{x:.0%}"),
        Interval=[f"{lo:.0%} to {hi:.0%}" for lo, hi in zip(shown["lo"], shown["hi"])],
        Verdict=["below your average" if v else "within chance" for v in shown["leak"]],
    )[["opening", "games", "Score", "Interval", "Verdict"]].rename(columns={"opening": "Opening", "games": "Games"})
    st.dataframe(table, hide_index=True, width="stretch")

    st.markdown("### 🎓 Study these openings")
    cols = st.columns(len(shown))
    for i, (col, name) in enumerate(zip(cols, shown["opening"])):
        entry = match_pool(name)
        with col:
            if entry is None:
                st.caption(f"{name}: no masterclass available")
            elif st.button(f"Masterclass: {name}", key=f"blindspot_btn_{i}", width="stretch"):
                queue_event("masterclass_opened", opening_name=str(entry.get("name", name)))
                show_opening_masterclass(str(entry.get("name", name)), entry=entry)
