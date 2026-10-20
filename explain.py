"""Free, deterministic coaching text built from the engine facts. The AI coach is an optional extra on top of this.

Everything here is computed from numbers the app already has, so it costs nothing and never changes between runs.
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

import analysis

_WHY = {
    "hung_piece": "{san} left something undefended: the opponent's best reply wins material. Before every move, spend ten seconds on "
                  "one question: what does this move leave hanging, and what can my opponent capture or attack next?",
    "missed_capture": "A strong capture was available (the engine liked {best}) but {san} did not take it. When you are comfortable, "
                      "scan for free material and checks first, then decide on your plan.",
    "walked_into_attack": "{san} allowed a forcing reply, a check, that you may not have seen. List the opponent's checks, captures "
                          "and threats before you commit.",
    "positional": "This was not a simple blunder: {best} kept more of your position, while {san} let the advantage drift. "
                  "Compare candidate moves by what each one improves, not just by what looks safe.",
}
_PHASE_TIP = {
    "opening": "In the opening, know your first 8 to 10 moves in the lines you play most.",
    "middlegame": "In the middlegame, slow down at critical moments: when the position is tense, check every forcing move.",
    "endgame": "In the endgame, calculate concrete lines to the end; small slips decide the game here.",
}
_HABIT = {
    "hung_piece": "Run a 10-second blunder check (checks, captures, threats) before every move this week.",
    "missed_capture": "Before choosing a plan, scan for free captures and tactics for both sides.",
    "walked_into_attack": "Name your opponent's checks and forcing replies before you move.",
    "positional": "For each critical move, compare two candidate moves and ask what each improves.",
}
_NAMES = {"hung_piece": "hanging pieces", "missed_capture": "missed captures", "walked_into_attack": "walking into attacks",
          "positional": "positional slips"}


def move_explanation(m: Dict[str, object]) -> str:
    """A short explanation of one engine-detected mistake (a ``analysis.key_moments`` item)."""
    best = m.get("best_san") or "another move"
    san = m.get("san", "the move")
    if str(best).endswith("#"):
        why = (f"{best} was checkmate. Before any other plan, always look at every check and capture first: "
               "forcing moves are the fastest way to find a mate or win material.")
    elif str(best).endswith("+") and m.get("error_type") in ("", "positional", None):
        why = (f"The engine's {best} was a strong forcing check. When you are ahead or the position is sharp, "
               "list all your checks, captures and threats before choosing a quiet move.")
    else:
        why = _WHY.get(str(m.get("error_type") or ""), _WHY["positional"]).format(san=san, best=best)
    move_no = int(m.get("move_number", 0) or 0)
    phase = "opening" if move_no <= 10 else "middlegame"
    return (f"You played {san} and gave away about {float(m.get('win_loss', 0)):.0f}% of your winning chances; the engine preferred {best}. "
            f"{why} {_PHASE_TIP[phase]}")


def coach_summary(moves: pd.DataFrame, games: pd.DataFrame) -> str:
    """A coaching summary from the aggregated engine results (weakest phase, error type, conversion, one habit)."""
    if moves is None or moves.empty or games is None or games.empty:
        return ""
    pat = analysis.error_patterns(moves)
    phase, types = pat["phase"], pat["types"]
    conv = analysis.conversion_profile(moves, games)
    parts = [f"Across {len(games)} analyzed games your average accuracy is {games['accuracy'].mean():.0f}%, with "
             f"{games['blunders'].mean():.1f} blunders and {games['mistakes'].mean():.1f} mistakes per game."]
    ok = phase[phase["moves"] >= 30] if not phase.empty else phase
    if len(ok) >= 2:
        worst = ok.loc[ok["errors_per_100"].idxmax()]
        best = ok.loc[ok["accuracy"].idxmax()]
        parts.append(f"Your weakest phase is the {worst['phase']} ({worst['errors_per_100']:.1f} serious errors per 100 moves); "
                     f"your strongest is the {best['phase']} (accuracy {best['accuracy']:.0f}%).")
    top: Optional[str] = None
    if not types.empty and int(types["count"].sum()) >= 5:
        top = str(types.iloc[0]["error_type"])
        parts.append(f"Your most common serious error is {_NAMES.get(top, top)} ({types.iloc[0]['share']:.0%}).")
    if conv["adv_n"] >= 3:
        parts.append(f"You converted {conv['adv_wins']} of {conv['adv_n']} winning positions.")
    if top:
        parts.append(f"Habit for this week: {_HABIT.get(top, _HABIT['positional'])}")
    return " ".join(parts)
