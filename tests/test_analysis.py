import chess
import pandas as pd

import analysis as A

SCHOLARS_MATE = "[White \"Alice\"]\n[Black \"Bob\"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0"


def test_win_probability_is_symmetric_and_monotonic():
    assert abs(A.win_probability(0.0) - 50.0) < 1e-9
    assert abs(A.win_probability(2.0) + A.win_probability(-2.0) - 100.0) < 1e-9
    assert A.win_probability(1.0) < A.win_probability(3.0) < 100.0
    assert A.win_probability(float("nan")) != A.win_probability(float("nan"))  # NaN stays NaN


def test_accuracy_and_labels():
    assert A.move_accuracy(0.0) > 99.0
    assert A.move_accuracy(50.0) < 15.0
    assert A.move_accuracy(5.0) > A.move_accuracy(25.0)
    assert [A.label_for(x) for x in (0, 9.9, 10, 20, 30)] == ["good", "good", "inaccuracy", "mistake", "blunder"]


def test_classify_game_finds_the_blunder():
    evals = pd.DataFrame({
        "ply": range(1, 8),
        "move_san": ["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"],
        "evaluation": [0.3, 0.3, 0.4, 0.3, 0.5, 10.0, 10.0],
        "best_move": ["e7e5", "g1f3", "b8c6", "f1c4", "g8f6", "h5f7", ""],
    })
    moves = A.classify_game(evals, SCHOLARS_MATE, "Bob")
    assert list(moves["ply"]) == [2, 4, 6]  # Bob is Black
    blunder = moves[moves["ply"] == 6].iloc[0]
    assert blunder["label"] == "blunder" and blunder["win_loss"] > 30
    assert A.label_counts(moves)["blunder"] == 1
    assert A.classify_game(evals, SCHOLARS_MATE, "Carol").empty  # not a player in this game


def test_classify_game_handles_missing_evals():
    evals = pd.DataFrame({"ply": [1, 2], "move_san": ["e4", "e5"], "evaluation": [0.3, float("nan")], "best_move": ["", ""]})
    moves = A.classify_game(evals, SCHOLARS_MATE, "Bob")
    assert moves["label"].tolist() == ["unknown"]


def test_error_type_hung_piece():
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 2 3")
    played = chess.Move.from_uci("c6d4")  # knight steps onto a square the f3 knight attacks
    assert A._error_type(board, played, "", "f3d4", "blunder") == "hung_piece"
    assert A._error_type(board, played, "", "f3d4", "good") == ""


def test_error_patterns_aggregation():
    moves = pd.DataFrame({
        "game_id": [0] * 4, "ply": [1, 2, 3, 4], "phase": ["opening", "opening", "middlegame", "endgame"],
        "accuracy": [90, 40, 80, 95], "label": ["good", "blunder", "good", "good"],
        "error_type": ["", "hung_piece", "", ""],
    })
    pat = A.error_patterns(moves)
    assert pat["phase"].set_index("phase").loc["opening", "errors_per_100"] == 50.0
    assert pat["types"].iloc[0]["error_type"] == "hung_piece"
    assert A.error_patterns(pd.DataFrame())["phase"].empty

import pandas as pd

import analysis


def _moves(game_id, wins):
    rows = []
    for i, (b, a) in enumerate(wins, start=1):
        rows.append({"game_id": game_id, "ply": i, "win_before": b, "win_after": a, "phase": "endgame", "move_san": "Qe2", "label": "blunder"})
    return pd.DataFrame(rows)


def test_conversion_profile_counts_and_collapse():
    games = pd.DataFrame({
        "game_id": ["a", "b", "c", "d"], "result": ["win", "loss", "draw", "win"],
        "peak_win": [90, 85, 50, 60], "low_win": [40, 30, 10, 15], "url": ["", "u", "", ""],
    })
    moves = pd.concat([_moves("b", [(85, 85), (85, 30)])])
    out = analysis.conversion_profile(moves, games)
    assert out["adv_n"] == 2 and out["adv_wins"] == 1 and out["conv_rate"] == 0.5
    assert out["res_n"] == 2 and out["res_wins"] == 1 and out["res_draws"] == 1 and out["save_rate"] == 1.0
    col = out["collapses"]
    assert list(col["game_id"]) == ["b"] and col.iloc[0]["turn_ply"] == 2


def test_conversion_profile_empty():
    out = analysis.conversion_profile(pd.DataFrame(), pd.DataFrame())
    assert out["adv_n"] == 0 and out["collapses"].empty
