"""Weekly training plan built from the player's own findings (rule-based, free links)."""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

import insights
from metrics import significantly_different

LICHESS_THEME = "https://lichess.org/training/"
LICHESS_OPENING = "https://lichess.org/opening/"

_TYPE_PLAN = {
    "hung_piece": ("Stop hanging pieces", "Before every move ask: 'what does this leave undefended?' Then do 15 puzzles on loose pieces.", LICHESS_THEME + "hangingPiece"),
    "missed_capture": ("Notice free material", "You missed winning captures. Before each move list all captures and checks for both sides. 15 puzzles to train the eye.", LICHESS_THEME + "advantage"),
    "walked_into_attack": ("Check the opponent's forcing replies", "Several errors allowed a strong check. Practise 'checks, captures, threats' on every move.", LICHESS_THEME + "mix"),
    "positional": ("Plan before you move", "Many errors are quiet positional drifts. Study the plan in one annotated game and name the plan out loud each move.", LICHESS_THEME + "middlegame"),
}
_PHASE_LINK = {"opening": LICHESS_THEME + "opening", "middlegame": LICHESS_THEME + "middlegame", "endgame": LICHESS_THEME + "endgame"}


def weak_openings(g: pd.DataFrame, min_games: int = 8, top: int = 2) -> pd.DataFrame:
    """Opening families that score significantly below the player's own average (needs `min_games` each)."""
    ops = insights.opening_summary(g, min_games)
    if ops.empty or g.empty:
        return pd.DataFrame()
    base, n_all = float(g["score"].mean()), len(g)
    bad = ops[[s < base and significantly_different(int(n), float(s), n_all, base) for n, s in zip(ops["games"], ops["score"])]]
    return bad.sort_values("score").head(top)[["opening", "games", "score"]]


def build_plan(
    insights_list: List[Dict[str, str]],
    patterns: Optional[Dict[str, pd.DataFrame]] = None,
    openings: Optional[pd.DataFrame] = None,
    opening_report: Optional[pd.DataFrame] = None,
    ledger_table: Optional[pd.DataFrame] = None,
) -> List[Dict[str, str]]:
    """Up to seven actionable items, most evidence-backed first, padded with solid habits."""
    items: List[Dict[str, str]] = []
    keys = {i["key"]: i for i in insights_list}

    if "stop_loss" in keys:
        items.append({"title": "Set your stop-loss", "detail": keys["stop_loss"]["title"] + ". Write it on a sticky note and obey it all week.", "link": "", "tag": "tilt"})
    if "scramble" in keys or "early_burn" in keys or "timeouts" in keys:
        why = (keys.get("scramble") or keys.get("early_burn") or keys.get("timeouts"))["detail"]
        items.append({"title": "Clock discipline", "detail": why + " This week: play 3 games in your usual time control and keep at least 70% of your clock after move 15.", "link": "", "tag": "time"})

    if patterns and not patterns.get("types", pd.DataFrame()).empty:
        for et in patterns["types"]["error_type"].head(2):
            if et in _TYPE_PLAN:
                title, detail, link = _TYPE_PLAN[et]
                items.append({"title": title, "detail": detail, "link": link, "tag": "tactics"})
    if patterns and not patterns.get("phase", pd.DataFrame()).empty:
        worst = patterns["phase"].sort_values("errors_per_100", ascending=False).iloc[0]
        items.append({
            "title": f"Fix your {worst['phase']}",
            "detail": f"{worst['errors_per_100']:.1f} serious errors per 100 moves, your weakest phase. Do 20 puzzles from this phase.",
            "link": _PHASE_LINK.get(worst["phase"], ""),
            "tag": "phase",
        })

    if openings is not None and not openings.empty:
        for r in openings.itertuples():
            items.append({
                "title": f"Repair your {r.opening}",
                "detail": f"You score {r.score:.0%} over {int(r.games)} games with it. Study the main line and one model game, then play it deliberately.",
                "link": LICHESS_OPENING + str(r.opening).replace(" ", "_"),
                "tag": "opening",
            })
    if opening_report is not None and not opening_report.empty:
        for r in opening_report[opening_report["verdict"].str.startswith("Opening problem")].head(2).itertuples():
            items.append({
                "title": f"Fix your {r.opening} as {r.color}",
                "detail": f"After move 10 you average {r.eval:+.2f} pawns over {r.games} games (worse than your other openings). "
                          "Replay your last games with it and find the move where you first leave known ideas, then study that line.",
                "link": LICHESS_OPENING + str(r.opening).replace(" ", "_"), "tag": "opening",
            })
    if ledger_table is not None and not ledger_table.empty:
        for r in ledger_table[ledger_table["reliable"] & (ledger_table["difference"] < 0)].head(1).itertuples():
            items.append({
                "title": "Stop the biggest rating leak",
                "detail": f"{r.situation}: {r.difference:+.2f} rating points per game versus your other games ({r.games} games). "
                          "Decide a rule for this situation before you play, for example a break or a different time control.",
                "link": "", "tag": "habit",
            })
    if "warmup" in keys:
        items.append({"title": "Warm up first", "detail": keys["warmup"]["detail"], "link": LICHESS_THEME + "mix", "tag": "habit"})

    fillers = [
        {"title": "Daily puzzle streak", "detail": "10 minutes of mixed puzzles every day builds pattern recognition faster than playing more games.", "link": LICHESS_THEME + "mix", "tag": "habit"},
        {"title": "Review one loss properly", "detail": "Pick one recent loss, find the moment it turned, and write down in one sentence what you missed.", "link": "", "tag": "habit"},
        {"title": "Endgame basics", "detail": "Rook endgames decide many club games. Spend 20 minutes on one technique (e.g. Lucena).", "link": LICHESS_THEME + "endgame", "tag": "phase"},
        {"title": "Play fewer, better games", "detail": "Decide a number of games for the week and take 2 minutes of review after each.", "link": "", "tag": "habit"},
        {"title": "Opening homework", "detail": "Pick the opening you play most and learn its first 8 moves and the main plan behind them.", "link": LICHESS_OPENING.rstrip("/"), "tag": "opening"},
        {"title": "Calculation practice", "detail": "Solve 5 harder puzzles slowly: find the full line before touching a piece.", "link": LICHESS_THEME + "mix", "tag": "tactics"},
        {"title": "Rest day", "detail": "A day off protects your focus. Come back and play one calm game.", "link": "", "tag": "habit"},
    ]
    for f in fillers:
        if len(items) >= 7:
            break
        items.append(f)

    for n, it in enumerate(items[:7], start=1):
        it["day"] = f"Day {n}"
    return items[:7]
