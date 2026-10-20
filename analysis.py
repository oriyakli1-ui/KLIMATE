"""Move-quality analysis from engine evaluations (Lichess-style win-probability model).

Pure functions on top of the evaluation frame produced by ``analytics.analyze_game``
(columns ``ply, move_san, evaluation, best_move``; evaluation = pawns, white's view,
measured *after* the move at ``ply``). No Streamlit imports.
"""
from __future__ import annotations

import io
import math
from typing import Dict

import chess
import chess.pgn
import pandas as pd

START_EVAL = 0.2  # pawns; the evaluation before move 1
# Win-chance loss (percentage points) thresholds, as used by Lichess.
INACCURACY, MISTAKE, BLUNDER = 10.0, 20.0, 30.0
_PIECE_VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}

MOVE_COLUMNS = [
    "ply", "move_san", "phase", "win_before", "win_after", "win_loss", "accuracy", "label", "error_type",
]


def win_probability(eval_pawns: float) -> float:
    """Chance (0-100) that White wins, from an evaluation in pawns (Lichess logistic model)."""
    if eval_pawns is None or eval_pawns != eval_pawns:
        return float("nan")
    cp = max(-1000.0, min(1000.0, eval_pawns * 100.0))
    return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.00368208 * cp)) - 1.0)


def move_accuracy(win_loss: float) -> float:
    """Accuracy (0-100) of a single move given the win-chance it lost."""
    if win_loss != win_loss:
        return float("nan")
    return float(max(0.0, min(100.0, 103.1668 * math.exp(-0.04354 * max(0.0, win_loss)) - 3.1669)))


def label_for(win_loss: float) -> str:
    if win_loss != win_loss:
        return "unknown"
    if win_loss >= BLUNDER:
        return "blunder"
    if win_loss >= MISTAKE:
        return "mistake"
    if win_loss >= INACCURACY:
        return "inaccuracy"
    return "good"


def _phase(board: chess.Board) -> str:
    """Opening until move 10; endgame once few pieces remain; middlegame otherwise."""
    pieces = sum(len(board.pieces(pt, c)) for pt in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN) for c in (True, False))
    if board.fullmove_number <= 10:
        return "opening"
    return "endgame" if pieces <= 6 else "middlegame"


def _captured_value(board: chess.Board, uci: str) -> int:
    """Value of the piece captured by ``uci`` on ``board`` (0 if not a capture / invalid)."""
    try:
        mv = chess.Move.from_uci(uci)
        if not board.is_capture(mv):
            return 0
        if board.is_en_passant(mv):
            return 1
        piece = board.piece_at(mv.to_square)
        return _PIECE_VALUE.get(piece.piece_type, 0) if piece else 0
    except Exception:
        return 0


def _error_type(board_before: chess.Board, played: chess.Move, best_before: str, best_reply: str, label: str) -> str:
    """Rough, explainable tag for a mistake/blunder (heuristic, based on engine best moves)."""
    if label not in ("mistake", "blunder"):
        return ""
    after = board_before.copy()
    after.push(played)
    if best_reply and _captured_value(after, best_reply) >= 3:
        return "hung_piece"
    if best_before and not board_before.is_capture(played) and _captured_value(board_before, best_before) >= 3:
        return "missed_capture"
    if after.is_check() is False and best_reply:
        try:
            if after.gives_check(chess.Move.from_uci(best_reply)):
                return "walked_into_attack"
        except Exception:
            pass
    return "positional"


