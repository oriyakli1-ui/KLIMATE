"""Klimate: chess psychology analytics. Streamlit entry point (routing only).

Run with:  streamlit run KLIMATEapp.py
Page code lives in ui_*.py and views_*.py; analysis code in insights.py, analysis.py and analytics.py.
"""
from __future__ import annotations

import streamlit as st
from streamlit_option_menu import option_menu

import insights
import views_coach
import views_features
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

# (page key, bootstrap icon). Labels come from strings.py ("nav_<key>"); keys are stable for analytics.
PAGES = [
    ("overview", "house"), ("clock", "clock-history"), ("spatial", "bullseye"), ("blindspots", "bullseye"),
    ("openingcheck", "book"), ("behavior", "activity"), ("ledger", "cash-coin"), ("playnow", "lightning-charge"), ("time", "stopwatch"), ("coach", "cpu"), ("progress", "graph-up"),
    ("plan", "calendar-check"), ("compare", "people"), ("engine", "cpu"),
]
TIMEZONES = ["Asia/Jerusalem", "UTC", "Europe/London", "Europe/Paris", "America/New_York",
             "America/Los_Angeles", "Asia/Kolkata", "Asia/Tokyo"]
COLOUR_OPTIONS = ["All", "White", "Black"]


def _browser_timezone() -> str:
    """The visitor's own IANA timezone (Streamlit reads it from the browser), UTC if unknown."""
    return getattr(st.context, "timezone", None) or "UTC"


def _timezone_options() -> list[str]:
    mine = _browser_timezone()
    return [mine] + [z for z in TIMEZONES if z != mine]


def _landing() -> None:
    """Landing page: logo, username and history range."""
    _, logo_col, _ = st.columns([1, 2, 1])
    with logo_col:
        st.image("logo.png", width="stretch")
    st.markdown(
        "<p style='text-align: center; color: #D1D5DB; font-size: 1.2rem; "
        "font-weight: 300; margin-top: -15px; margin-bottom: 40px; letter-spacing: 1px;'>"
        f"{t('tagline')}</p>",
        unsafe_allow_html=True,
    )

    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        username_input = st.text_input(t("username"), placeholder=t("username_ph"))
        with st.expander(t("history")):
            months = st.select_slider(t("months_back"), options=[3, 6, 12, 24], value=6)
            max_games = st.select_slider(t("max_games"), options=[100, 300, 500, 1000], value=500)
        analyze_clicked = st.button(t("analyze"), width="stretch")

    if analyze_clicked:
        queue_event("analyze_clicked", has_username=bool(username_input.strip()))

    if analyze_clicked and username_input.strip():
        username = username_input.strip()
        bar = st.progress(0.0, text=t("loading"))
        try:
            games_df = fetch_games(
                username, max_games=max_games, months=months,
                progress=lambda done, total: bar.progress(done / total, text=t("loading")),
            )
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
                st.session_state["fetch_params"] = {"max_games": max_games, "months": months}
                st.session_state["data_loaded"] = True
                queue_event("analysis_loaded", games_count=int(len(games_df)))
                st.rerun()

    flush_ga_events()


def _sidebar(games_df, username: str):
    """Sidebar: wrapped button, navigation, filters, language. Returns (page key, time classes, colour)."""
    labels = {t(f"nav_{key}"): key for key, _ in PAGES}
    with st.sidebar:
        st.image("logo.png", width="stretch")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button(t("wrapped_btn"), type="primary"):
            queue_event("wrapped_generated")
            show_klimate_masterpiece(
                username, st.session_state.get("enriched", games_df.iloc[0:0]), games_df,
                st.session_state.get("cognitive_tz", _browser_timezone()),
            )
        label = option_menu(
            menu_title="KLIMATE",
            options=list(labels),
            icons=[icon for _, icon in PAGES],
            menu_icon="cast",
            # Must stay constant: changing default_index between reruns remounts the component
            # and swallows later clicks. (Switching language therefore returns to Overview.)
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "transparent"},
                "icon": {"color": "#06B6D4", "font-size": "18px"},
                "nav-link": {"font-size": "15px", "text-align": "left", "margin": "0px",
                             "--hover-color": "rgba(6, 182, 212, 0.1)"},
                "nav-link-selected": {"background-color": "#06B6D4", "font-weight": "bold"},
            },
        )
        with st.expander(t("filters")):
            available = sorted(set(games_df["time_class"].dropna()) - {""})
            time_classes = st.multiselect(t("time_control"), available, default=available, key="flt_time_classes")
            colour = st.radio(
                t("colour"), COLOUR_OPTIONS, horizontal=True, key="flt_color",
                format_func=lambda c: t(c.lower()),
            )
            st.caption(t("games_loaded", n=len(games_df)))
    return labels[label], time_classes, colour


def _refresh_games(username: str) -> None:
    """Reload the newest games with the same settings as the first load."""
    params = st.session_state.get("fetch_params", {"max_games": 500, "months": 6})
    fresh = fetch_games(username, params["max_games"], params["months"])
    if not fresh.empty:
        st.session_state["games_df"] = fresh
        st.session_state["enriched"] = insights.enrich_games(fresh, username)


def _dashboard() -> None:
    all_games = st.session_state["games_df"]
    username = st.session_state["username"]
    page, time_classes, colour = _sidebar(all_games, username)

    # Filters apply to every page. ``enriched`` is computed once per load (sessions and tilt
    # need the full timeline) and filtered like the raw games.
    if "enriched" not in st.session_state:
        st.session_state["enriched"] = insights.enrich_games(all_games, username)
    enriched_f = insights.filter_enriched(st.session_state["enriched"], time_classes, colour)
    games_df = insights.filter_games(all_games, username, time_classes, colour)
    if games_df.empty:
        st.warning(t("no_match"))
        flush_ga_events()
        return

    if st.session_state.get("_last_page") != page:  # once per change, not on every rerun
        st.session_state["_last_page"] = page
        queue_event("page_selected", page_name=page)

    st.markdown(
        "<div style='margin-top: 45px; display: flex; align-items: center; gap: 10px; "
        "margin-bottom: 20px; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);'>"
        "<span style='font-size: 1.2rem; opacity: 0.8;'>♟️</span>"
        "<span style='font-weight: 700; color: #E2E8F0; letter-spacing: 2px; font-size: 1.1rem;'>KLIMATE</span>"
        "<span style='color: #06B6D4; font-size: 0.85rem; font-weight: 600; letter-spacing: 1px;'>| COMMAND CENTER</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if page == "overview":
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
        views_features.render_elo_ledger(enriched_f, st.session_state.get("cognitive_tz", _browser_timezone()))
    elif page == "playnow":
        views_features.render_play_now(st.session_state["enriched"], username,
                                       st.session_state.get("cognitive_tz", _browser_timezone()), lambda: _refresh_games(username))
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

    flush_ga_events()


def main() -> None:
    st.set_page_config(page_title="Klimate AI", page_icon="♟️", layout="wide")
    inject_ga()
    flush_ga_events()  # events queued by a run that ended in st.rerun()
    inject_global_styles()

    if not st.session_state.get("data_loaded", False):
        _landing()
    else:
        _dashboard()


if __name__ == "__main__":
    main()
