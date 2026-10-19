import sys
import warnings
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")


def make_games(results, start="2026-01-01 10:00", gap_minutes=None, username="me", clk_pgn=None, duration=5):
    """Raw games frame (data_engine columns) for ``username``.

    ``results`` are user-perspective: 'win', 'loss' or 'draw'. ``gap_minutes`` are the idle minutes
    between one game's end and the next game's start (default 10); each game lasts ``duration`` minutes.
    The user always plays White vs 'opp' at equal rating.
    """
    gap_minutes = gap_minutes or [10] * (len(results) - 1)
    starts = [pd.Timestamp(start, tz="UTC")]
    for g in gap_minutes:
        starts.append(starts[-1] + pd.Timedelta(minutes=duration + g))
    mapping = {"win": ("win", "checkmated"), "loss": ("checkmated", "win"), "draw": ("agreed", "agreed")}
    rows = []
    for st_, r in zip(starts, results):
        w, b = mapping[r]
        rows.append({
            "date_utc": st_ + pd.Timedelta(minutes=duration), "start_utc": st_, "white_player": username,
            "black_player": "opp", "white_rating": 1200, "black_rating": 1200, "white_result": w, "black_result": b,
            "time_class": "rapid", "eco": "", "opening": "Caro-Kann Defense", "opening_variation": "Caro-Kann Defense",
            "pgn": clk_pgn or "", "time_control": "600", "rated": True, "rules": "chess", "url": "", "plies": 40,
        })
    return pd.DataFrame(rows)


@pytest.fixture
def games_factory():
    return make_games