def classify_game(eval_df: pd.DataFrame, pgn: str, username: str) -> pd.DataFrame:
    """One row per move of ``username`` with win-chance loss, accuracy, label and phase."""
    empty = pd.DataFrame(columns=MOVE_COLUMNS)
    if eval_df is None or eval_df.empty or not isinstance(pgn, str) or not pgn.strip():
        return empty
    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
    except Exception:
        return empty
    if game is None:
        return empty
    is_white = (game.headers.get("White", "") or "").strip().lower() == username.strip().lower()
    if not is_white and (game.headers.get("Black", "") or "").strip().lower() != username.strip().lower():
        return empty

    ev = eval_df.sort_values("ply").reset_index(drop=True)
    by_ply: Dict[int, tuple] = {int(r.ply): (float(r.evaluation), str(r.best_move or "")) for r in ev.itertuples()}

    rows = []
    board = game.board()
    for ply, move in enumerate(game.mainline_moves(), start=1):
        mover_white = board.turn == chess.WHITE
        if ply in by_ply and mover_white == is_white:
            e_after, best_reply = by_ply[ply]
            e_before, best_before = by_ply.get(ply - 1, (START_EVAL, ""))
            w_b, w_a = win_probability(e_before), win_probability(e_after)
            if not is_white:  # convert to the user's own win chance
                w_b, w_a = 100.0 - w_b, 100.0 - w_a
            loss = max(0.0, w_b - w_a) if (w_b == w_b and w_a == w_a) else float("nan")
            lab = label_for(loss)
            rows.append(
                {
                    "ply": ply,
                    "move_san": board.san(move),
                    "phase": _phase(board),
                    "win_before": w_b,
                    "win_after": w_a,
                    "win_loss": loss,
                    "accuracy": move_accuracy(loss),
                    "label": lab,
                    "error_type": _error_type(board, move, best_before, best_reply, lab),
                }
            )
        try:
            board.push(move)
        except Exception:
            break
    return pd.DataFrame(rows, columns=MOVE_COLUMNS)


def game_accuracy(moves: pd.DataFrame) -> float:
    """Mean move accuracy (an approximation of Lichess's game accuracy)."""
    if moves is None or moves.empty:
        return float("nan")
    return float(moves["accuracy"].mean(skipna=True))


def label_counts(moves: pd.DataFrame) -> Dict[str, int]:
    out = {"blunder": 0, "mistake": 0, "inaccuracy": 0}
    if moves is not None and not moves.empty:
        for k in out:
            out[k] = int((moves["label"] == k).sum())
    return out


