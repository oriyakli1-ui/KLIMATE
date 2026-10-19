"""Spatial Analysis page: where the player moves pieces and where their pieces are captured."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import streamlit as st

import spatial

FILES = ["a", "b", "c", "d", "e", "f", "g", "h"]
RANKS = ["1 (your side)", "2", "3", "4", "5", "6", "7", "8 (opponent)"]
PIECES = ["All Pieces", "Pawn", "Knight", "Bishop", "Rook", "Queen", "King"]


def _square(row: int, col: int) -> str:
    return f"{FILES[col]}{row + 1}"


@st.cache_data(show_spinner=False)
def _maps(pairs: tuple, piece: str):
    return spatial.heatmaps(pairs, piece)


def _heat(grid: np.ndarray, title: str, colors: list[str]) -> None:
    fig = px.imshow(grid, x=FILES, y=RANKS, aspect="equal", origin="lower", color_continuous_scale=colors)
    fig.update_layout(
        title=dict(text=title, font=dict(color="#F8FAFC", size=18)),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#E5E7EB"),
        width=560, height=560, coloraxis_colorbar=dict(title="count"),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False, scaleanchor="x", scaleratio=1)
    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="content", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def render_spatial(games_df, username: str) -> None:
    st.markdown("### Spatial Analysis")
    piece = st.selectbox("Filter by piece type", PIECES, index=0, key="spatial_piece_filter")

    me = username.strip().lower()
    pairs = tuple(
        (pgn, str(w).strip().lower() == me) for pgn, w in zip(games_df["pgn"], games_df["white_player"])
    )
    activity, captured, used = _maps(pairs, piece)
    st.caption(
        f"Based on {used} games. Both maps are drawn from YOUR side of the board: rank 1 is your own "
        "back rank, whether you played White or Black."
    )
    label = "pieces" if piece == "All Pieces" else piece.lower() + "s"

    tab1, tab2 = st.tabs(["🟢 Activity Map", "🔴 Captured Pieces Map"])
    with tab1:
        if activity.max() > 0:
            r, c = np.unravel_index(np.argmax(activity), activity.shape)
            st.success(
                f"Your {label} most often land on **{_square(int(r), int(c))}** "
                f"({int(activity.max())} of {int(activity.sum())} moves)."
            )
        else:
            st.info("No moves for this filter yet.")
        _heat(activity, "Where do your moves end up?", ["#0F172A", "#06B6D4", "#22D3EE"])
    with tab2:
        if captured.max() > 0:
            r, c = np.unravel_index(np.argmax(captured), captured.shape)
            st.warning(
                f"Your {label} are captured most often on **{_square(int(r), int(c))}** "
                f"({int(captured.max())} of {int(captured.sum())} captures). Every capture counts, including "
                "even trades, so this shows where the fighting happens, not only where you lose material."
            )
        else:
            st.info("No captures for this filter yet.")
        _heat(captured, "Where are your pieces captured?", ["#0F172A", "#EF4444", "#F87171"])
