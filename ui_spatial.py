"""Spatial Analysis page: where the player moves pieces and where pieces are lost."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import streamlit as st

import analytics


def render_spatial(games_df, username: str) -> None:
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
                f"**🎯 Strategic Directive:** Your {piece_label} thrives on **{activity_square}**. "
                "In your next games, actively look for pawn breaks or maneuvers that help you establish "
                "an outpost on this exact square."
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
                f"**🛑 Danger Zone Alert:** You bleed material heavily on **{vulnerability_square}**. "
                f"Before moving your {piece_label} here, or if your opponent attacks this sector, force yourself "
                "to stop for 3 seconds and double-check for discovered attacks or hanging pieces."
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
