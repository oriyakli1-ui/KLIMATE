"""Renders pages inside Streamlit's AppTest harness, the closest thing to a click-through that runs in CI."""
import pandas as pd
from streamlit.testing.v1 import AppTest

from tests.conftest import make_games


def _coach_page():
    import pandas as pd
    import streamlit as st

    import views_coach

    st.session_state["coach"] = {
        "user": "me", "n": 2,
        "moves": pd.DataFrame({
            "game_id": [0, 0], "ply": [1, 2], "phase": ["opening", "middlegame"], "win_before": [50, 50], "win_after": [50, 10],
            "win_loss": [0.0, 40.0], "accuracy": [100.0, 5.0], "label": ["good", "blunder"], "move_san": ["e4", "Qh5"],
            "error_type": ["", "hung_piece"],
        }),
        "games": pd.DataFrame({
            "game_id": [0], "date_utc": [pd.Timestamp("2026-01-01", tz="UTC")], "time_class": ["rapid"], "result": ["loss"],
            "accuracy": [52.0], "blunders": [1], "mistakes": [0], "inaccuracies": [0],
        }),
    }
    views_coach.coach.stockfish_available = lambda: True
    views_coach.llm.pattern_summary = lambda text: "SUMMARY OK"
    views_coach.render_coach_report(pd.DataFrame(), "me")


def test_coach_summary_button_does_not_clash_with_session_state():
    at = AppTest.from_function(_coach_page, default_timeout=30).run()
    assert not at.exception, at.exception
    next(b for b in at.button if b.label == "Rewrite in coach voice with AI (optional)").click().run()
    assert not at.exception, at.exception  # regression: widget key == session_state key raised on the live site
    assert any("SUMMARY OK" in i.value for i in at.info)
