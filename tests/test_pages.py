"""Every page renders on synthetic data without raising (catches typos, missing imports, bad columns)."""
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import analysis
import insights
import wrapped
import analytics
from tests.conftest import make_games

PGN = ('[White "me"]\n[Black "opp"]\n\n1. e4 {[%clk 0:09:58.0]} e5 {[%clk 0:09:57.0]} 2. Nf3 {[%clk 0:09:50.0]} Nc6 {[%clk 0:09:40.0]} '
       '3. Bb5 {[%clk 0:09:30.0]} a6 {[%clk 0:09:20.0]} 4. Ba4 {[%clk 0:09:10.0]} Nf6 {[%clk 0:09:00.0]} 1-0')


@pytest.fixture(autouse=True)
def _restore_module_state():
    """The page scripts monkeypatch module attributes; undo that so other tests see the real ones."""
    saved = (analytics._find_stockfish, analytics.get_real_time_ratings)
    yield
    analytics._find_stockfish, analytics.get_real_time_ratings = saved


def _games(n=120, seed=1):
    rng = np.random.default_rng(seed)
    res = list(rng.choice(["win", "loss", "draw"], size=n, p=[0.45, 0.45, 0.1]))
    df = make_games(res, gap_minutes=list(rng.choice([3, 5, 90, 600], size=n - 1)), clk_pgn=PGN)
    df["opening"] = rng.choice(["Caro-Kann Defense", "Slav Defense", "Italian Game", "Unknown"], size=n)
    df["time_class"] = rng.choice(["rapid", "blitz"], size=n, p=[0.8, 0.2])
    return df


def test_key_moments_and_wrapped_builder():
    pgn = '[White "Alice"]\n[Black "Bob"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0'
    ev = pd.DataFrame({"ply": range(1, 8), "move_san": ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"],
                       "evaluation": [0.3, 0.3, 0.4, 0.3, 0.5, 10.0, 10.0],
                       "best_move": ["e7e5", "g1f3", "b8c6", "f1c4", "g8f6", "h5f7", ""]})
    moments = analysis.key_moments(ev, pgn, "Bob")
    assert len(moments) == 1
    m = moments[0]
    assert m["san"] == "Nf6" and m["label"] == "blunder" and m["move_number"] == 3
    assert m["fen"].split()[1] == "b" and m["played_uci"] == "g8f6" and m["best_uci"] == "g8f6"  # engine row says best was g8f6 at ply 5

    g = insights.enrich_games(_games(), "me")
    w = wrapped.build_wrapped(g, _games(), "me", {"peak": 1400, "peak_class": "rapid", "rapid": 1300}, "UTC")
    assert w["peak_rating"] == "1400" and "rapid" in w["peak_label"] and "games" in w["wins"]
    assert "Unknown" not in w["best_opening"]
    empty = wrapped.build_wrapped(g.iloc[0:0], _games().iloc[0:0], "me", {}, "UTC")
    assert empty["wins"] == "N/A"


def _run(fn):
    at = AppTest.from_function(fn, default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_overview_page(monkeypatch):
    def page():
        import analytics
        import insights
        import ui_overview
        from tests.test_pages import _games

        analytics.get_real_time_ratings = lambda u: {"rapid": 1300, "blitz": 1100, "bullet": "N/A", "best": {}, "peak": 1400, "peak_class": "rapid"}
        ui_overview.render_overview_page(insights.enrich_games(_games(), "me"), "me")

    at = _run(page)
    text = " ".join(m.value for m in at.markdown)
    assert "Score" in text and "Performance Rating" in text


@pytest.mark.parametrize("which", ["clock", "blindspots", "behavior", "time", "plan", "progress", "ledger", "playnow", "openingcheck", "action", "methodology", "weekly", "scout"])
@pytest.mark.parametrize("n", [120, 7, 1])
def test_other_pages(which, n):
    def page():
        import analytics
        import insights
        import streamlit as st
        import ui_blindspots
        import ui_overview
        import views_coach
        import views_insights
        from tests.test_pages import _games

        analytics.get_real_time_ratings = lambda u: {"rapid": 1300, "blitz": 1100, "bullet": "N/A", "best": {}, "peak": 1400, "peak_class": "rapid"}
        g = insights.enrich_games(_games(st.session_state["n"]), "me")
        which_page = st.session_state["which"]
        if which_page == "clock":
            ui_overview.render_cognitive_clock_chart(insights.hourly_profile(g, "UTC"), "UTC")
        elif which_page == "blindspots":
            ui_blindspots.render_strategic_blindspots(g, "me")
        elif which_page == "behavior":
            views_insights.render_behavior_lab(g)
        elif which_page == "time":
            views_insights.render_time_management(g)
        elif which_page == "plan":
            views_coach.render_training_plan(g, "me")
        elif which_page == "progress":
            views_coach.render_progress(g, "me")
        elif which_page == "ledger":
            import views_features

            views_features.render_elo_ledger(g, "UTC")
        elif which_page == "playnow":
            import views_features

            views_features.render_play_now(g, "me", "UTC", lambda: None)
        elif which_page == "action":
            import views_features

            views_features.render_action_center(g, g, "me", "UTC")
        elif which_page == "weekly":
            import pandas as pd
            import views_features

            views_features.render_weekly(g, "me", "UTC")
        elif which_page == "scout":
            import views_features

            st.session_state["scout"] = {"user": "opp", "enriched": g}
            views_features.render_scout(g, _games(st.session_state["n"]), "me", "UTC")
        elif which_page == "methodology":
            import views_info

            views_info.render_methodology()
        elif which_page == "openingcheck":
            import numpy as np
            import opening_eval
            import pandas as pd
            import views_features

            analytics._find_stockfish = lambda: "no-such-engine"      # the page renders; the button is not pressed
            rng = np.random.default_rng(0)
            data = pd.DataFrame({"opening": rng.choice(["A", "B"], 80), "color": rng.choice(["White", "Black"], 80),
                                 "score": rng.choice([0.0, 1.0], 80), "eval": rng.normal(0, 0.5, 80)})
            st.session_state["opening_eval"] = {"user": "me", "data": data}
            views_features.render_opening_check(g, "me")

    at = AppTest.from_function(page, default_timeout=60)
    at.session_state["which"] = which
    at.session_state["n"] = n
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_spatial_page():
    def page():
        import ui_spatial
        from tests.test_pages import _games

        ui_spatial.render_spatial(_games(20), "me")

    _run(page)


@pytest.mark.parametrize("n", [1, 3])
def test_overview_and_spatial_with_tiny_data(n):
    def page():
        import analytics
        import insights
        import streamlit as st
        import ui_overview
        import ui_spatial
        from tests.test_pages import _games

        analytics.get_real_time_ratings = lambda u: {"rapid": 1300, "blitz": 1100, "bullet": "N/A", "best": {}, "peak": 1400, "peak_class": "rapid"}
        g = _games(st.session_state["n"])
        ui_overview.render_overview_page(insights.enrich_games(g, "me"), "me")
        ui_spatial.render_spatial(g, "me")

    at = AppTest.from_function(page, default_timeout=60)
    at.session_state["n"] = n
    at.run()
    assert not at.exception, [e.value for e in at.exception]
