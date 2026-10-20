"""Streamlit pages: Coach Report, Progress, Training Plan, Compare."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analysis
import analytics
import coach
import insights
import ledger
import llm
import opening_eval
import trainer
import training
from strings import t
from metrics import linear_trend
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
    st.caption("Runs Stockfish on your recent games and finds *where* and *how* you lose points. A move counts as an inaccuracy when it gives "
               "away 10+ points of win chance, a mistake 20+, a blunder 30+. Accuracy is the average per-move accuracy (Lichess's formula).")
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

    _render_conversion(moves, games)

    if st.button("Write my coaching summary", key="coach_summary_btn"):
        with st.spinner("Writing…"):
            st.session_state["coach_summary"] = llm.pattern_summary(coach.stats_text(moves, games))
    if st.session_state.get("coach_summary"):
        st.info(st.session_state["coach_summary"])


def _render_conversion(moves: pd.DataFrame, games: pd.DataFrame) -> None:
    """Converting winning positions and fighting back from lost ones."""
    conv = analysis.conversion_profile(moves, games)
    st.markdown("#### Converting advantages and fighting back")
    c = st.columns(2)
    if conv["adv_n"]:
        c[0].metric("Winning positions converted", f"{conv['conv_rate']:.0%}",
                    f"{conv['adv_wins']} of {conv['adv_n']} games reaching 80%+ win chance",
                    help=f"95% interval {conv['conv_lo']:.0%} to {conv['conv_hi']:.0%}. Wins only; draws count as not converted.")
    else:
        c[0].metric("Winning positions converted", "n/a", "no game reached 80%+ yet")
    if conv["res_n"]:
        c[1].metric("Lost positions saved", f"{conv['save_rate']:.0%}",
                    f"{conv['res_wins'] + conv['res_draws']} of {conv['res_n']} games falling to 20% or less",
                    help=f"95% interval {conv['save_lo']:.0%} to {conv['save_hi']:.0%}. A draw or a win counts as saved.")
    else:
        c[1].metric("Lost positions saved", "n/a", "no game fell to 20% or less yet")
    col = conv["collapses"]
    if col is not None and len(col):
        st.caption("Advantages that were not converted. 'Turning point' is the first of your moves after the peak that left you below 50%.")
        show = col.assign(
            Game=[f"[open]({u})" if u else "" for u in col.get("url", [""] * len(col))],
            Peak=col["peak"].map("{:.0f}%".format), Result=col["result"],
            **{"Turning point": [f"move {int(p) // 2 + 1}: {m} ({ph}, {lb})" if m else "gradual" for p, m, ph, lb in zip(col["turn_ply"].fillna(0), col["move"], col["phase"], col["label"])]},
        )
        st.dataframe(show[["Peak", "Result", "Turning point", "Game"]], hide_index=True, width="stretch",
                     column_config={"Game": st.column_config.LinkColumn("Game", display_text="open")})
        if col["phase"].notna().sum() >= 3:
            top = col["phase"].value_counts()
            st.write(f"Most of your throws happen in the **{top.index[0]}** ({int(top.iloc[0])} of {int(col['phase'].notna().sum())}).")


# -------------------------------------------------------------------- Progress
def _goal_default(tc: str, current: int) -> int:
    raw = st.query_params.get(f"goal_{tc}")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return current + 100


def render_progress(g: pd.DataFrame, username: str) -> None:
    st.markdown("### " + t("progress_title"))
    d = g.dropna(subset=["rating_after"])
    if len(d) < 10:
        st.info("Not enough rated games yet. Load more history in the filters.")
        return

    live = analytics.get_real_time_ratings(username)
    st.caption("Each point is your rating right after that game. 'Current' in the goals below is your live rating.")
    fig = go.Figure()
    for tc, color in zip(sorted(d["time_class"].unique()), [CYAN, GREEN, "#F59E0B", GREY]):
        s = d[d["time_class"] == tc].sort_values("date_utc")
        if len(s) >= 5:
            fig.add_trace(go.Scatter(x=s["date_utc"], y=s["rating_after"], mode="lines", name=tc, line=dict(color=color)))
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
        current = int(live[tc]) if isinstance(live.get(tc), int) else int(s["rating_after"].iloc[-1])
        goal = int(st.number_input(f"{tc.title()} goal", 100, 3500, _goal_default(tc, current), step=25, key=f"goal_{tc}"))
        st.query_params[f"goal_{tc}"] = str(goal)
        st.progress(min(1.0, max(0.0, current / goal)), text=f"{tc.title()}: {current} / {goal}")
        slope, se = linear_trend(s.tail(80)["rating_after"].to_numpy(dtype=float))
        reliable = slope == slope and se == se and se > 0 and slope / se >= 2.0
        if current >= goal:
            st.success("Goal reached!")
        elif reliable and slope > 0:
            st.caption(f"Your rating has been rising by about {slope:.2f} per game over the last {min(80, len(s))} games (a statistically "
                       f"reliable trend), which would reach the goal in roughly {int((goal - current) / slope)} games if it continues. A rough estimate.")
        else:
            st.caption("No statistically reliable upward trend in your recent games, so no estimate is shown.")


# --------------------------------------------------------------- Training plan
def render_training_plan(g: pd.DataFrame, username: str) -> None:
    st.markdown("### " + t("plan_title"))
    st.caption("Built from your own data. Run the Coach Report first for tactical and phase advice.")
    data = st.session_state.get("coach")
    patterns = analysis.error_patterns(data["moves"]) if data and data["user"] == username and not data["moves"].empty else None
    store = st.session_state.get("opening_eval")
    opening_report = opening_eval.report(store["data"]) if store and store["user"] == username else None
    ledger_table = ledger.ledger(g, st.session_state.get("cognitive_tz", "UTC"))["table"]
    conv = analysis.conversion_profile(data["moves"], data["games"]) if data and data["user"] == username and not data["games"].empty else None
    plan = training.build_plan(insights.generate_insights(g), patterns, training.weak_openings(g), opening_report, ledger_table, conv)
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

    def _window(x: pd.DataFrame) -> str:
        return f"{len(x)} games, {x['date_utc'].min():%Y-%m-%d} to {x['date_utc'].max():%Y-%m-%d}"

    st.caption(f"{username}: {_window(my_enriched)}  ·  {rival}: {_window(other)}")
    span_a = (my_enriched["date_utc"].max() - my_enriched["date_utc"].min()).days + 1
    span_b = (other["date_utc"].max() - other["date_utc"].min()).days + 1
    if max(span_a, span_b) > 3 * max(1, min(span_a, span_b)):
        st.warning("The two samples cover very different periods (the number of games is capped), so differences may reflect "
                   "when the games were played, not only how the players play.")
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
    st.caption("Public games, standard chess only, from the last 6 months (at most 300 per player).")


# -------------------------------------------------------------- Blunder Trainer
def render_trainer(games_df: pd.DataFrame, username: str) -> None:
    import chess
    import chess.svg

    st.markdown("### 🧩 Blunder Trainer")
    st.caption("Puzzles made from YOUR own mistakes: the position before a move that cost you 20+ points of win chance. "
               "Find the move the engine prefers. Only moves are compared with Stockfish's top choice at a fixed depth; "
               "a different move can occasionally be just as good.")
    if not coach.stockfish_available():
        st.info("This page needs a local Stockfish engine, which is installed on the live site.")
        return
    state = st.session_state.get("trainer")
    if st.button("Build my puzzles" if not state else "Rebuild from my latest games", type="primary", key="trainer_build"):
        bar = st.progress(0.0, text="Finding your biggest mistakes...")
        puzzles = trainer.build_puzzles(
            games_df, username, lambda pgn: analytics.analyze_game_with_stockfish(pgn, 150, 10),
            progress=lambda d, n: bar.progress(d / n, text=f"Analyzed {d}/{n} games"))
        bar.empty()
        state = {"user": username, "puzzles": puzzles, "i": 0, "score": 0, "answered": 0, "checked": None}
        st.session_state["trainer"] = state
    if not state or state["user"] != username:
        st.info("Press the button. It reuses the engine results of the Coach Report where available.")
        return
    puzzles = state["puzzles"]
    if not puzzles:
        st.success("No mistake of 20+ points found in your latest analyzed games. Nothing to drill right now.")
        return
    i = min(state["i"], len(puzzles))
    if i >= len(puzzles):
        st.success(f"Done! You found the engine's move in {state['score']} of {state['answered']} puzzles.")
        return
    p = puzzles[i]
    options = trainer.make_options(p["fen"], p["best_uci"], p["played_uci"], seed=p["ply"] * 7 + i)
    board = chess.Board(p["fen"])
    st.progress(i / len(puzzles), text=f"Puzzle {i + 1} of {len(puzzles)} · score {state['score']}/{state['answered']}")
    checked = state["checked"]
    arrows = []
    if checked:
        for uci, colour in ((p["played_uci"], "#EF4444"), (p["best_uci"], "#10B981")):
            mv = chess.Move.from_uci(uci)
            arrows.append(chess.svg.Arrow(mv.from_square, mv.to_square, color=colour))
    c1, c2 = st.columns([1, 1])
    with c1:
        st.write(chess.svg.board(board=board, arrows=arrows, orientation=board.turn, size=360), unsafe_allow_html=True)
    with c2:
        st.markdown(f"**{'White' if board.turn else 'Black'} to move.** In your game you played a move here that gave away "
                    f"about {p['win_loss']:.0f}% of your winning chances. Which move would you play?")
        labels = {o["uci"]: o["san"] for o in options}
        pick = st.radio("Your move", list(labels), format_func=lambda u: labels[u], key=f"trainer_pick_{i}", disabled=bool(checked))
        if not checked:
            if st.button("Check my answer", key=f"trainer_check_{i}"):
                state["checked"] = pick
                state["answered"] += 1
                state["score"] += int(pick == p["best_uci"])
                st.rerun()
        else:
            if checked == p["best_uci"]:
                st.success(f"Correct. {p['best_san']} is the engine's move.")
            elif checked == p["played_uci"]:
                st.error(f"That is the move you played in the game ({p['san']}). The engine prefers {p['best_san']}.")
            else:
                st.warning(f"Not the engine's top choice. It prefers {p['best_san']}; in the game you played {p['san']}.")
            st.caption("Green arrow: engine's move. Red arrow: the move from your game.")
            if p.get("url"):
                st.markdown(f"[Open the game on Chess.com]({p['url']})")
            if st.button("Next puzzle", key=f"trainer_next_{i}"):
                state["i"], state["checked"] = i + 1, None
                st.rerun()
