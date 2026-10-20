"""Batch engine analysis of a player's recent games (needs a local Stockfish)."""
from __future__ import annotations

from typing import Callable, Optional, Tuple

import pandas as pd

import analysis
import analytics

GAME_COLUMNS = ["game_id", "date_utc", "time_class", "result", "accuracy", "blunders", "mistakes", "inaccuracies", "peak_win", "low_win", "url"]


def stockfish_available() -> bool:
    return analytics._find_stockfish() is not None


def _result_of(row: pd.Series, username: str) -> str:
    white = str(row["white_player"]).strip().lower() == username.strip().lower()
    res = str(row["white_result"] if white else row["black_result"]).lower()
    if res == "win":
        return "win"
    return "draw" if res in {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"} else "loss"


def analyze_recent(
    games_df: pd.DataFrame,
    username: str,
    n: int = 20,
    depth: int = 10,
    progress: Optional[Callable[[int, int], None]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Analyze the ``n`` most recent games. Returns ``(moves, games)``.

    ``moves`` has the analysis.MOVE_COLUMNS plus ``game_id``; ``games`` one row per game.
    Per-game engine results are cached by ``analytics.analyze_game_with_stockfish``.
    """
    empty = (pd.DataFrame(columns=analysis.MOVE_COLUMNS + ["game_id"]), pd.DataFrame(columns=GAME_COLUMNS))
    if games_df is None or games_df.empty or not stockfish_available():
        return empty
    recent = games_df.sort_values("date_utc", ascending=False).head(n).reset_index(drop=True)
    all_moves, game_rows = [], []
    for i, row in recent.iterrows():
        pgn = row.get("pgn")
        if isinstance(pgn, str) and pgn.strip():
            ev = analytics.analyze_game_with_stockfish(pgn, 150, depth)
            mv = analysis.classify_game(ev, pgn, username)
            if not mv.empty:
                counts = analysis.label_counts(mv)
                game_rows.append(
                    {
                        "game_id": i,
                        "date_utc": row["date_utc"],
                        "time_class": row.get("time_class", ""),
                        "result": _result_of(row, username),
                        "accuracy": analysis.game_accuracy(mv),
                        "blunders": counts["blunder"],
                        "mistakes": counts["mistake"],
                        "inaccuracies": counts["inaccuracy"],
                        "peak_win": float(max(mv["win_before"].max(), mv["win_after"].max())),
                        "low_win": float(min(mv["win_before"].min(), mv["win_after"].min())),
                        "url": row.get("url", ""),
                    }
                )
                all_moves.append(mv.assign(game_id=i))
        if progress:
            progress(i + 1, len(recent))
    if not all_moves:
        return empty
    return pd.concat(all_moves, ignore_index=True), pd.DataFrame(game_rows, columns=GAME_COLUMNS)


def stats_text(moves: pd.DataFrame, games: pd.DataFrame) -> str:
    """Plain-text facts for the LLM summary (all numbers computed here)."""
    pat = analysis.error_patterns(moves)
    lines = [f"Games analyzed: {len(games)}", f"Average accuracy: {games['accuracy'].mean():.0f}%"]
    lines.append(f"Blunders per game: {games['blunders'].mean():.1f}; mistakes per game: {games['mistakes'].mean():.1f}")
    for r in pat["phase"].itertuples():
        lines.append(f"{r.phase}: {r.errors_per_100:.1f} serious errors per 100 moves, accuracy {r.accuracy:.0f}%")
    for r in pat["types"].itertuples():
        lines.append(f"Serious errors of type '{r.error_type}': {r.count} ({r.share:.0%})")
    conv = analysis.conversion_profile(moves, games)
    if conv["adv_n"]:
        lines.append(f"Games where the player reached a winning position (80%+): {conv['adv_n']}, converted {conv['adv_wins']} to wins")
    if conv["res_n"]:
        lines.append(f"Games where the player fell to a lost position (20%-): {conv['res_n']}, saved {conv['res_wins'] + conv['res_draws']} (draw or win)")
    return "\n".join(lines)
