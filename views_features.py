"""Pages for the three signature tools: Elo Ledger, Play Now and Opening Check."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import actions
from ga import queue_event
import analytics
import html
import insights
import ledger
import opening_eval
import readiness
import home
import scout
import share_card
import weekly
from uci import UciEngine
from views_insights import CYAN, GREEN, GREY, RED, _card

LIGHT = {
    "red": ("#EF4444", "Take a break", "Your own history says this is a bad moment to start another game."),
    "green": ("#10B981", "Good to go", "Nothing in your history says this moment is worse than usual for you."),
    "grey": ("#64748B", "Not enough evidence", "Your history does not contain enough comparable games to judge this moment."),
}


def _plot(fig: go.Figure) -> None:
    st.markdown('<div class="klimate-card-plot">', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)


def _style(fig: go.Figure, title: str, height: int = 340) -> None:
    fig.update_layout(title=dict(text=title, font=dict(color="#F8FAFC", size=16)), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#E5E7EB"), height=height, margin=dict(l=20, r=20, t=50, b=20))


# ------------------------------------------------------------------ Elo Ledger
def render_elo_ledger(g: pd.DataFrame, timezone: str) -> None:
    st.markdown("### 🪙 Elo Ledger")
    st.caption("What your habits actually cost or earn, in real Chess.com rating points. Each game's rating change is measured "
               "from your published ratings (this rating minus the previous one in the same time control), not estimated.")
    res = ledger.ledger(g, timezone)
    s, table = res["summary"], res["table"]
    if s["usable_games"] < 60 or table.empty:
        st.info("The ledger needs at least 60 rated games with a measurable rating change. Load more history in the landing page options.")
        return
    c = st.columns(3)
    c[0].metric("Games with a measured change", f"{s['usable_games']} of {s['rated_games']}")
    c[1].metric("Net rating change", f"{s['net_points']:+.0f}")
    c[2].metric("Average per game", f"{s['mean_per_game']:+.2f}")

    judged = table[table["enough"]]
    if not judged.empty:
        fig = go.Figure(go.Bar(
            y=judged["situation"], x=judged["difference"], orientation="h",
            marker_color=[RED if v < 0 else GREEN for v in judged["difference"]],
            error_x=dict(type="data", symmetric=False, array=judged["diff_hi"] - judged["difference"],
                         arrayminus=judged["difference"] - judged["diff_lo"], color="rgba(229,231,235,0.6)"),
            text=[f"{d:+.2f}" for d in judged["difference"]], textposition="outside", cliponaxis=False,
        ))
        fig.add_vline(x=0, line_color="rgba(229,231,235,0.5)")
        _style(fig, "Rating points per game in this situation, compared with all other games (95% interval)", 360)
        fig.update_layout(margin=dict(l=20, r=40, t=60, b=20))
        fig.update_yaxes(autorange="reversed")
        _plot(fig)

    reliable = judged[judged["reliable"]]
    if reliable.empty:
        _card("No habit has a reliable rating cost yet",
              "None of the situations differs from your other games by more than chance would explain (a strict bar is used because "
              "several situations are tested at once). Intervals crossing zero in the chart mean the same.", "info")
    for r in reliable.itertuples():
        worse = r.difference < 0
        _card(f"{r.situation}: {r.difference:+.2f} points per game",
              f"Over {r.games} games that is {r.points_vs_normal:+.0f} rating points compared with how you do in other games.",
              "warn" if worse else "good")

    show = judged.assign(
        Situation=judged["situation"], Games=judged["games"], **{"Avg here": judged["mean_in"].map("{:+.2f}".format),
                                                                    "Avg elsewhere": judged["mean_out"].map("{:+.2f}".format),
                                                                    "Difference": judged["difference"].map("{:+.2f}".format),
                                                                    "Total vs normal": judged["points_vs_normal"].map("{:+.0f}".format),
                                                                    "Verdict": judged["reliable"].map({True: "reliable", False: "within chance"})})
    st.dataframe(show[["Situation", "Games", "Avg here", "Avg elsewhere", "Difference", "Total vs normal", "Verdict"]], hide_index=True, width="stretch")
    st.caption("Differences show association, not proof of cause. The situations overlap, so do not add their totals together. "
               "Games where an unseen game may sit between two published ratings are left out.")


# -------------------------------------------------------------------- Play Now
def render_play_now(g: pd.DataFrame, username: str, timezone: str, refresh) -> None:
    st.markdown("### ⚡ Play Now")
    st.caption("Should you start another game right now? Judged only by how YOU have performed in the same situation before.")
    if st.button("Refresh my latest games", key="playnow_refresh"):
        with st.spinner("Loading your latest games…"):
            refresh()
        st.rerun()
    if len(g) < 60:
        st.info("Needs at least 60 games of history to compare situations.")
        return
    now = pd.Timestamp.now(tz="UTC")
    state = readiness.current_state(g, now, timezone)
    res = readiness.assess(g, state, timezone)
    colour, headline, sub = LIGHT[res["light"]]

    st.markdown(
        f"<div style='background:#1E293B;border-left:8px solid {colour};border-radius:12px;padding:1.2rem 1.4rem;margin:0.8rem 0;'>"
        f"<div style='font-size:1.6rem;font-weight:800;color:{colour};'>{headline}</div>"
        f"<div style='color:#CBD5E1;margin-top:0.3rem;'>{sub}</div></div>", unsafe_allow_html=True)

    if state["in_session"]:
        st.write(f"Your last game ended **{state['minutes_since_last']:.0f} minutes ago** ({state['last_result']}). This would be game "
                 f"**{state['next_game_no']}** of the session, with **{state['losses_in_row']} loss(es) in a row**.")
    else:
        st.write("You are not in a session (your last game ended more than 30 minutes ago), so this would be a **fresh start**.")

    for c in res["checks"]:
        if not c["enough"]:
            st.caption(f"• {c['label']}: only {c['n']} comparable games in your history, too few to judge.")
            continue
        verdict = "worse than usual" if c.get("worse") else ("better than usual" if c.get("better") else "no reliable difference")
        pts = f", rating change {c['points_in']:+.2f} vs {c['points_out']:+.2f} per game" if "points_in" in c else ""
        st.markdown(f"• **{c['label']}** ({c['n']} games): score {c['score_in']:.0%} vs {c['score_out']:.0%} elsewhere{pts}. *{verdict}.*")

    tp = insights.tilt_profile(g)
    if tp["stop_loss_after"]:
        st.info(f"Your personal stop-loss: after {tp['stop_loss_after']} losses in a row your results drop significantly.")
    st.caption("This is guidance from your own data, not a guarantee. A grey light means the data cannot say, not that it is safe.")


# --------------------------------------------------------------- Opening Check
def _engine_eval_factory(engine: UciEngine, depth: int = 10):
    cache: dict = {}

    def evaluate(fen: str):
        if fen not in cache:
            cp, _ = engine.analyse(fen, depth)
            cache[fen] = None if cp is None else cp / 100.0
        return cache[fen]

    return evaluate


def render_opening_check(games_df: pd.DataFrame, username: str) -> None:
    st.markdown("### 📖 Opening Check")
    st.caption("How good is your position after 10 moves in each opening, as White and as Black? This separates opening trouble "
               "from middlegame and endgame trouble, which win/loss results cannot do.")
    path = analytics._find_stockfish()
    if not path:
        st.info("This page needs a Stockfish engine, which is installed on the live site (set STOCKFISH_PATH to use it locally).")
        return
    if st.button("Evaluate my openings", type="primary", key="opening_eval_run"):
        bar = st.progress(0.0, text="Evaluating…")
        engine = UciEngine(path)
        try:
            data = opening_eval.collect(games_df, username, _engine_eval_factory(engine),
                                        progress=lambda d, t: bar.progress(d / t, text=f"Evaluated {d}/{t} games"))
        finally:
            engine.close()
            bar.empty()
        st.session_state["opening_eval"] = {"user": username, "data": data}
    store = st.session_state.get("opening_eval")
    if not store or store["user"] != username:
        st.info("Press the button to evaluate your most recent 400 games (about 15 seconds).")
        return
    data = store["data"]
    rep = opening_eval.report(data)
    if rep.empty:
        st.warning(f"No opening has {opening_eval.MIN_GAMES}+ evaluated games for one colour yet.")
        return
    st.caption(f"Based on {len(data)} games. Evaluations are from your side, in pawns, after move 10 (positive = you are better), "
               "capped at ±5 so one crushing game does not dominate.")

    labels = [f"{o} ({c}, n={n})" for o, c, n in zip(rep["opening"], rep["color"], rep["games"])]
    fig = go.Figure(go.Bar(
        y=labels, x=rep["eval"], orientation="h",
        marker_color=[RED if "Opening problem" in v else (GREEN if "Strong" in v else (CYAN if "Later" in v else GREY)) for v in rep["verdict"]],
        error_x=dict(type="data", symmetric=False, array=rep["eval_hi"] - rep["eval"], arrayminus=rep["eval"] - rep["eval_lo"],
                     color="rgba(229,231,235,0.6)"),
    ))
    fig.add_vline(x=0, line_color="rgba(229,231,235,0.5)")
    _style(fig, "Average evaluation after move 10 (95% interval)", max(300, 40 * len(rep) + 120))
    fig.update_yaxes(autorange="reversed")
    _plot(fig)

    for r in rep.itertuples():
        if not r.verdict.startswith("Within"):
            tone = "warn" if ("problem" in r.verdict) else "good"
            _card(f"{r.opening} as {r.color}: {r.verdict}",
                  f"{r.games} games. Average evaluation after move 10: {r.eval:+.2f} (overall {data['eval'].mean():+.2f}). "
                  f"Score: {r.score:.0%} (overall {data['score'].mean():.0%}).", tone)
    if all(v.startswith("Within") for v in rep["verdict"]):
        _card("No opening stands out", "Every opening is within the normal range of your own openings. Intervals show how uncertain each average still is.", "info")
    table = rep.assign(Opening=rep["opening"], Colour=rep["color"], Games=rep["games"], **{"After move 10": rep["eval"].map("{:+.2f}".format),
                       "Score": rep["score"].map("{:.0%}".format), "Verdict": rep["verdict"]})
    st.dataframe(table[["Opening", "Colour", "Games", "After move 10", "Score", "Verdict"]], hide_index=True, width="stretch")
    st.caption("Evaluations come from Stockfish at a fixed depth. Openings with few games have wide intervals, so treat them as hints.")


# --------------------------------------------------------------- Action Center
def render_action_center(g: pd.DataFrame, g_full: pd.DataFrame, username: str, timezone: str) -> None:
    """Top of the Overview: the three things most worth doing next, from the player's own evidence."""
    st.markdown("### 🎯 Your next steps")
    if len(g) < 30:
        st.info("Load at least 30 games to get personal next steps.")
        return
    store = st.session_state.get("opening_eval")
    report = opening_eval.report(store["data"]) if store and store.get("user") == username else None
    light, in_session = "grey", False
    if len(g_full) >= 60:
        state = readiness.current_state(g_full, pd.Timestamp.now(tz="UTC"), timezone)
        light, in_session = readiness.assess(g_full, state, timezone)["light"], bool(state["in_session"])
    todo = actions.build_actions(insights.generate_insights(g), ledger.ledger(g, timezone)["table"], light, report, in_session, len(g))
    colours = {"warn": "#F59E0B", "info": "#06B6D4", "good": "#10B981"}
    for i, a in enumerate(todo, start=1):
        st.markdown(
            f"<div style='display:flex;gap:14px;align-items:flex-start;background:#1E293B;border:1px solid #334155;"
            f"border-radius:12px;padding:0.9rem 1.1rem;margin:0.5rem 0;'>"
            f"<div style='min-width:30px;height:30px;border-radius:50%;background:{colours[a['tone']]};color:#0F172A;font-weight:800;"
            f"display:flex;align-items:center;justify-content:center;'>{i}</div>"
            f"<div><div style='font-weight:700;color:#F8FAFC;'>{html.escape(a['title'])}</div>"
            f"<div style='color:#CBD5E1;margin-top:0.2rem;'>{html.escape(a['detail'])}</div>"
            f"<div style='color:#06B6D4;font-size:0.82rem;margin-top:0.35rem;'>Open in the sidebar: {html.escape(a['where'])}</div></div></div>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------- Weekly Report
def _delta(now_v: float, prev_v: float, fmt: str, suffix: str = "") -> str:
    if prev_v != prev_v or now_v != now_v:
        return "no previous week"
    d = now_v - prev_v
    return f"{d:{fmt}}{suffix} vs last week"


def render_weekly(g: pd.DataFrame, username: str, timezone: str) -> None:
    st.markdown("### 🗓️ Weekly Report")
    if g.empty:
        st.info("No games loaded.")
        return
    rep = weekly.weekly_report(g, pd.Timestamp.now(tz="UTC"))
    cur, prev, end = rep["this"], rep["previous"], rep["anchor"]
    start = end - 7 * weekly.DAY
    period = f"{start.tz_convert(timezone):%b %d} - {end.tz_convert(timezone):%b %d, %Y}"
    st.caption(f"Last 7 days of activity: {period} (compared with the 7 days before).")
    if cur["games"] == 0:
        st.info("No games in this period.")
        return

    c = st.columns(4)
    c[0].metric("Games", cur["games"], f"{cur['games'] - prev['games']:+d} vs last week")
    c[1].metric("Score", f"{cur['score']:.0%}", _delta(cur["score"] * 100, prev["score"] * 100, "+.0f", " pts"))
    known = cur["known_changes"] >= max(1, cur["games"] // 2)
    c[2].metric("Rating change", f"{cur['rating_change']:+.0f}" if known else "n/a",
                _delta(cur["rating_change"], prev["rating_change"], "+.0f") if known and prev["known_changes"] else None,
                help="Sum of the measured rating changes of games in this period.")
    c[3].metric("Time played", f"{cur['minutes'] / 60:.1f} h", _delta(cur["minutes"] / 60, prev["minutes"] / 60, "+.1f", " h"))

    daily = rep["daily"]
    if not daily.empty:
        fig = go.Figure(go.Bar(x=daily["day"], y=daily["rating_change"], marker_color=[GREEN if v >= 0 else RED for v in daily["rating_change"]],
                               text=[f"{int(n)} games" for n in daily["games"]], textposition="outside", cliponaxis=False))
        _style(fig, "Rating change per day", 320)
        fig.update_yaxes(gridcolor="rgba(148,163,184,0.2)")
        _plot(fig)

    st.markdown("#### 🛑 Your stop-loss rule")
    tp = insights.tilt_profile(g)
    default = int(tp["stop_loss_after"] or 3)
    n_rule = int(st.number_input("Stop after this many losses in a row", 1, 6, default, key="weekly_rule",
                                 help="Defaults to your personal stop-loss when your history shows one, otherwise 3."))
    now_part = weekly.rule_adherence(rep["games_frame"], n_rule)
    all_part = weekly.rule_adherence(g, n_rule)
    if now_part["reached"] == 0:
        st.success(f"This week you never lost {n_rule} games in a row within a session, so the rule did not come up.")
    else:
        pct = now_part["adherence"]
        (st.success if pct >= 0.5 else st.warning)(
            f"This week you hit {n_rule} losses in a row in {now_part['reached']} session(s) and stopped in {now_part['stopped']} of them ({pct:.0%}).")
    cont = all_part["continued_games"]
    if all_part["reached"] >= 5 and len(cont) >= 10 and cont["rating_change"].notna().sum() >= 10:
        rest = g.drop(cont.index)["rating_change"].dropna()
        st.caption(f"Over all loaded games, the {len(cont)} games you played after {n_rule} straight losses changed your rating by "
                   f"{cont['rating_change'].dropna().mean():+.2f} points on average, versus {rest.mean():+.2f} for all other games. "
                   f"You stopped in {all_part['stopped']} of {all_part['reached']} sessions that reached the rule.")

    st.markdown("#### Highlights")
    games_frame = rep["games_frame"]
    big = games_frame.groupby("session_id").size()
    st.write(f"• Longest session: **{int(big.max())} games**.")
    busy = daily.loc[daily["games"].idxmax()] if not daily.empty else None
    if busy is not None:
        st.write(f"• Busiest day: **{busy['day']:%a %b %d}** with {int(busy['games'])} games.")
    ok = daily[daily["games"] >= 3]
    if not ok.empty:
        best = ok.loc[ok["score"].idxmax()]
        st.write(f"• Best day (3+ games): **{best['day']:%a %b %d}**, score {best['score']:.0%}.")

    tiles = [("Games", cur["games"], f"{cur['games'] - prev['games']:+d}"), ("Score", f"{cur['score']:.0%}", _delta(cur["score"] * 100, prev["score"] * 100, "+.0f", " pts").split(" vs")[0]),
             ("Rating", f"{cur['rating_change']:+.0f}" if known else "n/a", ""), ("Hours played", f"{cur['minutes'] / 60:.1f}", "")]
    st.download_button("⬇️ Download weekly card (PNG)", share_card.render_weekly_png(username, period, tiles),
                       file_name=f"klimate-week-{username}.png", mime="image/png")


# ---------------------------------------------------------------- Opponent Scout
def render_scout(mine: pd.DataFrame, raw_games: pd.DataFrame, username: str, timezone: str) -> None:
    from data_engine import ChessComAPIError, fetch_games

    st.markdown("### 🔭 Opponent Scout")
    st.caption("Type the Chess.com username of someone you are about to play. Klimate reads their public games and builds a preparation "
               "sheet: what they play, where they are weak, how they handle the clock. Nothing is stored.")
    c = st.columns([3, 1])
    opp_name = c[0].text_input("Opponent's Chess.com username", key="scout_user", placeholder="e.g. their username")
    months = c[1].selectbox("History", [1, 3, 6], index=1, format_func=lambda m: f"{m} month{'s' if m > 1 else ''}", key="scout_months")
    if st.button("Scout this player", key="scout_btn") and opp_name.strip():
        queue_event("scout_run")
        bar = st.progress(0.0, text="Reading their games...")
        try:
            raw = fetch_games(opp_name.strip(), max_games=400, months=months, progress=lambda d, n: bar.progress(d / n, text="Reading their games..."))
        except ChessComAPIError as exc:
            bar.empty()
            st.error(f"Could not load games for {opp_name.strip()}: {exc}")
            return
        bar.empty()
        if raw.empty:
            st.warning(f"No standard games found for {opp_name.strip()} in this period.")
            return
        st.session_state["scout"] = {"user": opp_name.strip(), "enriched": insights.enrich_games(raw, opp_name.strip())}
    data = st.session_state.get("scout")
    if not data:
        st.info("Enter a username and press the button.")
        return

    opp, name = data["enriched"], data["user"]
    rep = scout.scout_report(opp, mine)
    if not rep["n"]:
        st.warning("No games to analyze.")
        return
    s = rep["summary"]
    st.markdown(f"#### {name}")
    m = st.columns(4)
    m[0].metric(f"Rating ({rep['main_class']})", f"{rep['rating']:.0f}" if rep["rating"] == rep["rating"] else "n/a",
                f"{rep['rating'] - rep['rating_30d_ago']:+.0f} in 30 days" if rep["rating_30d_ago"] == rep["rating_30d_ago"] else None)
    m[1].metric("Games read", rep["n"])
    m[2].metric("Score", f"{s['score']:.0%}", f"{s['wins']}W {s['draws']}D {s['losses']}L", delta_color="off")
    h2h = scout.head_to_head(raw_games, username, name)
    m[3].metric("Your record vs them", f"{h2h['wins']}W {h2h['draws']}D {h2h['losses']}L" if h2h["n"] else "no games yet")
    if not rep["enough"]:
        st.warning(f"Only {rep['n']} games found (at least {scout.MIN_GAMES} are needed for behavioural claims). Openings below are shown with their sample sizes; treat them as hints.")

    st.markdown("#### Preparation sheet")
    if not rep["prep"]:
        _card("Not enough data to prepare against", "Try a longer history, or this player has played very few standard games.", "info")
    for item in rep["prep"]:
        _card(item["title"], item["detail"], item["tone"])

    cols = st.columns(2)
    for col, colour in zip(cols, ("white", "black")):
        ops = rep[colour]
        col.markdown(f"**Openings as {colour.title()}**")
        if ops.empty:
            col.caption(f"No opening played {scout.MIN_OPENING_GAMES}+ times as {colour.title()}.")
            continue
        show = pd.DataFrame({"Opening": ops["opening"], "Games": ops["games"], "Share": ops["share"].map("{:.0%}".format),
                             "Their score": ops["score"].map("{:.0%}".format),
                             "Your score": [f"{sc:.0%} ({n})" if n >= 3 else "-" for sc, n in zip(ops["my_score"], ops["my_games"])]})
        col.dataframe(show, hide_index=True, width="stretch")
    st.caption("'Your score' is your own result (and game count) in games that featured the same opening on the other side of the board. "
               "Intervals and sample sizes decide what is called a weakness; a soft spot needs 5+ games clearly below their overall score.")

    hours = scout.peak_hours(insights.hourly_profile(opp, timezone))
    if hours:
        st.caption("They start most games around " + ", ".join(f"{h:02d}:00" for h in hours) + f" ({timezone}).")


# ---------------------------------------------------------------------- Home hero
def render_home_hero(g: pd.DataFrame, username: str, timezone: str) -> None:
    """First thing a player sees: where they stand, their biggest leak and strength, in a few seconds."""
    head = home.rating_headline(g)
    summ = insights.overall_summary(g)
    ledger_table = ledger.ledger(g, timezone)["table"] if len(g) >= 60 else None
    leak = home.biggest_leak(g, ledger_table) if len(g) >= 30 else None
    strength = home.biggest_strength(g, timezone) if len(g) >= 30 else None

    st.markdown(
        f"<div class='klimate-hero'><div class='hero-kicker'>YOUR CHESS IN 30 SECONDS</div>"
        f"<div class='hero-title'>Hi {html.escape(username)}, here is what your {summ.get('n', 0)} games say.</div></div>",
        unsafe_allow_html=True)
    cols = st.columns(3)
    if head:
        change = f"{head['change_30d']:+.0f} in 30 days" if head["change_30d"] == head["change_30d"] else "no 30-day history yet"
        sub_txt = f"{head['time_class']} · peak {head['peak']:.0f} · {change}"
        cols[0].markdown(f"<div class='hero-card'><div class='hc-label'>WHERE YOU STAND</div><div class='hc-value'>{head['rating']:.0f}</div>"
                         f"<div class='hc-sub'>{html.escape(sub_txt)}</div></div>", unsafe_allow_html=True)
    else:
        cols[0].markdown("<div class='hero-card'><div class='hc-label'>WHERE YOU STAND</div><div class='hc-value'>-</div>"
                         "<div class='hc-sub'>no rated games loaded</div></div>", unsafe_allow_html=True)
    for col, label, item, tone, empty in (
            (cols[1], "YOUR BIGGEST LEAK", leak, "leak", "No habit stands out as costly yet. That is good news, or a sign more games are needed."),
            (cols[2], "YOUR BIGGEST STRENGTH", strength, "strength", "No reliable strength yet. It needs more games to rule out luck.")):
        if item:
            col.markdown(f"<div class='hero-card {tone}'><div class='hc-label'>{label}</div><div class='hc-title'>{html.escape(item['title'])}</div>"
                         f"<div class='hc-sub'>{html.escape(item['detail'])}</div>"
                         f"<div class='hc-link'>Details: {html.escape(item['where'])}</div></div>", unsafe_allow_html=True)
        else:
            col.markdown(f"<div class='hero-card {tone}'><div class='hc-label'>{label}</div><div class='hc-sub'>{empty}</div></div>",
                         unsafe_allow_html=True)
