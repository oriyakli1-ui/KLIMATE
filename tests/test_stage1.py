import pandas as pd

import actions
import nav
import strings
import views_info


def test_navigation_groups_cover_every_page_exactly_once():
    pages = nav.all_pages()
    assert len(pages) == len(set(pages))
    expected = {"overview", "playnow", "behavior", "ledger", "time", "clock", "openingcheck", "blindspots", "spatial",
                "coach", "engine", "progress", "plan", "compare", "methodology", "weekly", "scout"}
    assert set(pages) == expected
    assert all(strings.t(f"nav_{p}") != f"nav_{p}" for p in pages)      # every page has a label
    assert nav.group_of("ledger") == "habits" and nav.group_labels()["🏠 Home"] == "home"
    assert nav.pages_of("home")[0][0] == "overview"


def _ledger(reliable=True):
    return pd.DataFrame([{"situation": "Games right after a loss (same session)", "difference": -1.4, "games": 120,
                          "points_vs_normal": -168.0, "reliable": reliable, "enough": True}])


def _report():
    return pd.DataFrame([{"opening": "Slav Defense", "color": "Black", "games": 30, "eval": -1.2,
                          "verdict": "Opening problem: you are worse than usual by move 10"}])


def test_actions_prioritise_break_then_leaks_then_openings():
    ins = [{"key": "warmup", "title": "You start sessions cold", "detail": "x"}]
    acts = actions.build_actions(ins, _ledger(), "red", _report(), True, 400)
    assert [a["where"] for a in acts] == ["Play Now", "Elo Ledger", "Opening Check"]
    assert len(acts) == actions.MAX_ACTIONS


def test_actions_fall_back_to_discovery_when_there_is_no_evidence():
    acts = actions.build_actions([], _ledger(reliable=False), "grey", None, False, 400)
    assert len(acts) == 3 and all(a["tone"] == "info" for a in acts)
    assert acts[0]["where"] == "Opening Check"
    few = actions.build_actions([], None, "grey", None, False, 20)
    assert len(few) == 3 and few[0]["where"] == "Coach Report"


def test_methodology_has_the_sections_users_need():
    titles = [t for t, _ in views_info.SECTIONS]
    assert any("Ratings" in t for t in titles) and any("reliable" in t for t in titles) and any("limits" in t for t in titles)

def test_landing_has_demo_buttons():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("KLIMATEapp.py", default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    labels = [b.label for b in at.button]
    assert "hikaru" in labels and "magnuscarlsen" in labels
