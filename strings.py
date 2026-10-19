"""UI strings (English). ``t(key, **kw)`` formats a string; unknown keys return the key itself."""
from __future__ import annotations

from typing import Dict

STRINGS: Dict[str, str] = {
    # navigation
    "nav_overview": "Overview", "nav_clock": "Cognitive Clock", "nav_spatial": "Spatial Analysis",
    "nav_blindspots": "Strategic Blindspots", "nav_behavior": "Behavior Lab", "nav_time": "Time Management",
    "nav_coach": "Coach Report", "nav_progress": "Progress", "nav_plan": "Training Plan",
    "nav_compare": "Compare", "nav_engine": "Engine Deep Dive",
    "nav_ledger": "Elo Ledger", "nav_playnow": "Play Now", "nav_openingcheck": "Opening Check",
    "nav_methodology": "Methodology",
    # landing + sidebar
    "tagline": "Decode Your Chess DNA. Elevate Your Mental Game.", "username": "Chess.com Username",
    "username_ph": "e.g. oriyakli1", "history": "History to analyze", "months_back": "Months back",
    "max_games": "Max games", "analyze": "Analyze DNA", "loading": "Analyzing your chess DNA...",
    "err_fetch": "Failed to fetch games for '{user}': {err}",
    "no_games": "No recent games found for '{user}'. Play a few games on Chess.com and try again.",
    "wrapped_btn": "🎁 Generate My Klimate Masterpiece", "filters": "🎛️ Filters", "time_control": "Time control",
    "colour": "Colour", "all": "All", "white": "White", "black": "Black", "games_loaded": "{n} games loaded",
    "no_match": "No games match the current filters.",
    # insights panel
    "insights_title": "💡 Klimate Insights",
    "min_games": "Not enough games for a reliable reading yet. Load more history in the sidebar filters.",
    "no_pattern_title": "No reliable pattern yet",
    "no_pattern_detail": "Across {n} games none of the patterns we test (tilt, slow starts, time scrambles, opponent strength, colour) differs from normal luck. Load more history to look for subtler ones.",
    "more_insights": "{n} more insight(s)",
    "insights_caption": "Insights appear only when the difference is larger than chance would explain.",
    # behavior lab
    "behavior_title": "🧪 Behavior Lab", "sessions": "Sessions", "games_session": "Games / session",
    "longest_session": "Longest session", "overall_score": "Overall score",
    "session_caption": "A session = games where less than {m} minutes pass between one game ending and the next starting. Score = (wins + 0.5 × draws) / games.",
    "tilt_header": "Tilt: what happens after consecutive losses",
    "tilt_chart": "Score by losses in a row just before the game",
    "stop_card_title": "Your stop-loss rule: stop after {n} loss{es} in a row",
    "stop_card_detail": "Your results drop significantly beyond that point. Take a break instead of chasing the rating.",
    "no_tilt_title": "No reliable tilt effect", "no_tilt_detail": "Your results after losses are not significantly worse than usual.",
    "warmup_header": "Warm-up: score by game number in a session", "warmup_chart": "Score by game number in the session",
    "opp_header": "Opponent strength", "opp_chart": "Score by opponent rating vs yours",
    "colour_header": "Colour", "colour_chart": "Score as White vs Black",
    # time management
    "time_title": "⏱️ Time Management", "games_clocks": "Games with clocks", "scramble_rate": "Time-scramble rate",
    "timeouts_wl": "Lost on time / won on time", "clock_15": "Clock left after move 15",
    "clock_chart": "Score by how you used the clock", "by_time_class": "By time class",
    # coach / progress / plan / compare
    "coach_title": "🧠 Coach Report", "analyze_recent": "Analyze my recent games",
    "progress_title": "📈 Progress", "goals": "🎯 Your goals",
    "plan_title": "🗓️ Your weekly training plan", "compare_title": "🆚 Compare with another player",
    "compare_prompt": "Chess.com username to compare with",
}


def t(key: str, **kw: object) -> str:
    text = STRINGS.get(key, key)
    try:
        return text.format(**kw) if kw else text
    except (KeyError, IndexError):
        return text


def insight_text(item: Dict[str, object]) -> Dict[str, str]:
    """Title and detail of an insight (built from the templates in insights.py)."""
    return {"title": str(item["title"]), "detail": str(item["detail"])}
