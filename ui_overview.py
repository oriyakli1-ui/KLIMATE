"""Overview and Cognitive Clock pages."""
from __future__ import annotations

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import analytics
from ui_common import format_opening_label, render_dashboard_metric_card, render_metric_card


MIN_GAMES_FOR_WIN_RATE_LINE = 2


def render_cognitive_clock_chart(time_of_day_df):
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
            f"**🔥 Action Plan:** Your sharpest focus is around **{peak_hour:02d}:00** ({peak_pct:.1f}% win rate). "
            "Schedule your most important Rated games during this window."
        )
    volume_row = df.loc[df["total_games"].idxmax()]
    volume_hour = int(volume_row["hour"])
    st.markdown(
        f"**⚠️ Energy Management:** You grind the most games at **{volume_hour:02d}:00**. "
        "If this isn't your peak win-rate hour, you are likely playing through fatigue. "
        "Switch to Tactics/Puzzles or Unrated games during this time to protect your Elo."
    )


def render_overview_page(games_df, username: str) -> None:
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
        render_dashboard_metric_card(title="Rapid Rating", value_str=str(live_ratings.get("rapid", "N/A")))
    with metric_cols[1]:
        render_dashboard_metric_card(title="Blitz Rating", value_str=str(live_ratings.get("blitz", "N/A")))
    with metric_cols[2]:
        render_dashboard_metric_card(title="Bullet Rating", value_str=str(live_ratings.get("bullet", "N/A")))
    with metric_cols[3]:
        render_dashboard_metric_card(title="Current Streak", value_str=streak)

    st.divider()

    # Aggregate performance metrics
    twr = analytics.calculate_true_win_rate(games_df, username)
    perf = analytics.calculate_performance_rating(games_df, username)
    tilt_stats = analytics.calculate_tilt_index(games_df, username)
    baseline_loss_rate = float(tilt_stats.get("baseline_loss_rate", 0.0) or 0.0)
    post_loss_loss_rate = float(tilt_stats.get("post_loss_loss_rate", 0.0) or 0.0)
    tilt_delta = float(tilt_stats.get("tilt_delta", 0.0) or 0.0)

    metric_cols = st.columns(3)
    with metric_cols[0]:
        twr_pct_str = f"{twr * 100:.1f}%" if twr == twr else "—"
        twr_good = twr >= 0.5 if twr == twr else False
        render_metric_card(
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
        render_metric_card(
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
        tilt_str = f"{post_loss_loss_rate:.1f}%"
        badge_text = f"{tilt_delta:+.1f}% vs baseline"
        is_tilting = tilt_delta > 5.0
        render_metric_card(
            title=(
                "Tilt Index (Post-Loss Loss Rate) "
                "<div class='custom-tooltip'>❔"
                f"<span class='tooltip-text'>Your chance of losing a game immediately after a loss, "
                f"compared to your usual loss rate of {baseline_loss_rate:.1f}%.</span>"
                "</div>"
            ),
            value_str=tilt_str,
            badge_text=badge_text,
            badge_variant="danger" if is_tilting else "neutral",
            value_class="klimate-metric-value--danger" if is_tilting else "",
        )

    st.markdown("")
    st.markdown("### Opening DNA")
    openings_df = analytics.analyze_openings(games_df, username)
    if openings_df.empty:
        st.info("Not enough data to analyze openings yet.")
        return
    openings_df = openings_df.copy()
    openings_df["opening_clean"] = openings_df["opening"].apply(format_opening_label)
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
