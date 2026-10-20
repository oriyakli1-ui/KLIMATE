"""Klimate: chess psychology analytics. Streamlit entry point (routing only).

Run with:  streamlit run KLIMATEapp.py
Page code lives in ui_*.py and views_*.py; analysis code in insights.py, analysis.py, ledger.py and friends.
"""
from __future__ import annotations

import streamlit as st
from streamlit_option_menu import option_menu

import background
import insights
import nav
import coach
import views_coach
import views_features
import views_info
import views_insights
from data_engine import ChessComAPIError, fetch_games
from ga import flush_ga_events, inject_ga, queue_event
from strings import t
from ui_blindspots import render_strategic_blindspots
from ui_engine import render_engine_deep_dive
from ui_overview import render_cognitive_clock_chart, render_overview_page
from ui_spatial import render_spatial
from ui_style import inject_global_styles
from ui_wrapped import show_klimate_masterpiece

TIMEZONES = ["Asia/Jerusalem", "UTC", "Europe/London", "Europe/Paris", "America/New_York",
             "America/Los_Angeles", "Asia/Kolkata", "Asia/Tokyo"]
COLOUR_OPTIONS = ["All", "White", "Black"]
DEMO_PLAYERS = ["hikaru", "magnuscarlsen"]
VALUE_CARDS = [
    ("📏", "Measured, not guessed", "Every number is checked against the raw Chess.com data and shown with its uncertainty."),
    ("🪙", "Your habits in rating points", "See what tilt, late nights and time scrambles actually cost you."),
    ("🔒", "Free and private", "Reads your public games only. Nothing is stored."),
]


def _browser_timezone() -> str:
    """The visitor's own IANA timezone (Streamlit reads it from the browser), UTC if unknown."""
    return getattr(st.context, "timezone", None) or "UTC"


def _timezone_options() -> list[str]:
    mine = _browser_timezone()
    return [mine] + [z for z in TIMEZONES if z != mine]


def _tz() -> str:
    return st.session_state.get("cognitive_tz", _browser_timezone())


def _landing() -> None:
    """Landing page: what the tool does, username and history range."""
    _, logo_col, _ = st.columns([1, 2, 1])
    with logo_col:
        st.image("logo.png", width="stretch")
    st.markdown(
        "<p style='text-align: center; color: #D1D5DB; font-size: 1.2rem; "
        "font-weight: 300; margin-top: -15px; margin-bottom: 28px; letter-spacing: 1px;'>"
        f"{t('tagline')}</p>",
        unsafe_allow_html=True,
    )
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        username_input = st.text_input(t("username"), value=st.query_params.get("user", ""), placeholder=t("username_ph"))
        with st.expander(t("history")):
            months = st.select_slider(t("months_back"), options=[3, 6, 12, 24], value=6)
            max_games = st.select_slider(t("max_games"), options=[100, 300, 500, 1000], value=500)
        analyze_clicked = st.button(t("analyze"), width="stretch")
        st.caption("Press Enter or the button. Loading takes a few seconds; the first run for a new player can take up to a minute.")

    with col_center:
        st.markdown("<p style='text-align:center; color:#94A3B8; margin:14px 0 4px 0;'>No account handy? Try a public player:</p>", unsafe_allow_html=True)
        demo_cols = st.columns(len(DEMO_PLAYERS))
        demo_choice = next((name for col, name in zip(demo_cols, DEMO_PLAYERS) if col.button(name, key=f"demo_{name}", width="stretch")), None)

    st.markdown("<div style='height: 26px'></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for col, (icon, title, text) in zip(cols, VALUE_CARDS):
        col.markdown(
            f"<div class='klimate-value-card'><div class='vc-icon'>{icon}</div><div class='vc-title'>{title}</div>"
            f"<div class='vc-text'>{text}</div></div>", unsafe_allow_html=True)

    if analyze_clicked:
        queue_event("analyze_clicked", has_username=bool(username_input.strip()))
    if demo_choice:
        queue_event("demo_clicked", player=demo_choice)

    target = demo_choice or (username_input.strip() if analyze_clicked else "")
    if target:
        username = target
        bar = st.progress(0.0, text=t("loading"))
        quick_months, quick_max = (1 if months > 1 else months), min(max_games, 200)
        try:
            # Show the dashboard fast with the most recent games; the full history loads in the background.
            games_df = fetch_games(
                username, max_games=quick_max, months=quick_months,
                progress=lambda done, total: bar.progress(done / total, text=t("loading")),
            )
            background_history = quick_months < months or quick_max < max_games
            if games_df.empty and background_history:
                games_df = fetch_games(username, max_games=max_games, months=months,
                                       progress=lambda done, total: bar.progress(done / total, text=t("loading")))
                background_history = False
        except ChessComAPIError as exc:
            queue_event("analysis_failed", reason="api_error")
            bar.empty()
            st.error(t("err_fetch", user=username, err=exc))
        else:
            bar.empty()
            if games_df.empty:
                queue_event("analysis_failed", reason="no_games")
                st.warning(t("no_games", user=username))
            else:
                st.session_state["games_df"] = games_df
                st.session_state["enriched"] = insights.enrich_games(games_df, username)
                st.session_state["username"] = username
                st.session_state["fetch_params"] = {"max_games": quick_max if background_history else max_games,
                                                    "months": quick_months if background_history else months}
                st.session_state["data_loaded"] = True
                st.query_params["user"] = username
                if background_history:
                    key = f"history:{username.lower()}:{months}:{max_games}"
                    background.start(key, lambda progress, u=username: fetch_games(u, max_games=max_games, months=months, progress=progress))
                    st.session_state["history_job"] = {"key": key, "months": months, "max_games": max_games}
                queue_event("analysis_loaded", games_count=int(len(games_df)), phased=background_history)
                st.rerun()

    flush_ga_events()


def _sidebar(games_df, enriched, username: str):
    """Sidebar: wrapped button, grouped navigation, filters, export. Returns (page key, time classes, colour)."""
    labels = nav.group_labels()
    with st.sidebar:
        st.image("logo.png", width="stretch")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(t("wrapped_btn"), type="primary"):
            queue_event("wrapped_generated")
            show_klimate_masterpiece(username, enriched, games_df, _tz())
        group_label = st.radio("Section", list(labels), horizontal=True, key="nav_group", label_visibility="collapsed")
        group = labels[group_label]
        pages = nav.pages_of(group)
        page_labels = {t(f"nav_{key}"): key for key, _ in pages}
        label = option_menu(
            menu_title=None,
            options=list(page_labels),
            icons=[icon for _, icon in pages],
            # Must stay constant per menu: changing default_index between reruns remounts the component
            # and swallows later clicks. Each section has its own menu instance, so switching section
            # opens that section's first page.
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#0B1220"},
                "icon": {"color": "#06B6D4", "font-size": "17px"},
                "nav-link": {"font-size": "15px", "text-align": "left", "margin": "0px", "color": "#E5E7EB",
                             "--hover-color": "rgba(6, 182, 212, 0.15)"},
                "nav-link-selected": {"background-color": "#06B6D4", "font-weight": "bold", "color": "#0F172A"},
            },
        )
        with st.expander(t("filters")):
            available = sorted(set(games_df["time_class"].dropna()) - {""})
            time_classes = st.multiselect(t("time_control"), available, default=available, key="flt_time_classes")
            colour = st.radio(t("colour"), COLOUR_OPTIONS, horizontal=True, key="flt_color", format_func=lambda c: t(c.lower()))
            st.caption(t("games_loaded", n=len(games_df)))
        if st.button("Load someone else", key="reset_user"):
            for key in ("data_loaded", "games_df", "enriched", "username", "opening_eval", "coach", "coach_summary", "history_job", "coach_job"):
                st.session_state.pop(key, None)
            st.rerun()
    return page_labels[label], time_classes, colour


