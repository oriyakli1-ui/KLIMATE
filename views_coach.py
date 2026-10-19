"""Streamlit pages: Coach Report, Progress, Training Plan, Compare."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis
import coach
import insights
import llm
import training
from i18n import t
from data_engine import ChessComAPIError, fetch_player_games
from views_insights import CYAN, GREEN, GREY, RED, _bar, _card


def _line_layout(fig: go.Figure, title: str, height: int = 340) -> None:
    fig.update_layout(
        title=dict(text=title, font=dict(color="#F8FAFC", size=16)),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E5E7EB"),
        height=height,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", y=1.12),
    )
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.2)")


def _plot(fig: go.Figure) -> None:
    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- Coach Report
def render_coach_report(games_df: pd.DataFrame, username: str) -> None:
    st.markdown("### " + t("coach_title"))
    st.caption("Runs Stockfish on your recent games and finds *where* and *how* you lose points.")
    if not coach.stockfish_available():
        st.info(
            "This page needs a local Stockfish engine, which is installed on the live site. "
            "Set the STOCKFISH_PATH environment variable (or install Stockfish) to use it locally."
        )
        return

    n = st.select_slider("Games to analyze", options=[10, 20, 30], value=20, key="coach_n")
    if st.button(t("analyze_recent"), type="primary", key="coach_run"):
        bar = st.progress(0.0, text="Analyzing…")
        moves, games = coach.analyze_recent(
            games_df, username, n=n, depth=10, progress=lambda done, total: bar.progress(done / total, text=f"Analyzed {done}/{total} games")
        )
        bar.empty()
        st.session_state["coach"] = {"moves": moves, "games": games, "user": username, "n": n}

    data = st.session_state.get("coach")
    if not data or data["user"] != username:
        st.info("Press the button to analyze. It takes roughly 2-3 seconds per game.")
        return
    moves, games = data["moves"], data["games"]
    if games.empty:
        st.warning("No analyzable games found (the games need PGNs).")
        return

    c = st.columns(4)
    c[0].metric("Games analyzed", len(games))
    c[1].metric("Average accuracy", f"{games['accuracy'].mean():.0f}%", help="Mean per-move accuracy from win-chance loss (Lichess-style approximation).")
    c[2].metric("Blunders / game", f"{games['blunders'].mean():.1f}")
    c[3].metric("Mistakes / game", f"{games['mistakes'].mean():.1f}")

    g = games.sort_values("date_utc")
    fig = go.Figure(go.Scatter(x=list(range(1, len(g) + 1)), y=g["accuracy"], mode="lines+markers", line=dict(color=CYAN)))
    _line_layout(fig, "Accuracy per game (oldest → newest)")
    fig.update_yaxes(range=[0, 100])
    _plot(fig)

    pat = analysis.error_patterns(moves)
    if not pat["phase"].empty:
        p = pat["phase"]
        _bar(p["phase"].str.title(), p["errors_per_100"],
             "Serious errors per 100 moves, by phase (tallest bar = weakest phase)", pct=False,
             labels=[f"{e:.1f}<br>n={int(m)}" for e, m in zip(p["errors_per_100"], p["moves"])],
             colors=[RED if e == p["errors_per_100"].max() else CYAN for e in p["errors_per_100"]], height=300)
    if not pat["types"].empty:
        types_df = pat["types"]
        names = {"hung_piece": "Hung a piece", "missed_capture": "Missed a free capture",
                 "walked_into_attack": "Walked into an attack", "positional": "Positional drift"}
        _bar([names.get(x, x) for x in types_df["error_type"]], types_df["share"], "What your mistakes and blunders are",
             [f"{s:.0%}<br>n={n_}" for s, n_ in zip(types_df["share"], types_df["count"])], height=300)
        st.caption("Error types are heuristics based on the engine's best moves, not a verdict.")

    if st.button("Write my coaching summary", key="coach_summary"):
        with st.spinner("Writing…"):
            st.session_state["coach_summary"] = llm.pattern_summary(coach.stats_text(moves, games))
    if st.session_state.get("coach_summary"):
        st.info(st.session_state["coach_summary"])


# -------------------------------------------------------------------- Progress
def _goal_default(tc: str, current: int) -> int:
    raw = st.query_params.get(f"goal_{tc}")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return current + 100


def render_progress(g: pd.DataFrame) -> None:
    st.markdown("### " + t("progress_title"))
    d = g.dropna(subset=["user_rating"])
    if len(d) < 10:
        st.info("Not enough rated games yet. Load more history in the filters.")
        return

    fig = go.Figure()
    for tc, color in zip(sorted(d["time_class"].unique()), [CYAN, GREEN, "#F59E0B", GREY]):
        s = d[d["time_class"] == tc].sort_values("date_utc")
        if len(s) >= 5:
            fig.add_trace(go.Scatter(x=s["date_utc"], y=s["user_rating"], mode="lines", name=tc, line=dict(color=color)))
    _line_layout(fig, "Rating over time")
    _plot(fig)

    roll = d.sort_values("date_utc").assign(rolling=lambda x: x["score"].rolling(20, min_periods=10).mean())
    fig2 = go.Figure(go.Scatter(x=roll["date_utc"], y=roll["rolling"], mode="lines", line=dict(color=GREEN)))
    fig2.add_hline(y=float(d["score"].mean()), line_dash="dash", line_color="rgba(229,231,235,0.5)")
    _line_layout(fig2, "Score, rolling 20 games")
    fig2.update_yaxes(range=[0, 1], tickformat=".0%")
    _plot(fig2)

    st.markdown("#### " + t("goals"))
    st.caption("Goals are saved in the page address: bookmark this page to keep them.")
    for tc in sorted(d["time_class"].unique()):
        s = d[d["time_class"] == tc].sort_values("date_utc")
        if len(s) < 15:
            continue
        current = int(s["user_rating"].iloc[-1])
        goal = int(st.number_input(f"{tc.title()} goal", 100, 3500, _goal_default(tc, current), step=25, key=f"goal_{tc}"))
        st.query_params[f"goal_{tc}"] = str(goal)
        st.progress(min(1.0, max(0.0, current / goal)), text=f"{tc.title()}: {current} / {goal}")
        recent = s.tail(80)
        slope = float(np.polyfit(np.arange(len(recent)), recent["user_rating"].to_numpy(dtype=float), 1)[0])
        if current >= goal:
            st.success("Goal reached!")
        elif slope > 0.05:
            st.caption(f"At your recent trend (+{slope:.2f} rating/game) that is roughly {int((goal - current) / slope)} games away. A rough linear estimate.")
        else:
            st.caption("Your recent trend is flat or falling, so no honest estimate yet.")


# --------------------------------------------------------------- Training plan
def render_training_plan(g: pd.DataFrame, username: str) -> None:
    st.markdown("### " + t("plan_title"))
    st.caption("Built from your own data. Run the Coach Report first for tactical and phase advice.")
    data = st.session_state.get("coach")
    patterns = analysis.error_patterns(data["moves"]) if data and data["user"] == username and not data["moves"].empty else None
    plan = training.build_plan(insights.generate_insights(g), patterns, training.weak_openings(g))
    for it in plan:
        _card(f"{it['day']}: {it['title']}", it["detail"], "info", link=it["link"])
    if patterns is None:
        st.info("Run the Coach Report to add personal tactical drills to this plan.")


# --------------------------------------------------------------------- Compare
@st.cache_data(show_spinner=False, ttl=600)
def _rival_games(username: str) -> pd.DataFrame:
    return fetch_player_games(username, max_games=300, months=6)


def _summary(g: pd.DataFrame) -> dict:
    cp = insights.clock_profile(g)
    tp = insights.tilt_profile(g)
    col = insights.color_profile(g).set_index("user_color")["score"] if not g.empty else pd.Series(dtype=float)
    return {
        "Games": len(g),
        "Score": g["score"].mean(),
        "Score as White": col.get("white", np.nan),
        "Score as Black": col.get("black", np.nan),
        "Games per session": insights.session_profile(g)["avg_games"],
        "Score after a loss": float(tp["table"].set_index("bucket")["score"].get("1", np.nan)) if not tp["table"].empty else np.nan,
        "Time-scramble rate": cp.get("scramble_rate", np.nan),
        "Avg rating gap to opponents": g["rating_diff"].mean(),
    }


def render_compare(my_enriched: pd.DataFrame, username: str) -> None:
    st.markdown("### " + t("compare_title"))
    rival = st.text_input(t("compare_prompt"), key="rival_name").strip()
    if not rival:
        st.info("Enter a friend or a stronger player to see your habits side by side.")
        return
    if rival.lower() == username.lower():
        st.info("That is you. Pick someone else.")
        return
    try:
        with st.spinner(f"Loading {rival}'s games…"):
            df = _rival_games(rival)
    except ChessComAPIError as exc:
        st.error(f"Could not load {rival}: {exc}")
        return
    if df.empty:
        st.warning(f"No recent games found for {rival}.")
        return
    other = insights.enrich_games(df, rival)
    if len(other) < 10:
        st.warning("Not enough games to compare.")
        return

    a, b = _summary(my_enriched), _summary(other)
    table = pd.DataFrame({"Metric": list(a.keys()), username: list(a.values()), rival: list(b.values())})

    def _fmt(metric: str, v) -> str:
        if v != v:
            return "n/a"
        if metric in ("Games",):
            return str(int(v))
        if metric in ("Games per session",):
            return f"{v:.1f}"
        if metric.startswith("Avg rating"):
            return f"{v:+.0f}"
        return f"{v:.0%}"

    show = table.copy()
    for col in (username, rival):
        show[col] = [_fmt(m, v) for m, v in zip(table["Metric"], table[col])]
    st.dataframe(show, hide_index=True, width="stretch")

    for_chart = [
        (tc, my_enriched[my_enriched["time_class"] == tc]["score"].mean(), other[other["time_class"] == tc]["score"].mean())
        for tc in sorted(set(my_enriched["time_class"]) & set(other["time_class"]))
    ]
    if for_chart:
        fig = go.Figure()
        fig.add_bar(name=username, x=[x[0] for x in for_chart], y=[x[1] for x in for_chart], marker_color=CYAN)
        fig.add_bar(name=rival, x=[x[0] for x in for_chart], y=[x[2] for x in for_chart], marker_color=GREY)
        _line_layout(fig, "Score by time control")
        fig.update_yaxes(range=[0, 1], tickformat=".0%")
        _plot(fig)
    st.caption("Both players' public games from the last 6 months (up to 300).")
