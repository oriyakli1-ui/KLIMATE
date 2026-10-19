import pytest

import analytics
from uci import UciEngine

pytestmark = pytest.mark.skipif(analytics._find_stockfish() is None, reason="Stockfish not installed")


@pytest.fixture(scope="module")
def engine():
    e = UciEngine(analytics._find_stockfish())
    yield e
    e.close()


def test_start_position_is_balanced(engine):
    cp, best = engine.analyse("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", depth=8)
    assert -80 < cp < 80 and len(best) in (4, 5)


def test_scores_are_from_whites_point_of_view(engine):
    white_mates, best_w = engine.analyse("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", depth=8)
    black_mates, best_b = engine.analyse("3r2k1/5ppp/8/8/8/8/5PPP/6K1 b - - 0 1", depth=8)
    assert white_mates == 1000 and best_w == "d1d8"
    assert black_mates == -1000 and best_b == "d8d1"


def test_game_analysis_end_to_end():
    pgn = '[White "a"]\n[Black "b"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0'
    ev = analytics.analyze_game_with_stockfish(pgn, 20, 8)
    assert list(ev["ply"]) == list(range(1, 8))
    assert ev["evaluation"].iloc[-1] == 10.0  # checkmate for White is capped at +10 pawns