def _refresh_games(username: str) -> None:
    """Reload the newest games with the same settings as the first load."""
    params = st.session_state.get("fetch_params", {"max_games": 500, "months": 6})
    fresh = fetch_games(username, params["max_games"], params["months"])
    if not fresh.empty:
        st.session_state["games_df"] = fresh
        st.session_state["enriched"] = insights.enrich_games(fresh, username)


def _export_button(enriched_f, username: str) -> None:
    cols = [c for c in ("date_utc", "start_utc", "time_class", "rated", "user_color", "opening", "outcome", "score", "rating_after",
                        "rating_change", "user_rating", "opp_rating", "rating_diff", "session_id", "session_game_no", "losses_before",
                        "final_clock", "scramble") if c in enriched_f.columns]
    st.sidebar.download_button("⬇️ Download my data (CSV)", enriched_f[cols].to_csv(index=False).encode("utf-8"),
                               file_name=f"klimate-{username}.csv", mime="text/csv",
                               on_click=lambda: queue_event("data_exported"))


def _apply_history(username: str) -> None:
    """Swap in the full history once its background job has finished."""
    info = st.session_state.get("history_job")
    job = background.get(info["key"]) if info else None
    if job is None or job.status == "running":
        return
    st.session_state.pop("history_job", None)
    if job.status == "done" and job.result is not None and not job.result.empty:
        st.session_state["games_df"] = job.result
        st.session_state["enriched"] = insights.enrich_games(job.result, username)
        st.session_state["fetch_params"] = {"max_games": info["max_games"], "months": info["months"]}
        queue_event("history_loaded", games_count=int(len(job.result)))
        st.toast(f"Full history loaded: {len(job.result)} games.", icon="✅")
        st.rerun(scope="app")


def _apply_coach(username: str) -> None:
    info = st.session_state.get("coach_job")
    job = background.get(info["key"]) if info else None
    if job is None or job.status == "running":
        return
    st.session_state.pop("coach_job", None)
    if job.status == "done" and job.result is not None:
        moves, games = job.result
        if not games.empty and (st.session_state.get("coach") or {}).get("user") != username:
            st.session_state["coach"] = {"moves": moves, "games": games, "user": username, "n": len(games)}
            queue_event("coach_auto_ready", games_count=int(len(games)))
            st.toast("Engine analysis of your recent games is ready (Coach Report).", icon="🧠")


