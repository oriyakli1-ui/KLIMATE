"""Action Center: the few things most worth doing next, from the player's own evidence (pure, tested)."""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

MAX_ACTIONS = 3


def build_actions(
    insights_list: List[Dict[str, object]],
    ledger_table: Optional[pd.DataFrame],
    play_light: str,
    opening_report: Optional[pd.DataFrame],
    in_session: bool,
    games: int,
) -> List[Dict[str, str]]:
    """Up to three actions, most urgent first. Each: title, detail, where (page name), tone."""
    acts: List[Dict[str, str]] = []

    if play_light == "red" and in_session:
        acts.append({"title": "Take a break before the next game",
                     "detail": "Your own history says this exact moment (session length or losses in a row) goes worse than usual.",
                     "where": "Play Now", "tone": "warn"})

    if ledger_table is not None and not ledger_table.empty:
        bad = ledger_table[ledger_table["reliable"] & (ledger_table["difference"] < 0)].sort_values("points_vs_normal")
        for r in bad.head(2).itertuples():
            acts.append({"title": f"Fix this leak: {r.situation.lower()}",
                         "detail": f"It costs you {abs(r.difference):.2f} rating points per game compared with your other games ({r.games} games).",
                         "where": "Elo Ledger", "tone": "warn"})

    if opening_report is not None and not opening_report.empty:
        for r in opening_report[opening_report["verdict"].str.startswith("Opening problem")].head(1).itertuples():
            acts.append({"title": f"Repair your {r.opening} as {r.color}",
                         "detail": f"You are on average {abs(r.eval):.1f} pawns worse than usual after 10 moves ({r.games} games).",
                         "where": "Opening Check", "tone": "warn"})

    for ins in insights_list:
        if len(acts) >= MAX_ACTIONS:
            break
        if ins["key"] == "stop_loss" and any(a["where"] == "Elo Ledger" for a in acts):
            continue
        acts.append({"title": str(ins["title"]), "detail": str(ins["detail"]), "where": "Behavior Lab", "tone": "warn"})

    if len(acts) < MAX_ACTIONS and opening_report is None and games >= 60:
        acts.append({"title": "Check your openings with the engine",
                     "detail": "Find out which openings leave you worse by move 10 (takes about 15 seconds).",
                     "where": "Opening Check", "tone": "info"})
    if len(acts) < MAX_ACTIONS:
        acts.append({"title": "Analyze your latest games with the engine",
                     "detail": "The Coach Report shows where in the game you lose points and what kind of mistakes you make.",
                     "where": "Coach Report", "tone": "info"})
    if len(acts) < MAX_ACTIONS and games < 150:
        acts.append({"title": "Load more history for deeper insights",
                     "detail": f"You have {games} games loaded. Most patterns need a few hundred; pick a longer history on the first screen.",
                     "where": "Load someone else (history options)", "tone": "info"})
    if len(acts) < MAX_ACTIONS:
        acts.append({"title": "Check Play Now before your next session",
                     "detail": "A quick evidence-based check on whether this is a good moment to play.", "where": "Play Now", "tone": "info"})
    return acts[:MAX_ACTIONS]
