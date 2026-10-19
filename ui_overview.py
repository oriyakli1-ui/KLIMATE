"""Overview and Cognitive Clock pages. Every number comes from insights.py / metrics.py."""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import analytics
import insights
from ui_common import render_dashboard_metric_card, render_metric_card

MIN_HOUR_GAMES = 10


def _pct(x: float) -> str:
    return f"{x:.0%}" if x == x else "n/a"


def _tip(label: str, text: str) -> str:
    return f"{label} <div class='custom-tooltip'>❔<span class='tooltip-text'>{text}</span></div>"


def render_cognitive_clock_chart(profile, timezone: str) -> None:
    """Games per hour (stacked wins/draws/losses) with the score per hour and its 95% interval."""
    if profile.empty or profile["games"].sum() == 0:
        st.info("Not enough data to show time-of-day performance yet.")
        return
    df = profile.copy()
    df["label"] = df["hour"].map(lambda h: f"{h:02d}:00")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for col, name, colour in (("wins", "Wins", "#10B981"), ("draws", "Draws", "#64748B"), ("losses", "Losses", "#EF4444")):
        fig.add_trace(go.Bar(x=df["label"], y=df[col], name=name, marker_color=colour), secondary_y=False)
    solid = df[df["games"] >= MIN_HOUR_GAMES]
    if not solid.empty:
        fig.add_trace(go.Scatter(
            x=solid["label"], y=solid["score"], mode="lines+markers", name=f"Score (hours with {MIN_HOUR_GAMES}+ games)",
            line=dict(color="#06B6D4", width=2), marker=dict(size=8),
            error_y=dict(type="data", symmetric=False, array=solid["hi"] - solid["score"], arrayminus=solid["score"] - solid["lo"],
                         color="rgba(6,182,212,0.45)"),
        ), secondary_y=True)
    fig.update_layout(
        barmode="stack", hovermode="x unified", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"), margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    fig.update_xaxes(title_text=f"Hour the game started ({timezone})", gridcolor="rgba(148,163,184,0.2)")
    fig.update_yaxes(title_text="Games", secondary_y=False, gridcolor="rgba(148,163,184,0.2)")
    fig.update_yaxes(title_text="Score (95% interval)", secondary_y=True, tickformat=".0%", range=[0, 1.02])
    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    best = insights.best_hour(profile, MIN_HOUR_GAMES)
    if best:
        st.success(
            f"**Your best hour is {best['hour']:02d}:00**: score {best['score']:.0%} over {best['games']} games, "
            f"versus {best['rest']:.0%} for the rest of the day. This gap is larger than chance would explain."
        )
    else:
        st.info(
            f"**No reliable time-of-day effect.** With {int(profile['games'].sum())} games, no hour stands out from the rest "
            "by more than chance (hours with fewer than 10 games are not judged, and picking the best of 24 hours needs strong evidence)."
        )
    busiest = profile.loc[profile["games"].idxmax()]
    st.caption(f"You start the most games around {int(busiest['hour']):02d}:00 ({int(busiest['games'])} games).")


def render_overview_page(g, username: str) -> None:
    """Overview: live ratings, streak, score, performance rating, tilt and openings (``g`` = enriched games)."""
    ratings = analytics.get_real_time_ratings(username)
    kind, n = insights.current_streak(g)
    streak_value = "0" if kind == "none" else f"{'🔥' if kind == 'win' else '🧊'} {n}"
    streak_sub = "no streak" if kind == "none" else ("wins in a row" if kind == "win" else "losses in a row")

    st.markdown("<div style='margin-top: 2.5rem;'></div>", unsafe_allow_html=True)
    cols = st.columns(4)
    for col, (title, val, sub) in zip(cols, (("Rapid", ratings["rapid"], "current rating"), ("Blitz", ratings["blitz"], "current rating"),
                                             ("Bullet", ratings["bullet"], "current rating"), ("Streak", streak_value, streak_sub))):
        with col:
            render_dashboard_metric_card(title=title, value_str=str(val), sub=sub)
    st.divider()

    summ = insights.overall_summary(g)
    perf = insights.performance_summary(g)
    tilt = insights.tilt_summary(g)

    c1, c2, c3 = st.columns(3)
    with c1:
        render_metric_card(
            title=_tip("Score", "Wins plus half of draws, divided by games. The range is a 95% interval: with this many games "
                                "the true value is very likely inside it."),
            value_str=_pct(summ["score"]),
            badge_text=f"{summ['wins']}W {summ['draws']}D {summ['losses']}L · ±{(summ['score_hi'] - summ['score_lo']) / 2:.0%}" if summ["n"] > 1 else None,
        )
    with c2:
        val = f"{perf['rating']:.0f}" if perf["rating"] == perf["rating"] else "—"
        badge = (f"{perf['time_class']} · {perf['n']} rated games · opp avg {perf['avg_opponent']:.0f}" if perf["rating"] == perf["rating"]
                 else f"needs 20+ rated {perf['time_class'] or 'games'} (have {perf['n']})")
        render_metric_card(
            title=_tip("Performance Rating", "The rating at which your results would be exactly average against your opponents "
                                             "(Elo formula, rated games of your most-played time control only; time controls are never mixed)."),
            value_str=val, badge_text=badge,
        )
    with c3:
        if tilt["enough"]:
            value = f"{tilt['loss_after']:.0%}"
            badge = f"vs {tilt['loss_other']:.0%} otherwise · " + ("significant" if tilt["significant"] else "not significant")
        else:
            value, badge = "—", f"needs 20+ games after a loss (have {tilt['n_after']})"
        render_metric_card(
            title=_tip("Loss rate right after a loss", "How often you lose the game that follows a loss in the same session, compared with "
                                                       "games that do not follow a loss. 'Significant' means the difference is larger than chance explains."),
            value_str=value, badge_text=badge, badge_variant="danger" if tilt["significant"] else "neutral",
            value_class="klimate-metric-value--danger" if tilt["significant"] else "",
        )
    if perf["mixed_classes"]:
        st.caption(f"Performance rating covers {perf['time_class']} only; your other time controls are not mixed in.")
    if summ["n"]:
        opp_left = int((g["opp_result"] == "abandoned").sum())
        you_left = int((g["user_result"] == "abandoned").sum())
        if opp_left or you_left:
            st.caption(f"Results include {opp_left} wins because the opponent abandoned and {you_left} losses by abandonment, as Chess.com records them.")
        st.caption(f"Win rate (wins only): {summ['win_rate']:.1%} (95% interval {summ['win_lo']:.0%} to {summ['win_hi']:.0%}) over {summ['n']} games.")

    st.markdown("")
    st.markdown("### Opening DNA")
    ops = insights.opening_summary(g)
    if ops.empty:
        st.info("Not enough data to analyze openings yet.")
        return
    top = ops.head(10)
    fig = go.Figure(go.Bar(
        x=top["opening"], y=top["games"],
        marker=dict(color=top["score"], colorscale=["#0EA5E9", "#22C55E"], cmin=0.3, cmax=0.7,
                    colorbar=dict(title="Score", tickformat=".0%")),
        customdata=np.stack([top["score"], top["lo"], top["hi"]], axis=-1),
        hovertemplate="%{x}<br>%{y} games<br>score %{customdata[0]:.0%} (95%: %{customdata[1]:.0%} to %{customdata[2]:.0%})<extra></extra>",
    ))
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#E5E7EB"),
                      margin=dict(l=20, r=20, t=30, b=20), xaxis_title="Opening", yaxis_title="Games")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.25)")
    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)
    unk = int((g["opening"] == "Unknown").sum()) if "opening" in g.columns else 0
    if unk:
        st.caption(f"{unk} games have no opening name from Chess.com and are not shown here.")