def _background_status(username: str) -> None:
    """One slim line while the full history or the engine analysis is still working (polls every 2 s)."""
    def tick() -> None:
        _apply_history(username)
        _apply_coach(username)
        lines = []
        for name, label in (("history_job", "Loading your older games"), ("coach_job", "Analyzing your recent games with Stockfish")):
            info = st.session_state.get(name)
            job = background.get(info["key"]) if info else None
            if job is not None and job.status == "running":
                lines.append(f"{label}{f' ({job.done}/{job.total})' if job.total else '...'}")
        if lines:
            st.caption("⏳ " + "  |  ".join(lines) + " - you can keep exploring.")

    active = any(st.session_state.get(k) for k in ("history_job", "coach_job"))
    st.fragment(run_every=2 if active else None)(tick)()


def _start_coach_job(all_games, username: str) -> None:
    """Begin the engine analysis automatically so the Coach Report is ready when the player gets there."""
    if st.session_state.get("coach_job") or (st.session_state.get("coach") or {}).get("user") == username:
        return
    if not coach.stockfish_available():
        return
    key = f"coach:{username.lower()}:{len(all_games)}"
    background.start(key, lambda progress: coach.analyze_recent(all_games, username, n=20, depth=10, progress=progress))
    st.session_state["coach_job"] = {"key": key}


def _dashboard() -> None:
    all_games = st.session_state["games_df"]
    username = st.session_state["username"]
    if "enriched" not in st.session_state:
        st.session_state["enriched"] = insights.enrich_games(all_games, username)
    page, time_classes, colour = _sidebar(all_games, st.session_state["enriched"], username)

    # Filters apply to every page. ``enriched`` is computed once per load (sessions and tilt
    # need the full timeline) and filtered like the raw games.
    enriched_f = insights.filter_enriched(st.session_state["enriched"], time_classes, colour)
    games_df = insights.filter_games(all_games, username, time_classes, colour)
    if games_df.empty:
        st.warning(t("no_match"))
        flush_ga_events()
        return
    _export_button(enriched_f, username)
    _start_coach_job(all_games, username)
    _background_status(username)

    if st.session_state.get("_last_page") != page:  # once per change, not on every rerun
        st.session_state["_last_page"] = page
        queue_event("page_selected", page_name=page)

    st.markdown(
        "<div style='margin-top: 45px; display: flex; align-items: center; gap: 10px; "
        "margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);'>"
        "<span style='font-size: 1.2rem; opacity: 0.8;'>♟️</span>"
        "<span style='font-weight: 700; color: #E2E8F0; letter-spacing: 2px; font-size: 1.1rem;'>KLIMATE</span>"
        f"<span style='color: #06B6D4; font-size: 0.85rem; font-weight: 600; letter-spacing: 1px;'>| {username.upper()}</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if page == "overview":
        views_features.render_home_hero(st.session_state["enriched"], username, _tz())
        views_features.render_action_center(enriched_f, st.session_state["enriched"], username, _tz())
        render_overview_page(enriched_f, username)
        views_insights.render_insights_panel(enriched_f)
    elif page == "clock":
        st.markdown("### Cognitive Performance (Time of Day)")
        tz = st.selectbox("Your timezone", _timezone_options(), index=0, key="cognitive_tz")
        render_cognitive_clock_chart(insights.hourly_profile(enriched_f, tz), tz)
    elif page == "spatial":
        render_spatial(games_df, username)
    elif page == "blindspots":
        render_strategic_blindspots(enriched_f, username)
    elif page == "behavior":
        views_insights.render_behavior_lab(enriched_f)
    elif page == "ledger":
        views_features.render_elo_ledger(enriched_f, _tz())
    elif page == "weekly":
        views_features.render_weekly(st.session_state["enriched"], username, _tz())
    elif page == "playnow":
        views_features.render_play_now(st.session_state["enriched"], username, _tz(), lambda: _refresh_games(username))
    elif page == "scout":
        views_features.render_scout(st.session_state["enriched"], all_games, username, _tz())
    elif page == "openingcheck":
        views_features.render_opening_check(games_df, username)
    elif page == "time":
        views_insights.render_time_management(enriched_f)
    elif page == "coach":
        views_coach.render_coach_report(games_df, username)
    elif page == "progress":
        views_coach.render_progress(enriched_f, username)
    elif page == "plan":
        views_coach.render_training_plan(enriched_f, username)
    elif page == "compare":
        views_coach.render_compare(enriched_f, username)
    elif page == "engine":
        render_engine_deep_dive(games_df, username)
    elif page == "methodology":
        views_info.render_methodology()

    flush_ga_events()


def main() -> None:
    st.set_page_config(page_title="Klimate", page_icon="♟️", layout="wide")
    inject_ga()
    flush_ga_events()  # events queued by a run that ended in st.rerun()
    inject_global_styles()

    if not st.session_state.get("data_loaded", False):
        _landing()
    else:
        _dashboard()


if __name__ == "__main__":
    main()