def error_patterns(all_moves: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Aggregate classified moves across games.

    ``all_moves`` needs the MOVE_COLUMNS plus ``game_id``. Returns two frames:
    - ``phase``: per phase, moves, serious errors (mistake+blunder) per 100 moves, mean accuracy
    - ``types``: serious errors by heuristic type with their share
    """
    if all_moves is None or all_moves.empty:
        return {"phase": pd.DataFrame(), "types": pd.DataFrame()}
    serious = all_moves["label"].isin(["mistake", "blunder"])
    phase = (
        all_moves.assign(serious=serious)
        .groupby("phase")
        .agg(moves=("ply", "size"), serious=("serious", "sum"), accuracy=("accuracy", "mean"))
        .reindex(["opening", "middlegame", "endgame"])
        .dropna(subset=["moves"])
        .reset_index()
    )
    phase["errors_per_100"] = phase["serious"] / phase["moves"] * 100.0
    types = all_moves[serious & (all_moves["error_type"] != "")]["error_type"].value_counts().rename_axis("error_type").reset_index(name="count")
    if not types.empty:
        types["share"] = types["count"] / types["count"].sum()
    return {"phase": phase, "types": types}


def key_moments(eval_df: pd.DataFrame, pgn: str, username: str, top: int = 5) -> list:
    """The player's biggest mistakes/blunders (by win chance given away), with what to show on the board.

    Each item: ply, move_number, san, label, win_loss, error_type, fen (position BEFORE the move),
    played_uci, best_uci (the engine's choice in that position) and best_san.
    """
    moves = classify_game(eval_df, pgn, username)
    if moves.empty:
        return []
    bad = moves[moves["label"].isin(["mistake", "blunder"])].sort_values("win_loss", ascending=False).head(top)
    if bad.empty:
        return []
    game = chess.pgn.read_game(io.StringIO(pgn))
    by_ply = {int(r.ply): str(r.best_move or "") for r in eval_df.itertuples()}
    wanted = {int(p) for p in bad["ply"]}
    info = {}
    board = game.board()
    for ply, move in enumerate(game.mainline_moves(), start=1):
        if ply in wanted:
            best_uci = by_ply.get(ply - 1, "")
            try:
                best_san = board.san(chess.Move.from_uci(best_uci)) if best_uci else ""
            except Exception:  # noqa: BLE001 - engine move not legal here (should not happen)
                best_uci, best_san = "", ""
            info[ply] = {"fen": board.fen(), "played_uci": move.uci(), "best_uci": best_uci, "best_san": best_san}
        board.push(move)
    out = []
    for r in bad.itertuples():
        d = info.get(int(r.ply))
        if d:
            out.append({"ply": int(r.ply), "move_number": (int(r.ply) + 1) // 2, "san": r.move_san, "label": r.label,
                        "win_loss": float(r.win_loss), "error_type": r.error_type, **d})
    return out


def conversion_profile(moves: pd.DataFrame, games: pd.DataFrame, hi: float = 80.0, lo: float = 20.0) -> Dict[str, object]:
    """Converting advantages and fighting back, from per-game win-chance extremes.

    ``games`` needs: game_id, result ('win'/'draw'/'loss'), peak_win, low_win (the player's best and worst
    win chance during the game) and optionally url/date_utc. A game is an *advantage game* when the player
    reached ``hi`` percent win chance at some point, a *deficit game* when they dropped to ``lo`` percent.
    Collapses are advantage games that were not won; the turning point is the first player move after the
    peak that left the win chance below 50%.
    """
    from metrics import wilson_interval

    out: Dict[str, object] = {"adv_n": 0, "res_n": 0, "collapses": pd.DataFrame(), "hi": hi, "lo": lo}
    if games is None or games.empty or "peak_win" not in games.columns:
        return out
    adv = games[games["peak_win"] >= hi]
    deficit = games[games["low_win"] <= lo]
    out.update(
        adv_n=len(adv), adv_wins=int((adv["result"] == "win").sum()), adv_draws=int((adv["result"] == "draw").sum()),
        adv_losses=int((adv["result"] == "loss").sum()), res_n=len(deficit),
        res_wins=int((deficit["result"] == "win").sum()), res_draws=int((deficit["result"] == "draw").sum()),
        res_losses=int((deficit["result"] == "loss").sum()),
    )
    if len(adv):
        out["conv_rate"] = out["adv_wins"] / len(adv)
        out["conv_lo"], out["conv_hi"] = wilson_interval(out["adv_wins"], len(adv))
    if len(deficit):
        saved = out["res_wins"] + out["res_draws"]
        out["save_rate"] = saved / len(deficit)
        out["save_lo"], out["save_hi"] = wilson_interval(saved, len(deficit))

    rows = []
    for r in adv[adv["result"] != "win"].itertuples():
        mv = moves[moves["game_id"] == r.game_id].sort_values("ply") if moves is not None and not moves.empty else pd.DataFrame()
        turn = None
        if not mv.empty:
            peak_idx = mv["win_before"].idxmax()
            after = mv.loc[peak_idx:]
            below = after[after["win_after"] < 50.0]
            if not below.empty:
                turn = below.iloc[0]
        rows.append({"game_id": r.game_id, "date_utc": getattr(r, "date_utc", None), "url": getattr(r, "url", ""), "result": r.result,
                     "peak": float(r.peak_win), "turn_ply": int(turn["ply"]) if turn is not None else None,
                     "phase": turn["phase"] if turn is not None else None, "move": turn["move_san"] if turn is not None else None,
                     "label": turn["label"] if turn is not None else None})
    out["collapses"] = pd.DataFrame(rows)
    return out
