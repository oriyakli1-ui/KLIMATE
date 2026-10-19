"""English / Hebrew UI strings.

``t(key)`` returns the string in the language chosen in ``st.session_state["lang"]``
and falls back to English, then to the key itself, so a missing translation never breaks a page.
Coverage: navigation, landing page, filters, the new analysis pages' headings/metrics and the
insight cards. Older pages (Overview cards, Spatial, Blindspots text, Engine coach) are still English.
"""
from __future__ import annotations

from typing import Dict

import streamlit as st

EN: Dict[str, str] = {
    # navigation
    "nav_overview": "Overview", "nav_clock": "Cognitive Clock", "nav_spatial": "Spatial Analysis",
    "nav_blindspots": "Strategic Blindspots", "nav_behavior": "Behavior Lab", "nav_time": "Time Management",
    "nav_coach": "Coach Report", "nav_progress": "Progress", "nav_plan": "Training Plan",
    "nav_compare": "Compare", "nav_engine": "Engine Deep Dive",
    # landing + sidebar
    "tagline": "Decode Your Chess DNA. Elevate Your Mental Game.", "username": "Chess.com Username",
    "username_ph": "e.g. oriyakli1", "history": "History to analyze", "months_back": "Months back",
    "max_games": "Max games", "analyze": "Analyze DNA", "loading": "Analyzing your chess DNA...",
    "err_fetch": "Failed to fetch games for '{user}': {err}",
    "no_games": "No recent games found for '{user}'. Play a few games on Chess.com and try again.",
    "wrapped_btn": "🎁 Generate My Klimate Masterpiece", "filters": "🎛️ Filters", "time_control": "Time control",
    "colour": "Colour", "all": "All", "white": "White", "black": "Black", "games_loaded": "{n} games loaded",
    "no_match": "No games match the current filters.", "language": "Language",
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
    "session_caption": "A session = games with less than {m} minutes between them. Score = (wins + 0.5 × draws) / games.",
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

HE: Dict[str, str] = {
    "nav_overview": "סקירה", "nav_clock": "שעון קוגניטיבי", "nav_spatial": "ניתוח מרחבי",
    "nav_blindspots": "נקודות עיוורון", "nav_behavior": "מעבדת התנהגות", "nav_time": "ניהול זמן",
    "nav_coach": "דוח מאמן", "nav_progress": "התקדמות", "nav_plan": "תוכנית אימון",
    "nav_compare": "השוואה", "nav_engine": "צלילה למנוע",
    "tagline": "פענח את ה-DNA השחמטאי שלך. שפר את המשחק המנטלי.", "username": "שם משתמש ב-Chess.com",
    "username_ph": "לדוגמה: oriyakli1", "history": "היסטוריה לניתוח", "months_back": "חודשים אחורה",
    "max_games": "מקסימום משחקים", "analyze": "נתח את ה-DNA", "loading": "מנתח את ה-DNA השחמטאי שלך...",
    "err_fetch": "טעינת המשחקים של '{user}' נכשלה: {err}",
    "no_games": "לא נמצאו משחקים אחרונים של '{user}'. שחק כמה משחקים ב-Chess.com ונסה שוב.",
    "wrapped_btn": "🎁 צור את יצירת המופת שלי", "filters": "🎛️ מסננים", "time_control": "בקרת זמן",
    "colour": "צבע", "all": "הכול", "white": "לבן", "black": "שחור", "games_loaded": "{n} משחקים נטענו",
    "no_match": "אין משחקים שמתאימים למסננים.", "language": "שפה",
    "insights_title": "💡 תובנות Klimate",
    "min_games": "אין עדיין מספיק משחקים לקריאה אמינה. טען יותר היסטוריה במסננים בסרגל הצד.",
    "no_pattern_title": "עדיין אין דפוס אמין",
    "no_pattern_detail": "ב-{n} משחקים אף אחד מהדפוסים שאנחנו בודקים (טילט, פתיחה קרה, לחץ זמן, חוזק יריב, צבע) לא שונה ממזל רגיל. טען יותר היסטוריה כדי לחפש דפוסים עדינים יותר.",
    "more_insights": "עוד {n} תובנות",
    "insights_caption": "תובנות מופיעות רק כשההבדל גדול ממה שמזל היה מסביר.",
    "behavior_title": "🧪 מעבדת התנהגות", "sessions": "סשנים", "games_session": "משחקים לסשן",
    "longest_session": "הסשן הארוך ביותר", "overall_score": "ציון כללי",
    "session_caption": "סשן = משחקים עם פחות מ-{m} דקות ביניהם. ציון = (ניצחונות + 0.5 × תיקו) / משחקים.",
    "tilt_header": "טילט: מה קורה אחרי הפסדים רצופים",
    "tilt_chart": "ציון לפי מספר ההפסדים הרצופים שלפני המשחק",
    "stop_card_title": "כלל העצירה שלך: עצור אחרי {n_he} ברצף",
    "stop_card_detail": "התוצאות שלך יורדות משמעותית מעבר לנקודה הזו. קח הפסקה במקום לרדוף אחרי הדירוג.",
    "no_tilt_title": "אין אפקט טילט אמין", "no_tilt_detail": "התוצאות שלך אחרי הפסדים לא גרועות משמעותית מהרגיל.",
    "warmup_header": "חימום: ציון לפי מספר המשחק בסשן", "warmup_chart": "ציון לפי מספר המשחק בסשן",
    "opp_header": "חוזק היריב", "opp_chart": "ציון לפי דירוג היריב ביחס לשלך",
    "colour_header": "צבע", "colour_chart": "ציון כלבן מול שחור",
    "time_title": "⏱️ ניהול זמן", "games_clocks": "משחקים עם שעונים", "scramble_rate": "שיעור לחץ זמן",
    "timeouts_wl": "הפסד בזמן / ניצחון בזמן", "clock_15": "זמן שנשאר אחרי המהלך ה-15",
    "clock_chart": "ציון לפי השימוש בשעון", "by_time_class": "לפי בקרת זמן",
    "coach_title": "🧠 דוח מאמן", "analyze_recent": "נתח את המשחקים האחרונים שלי",
    "progress_title": "📈 התקדמות", "goals": "🎯 היעדים שלך",
    "plan_title": "🗓️ תוכנית האימון השבועית שלך", "compare_title": "🆚 השוואה לשחקן אחר",
    "compare_prompt": "שם משתמש ב-Chess.com להשוואה",
}

HE_INSIGHTS: Dict[str, tuple] = {
    "stop_loss": (
        "כלל העצירה האישי שלך: סיים את הסשן אחרי {n_he} ברצף",
        "אחרי {n_he}{plus} בסשן הציון שלך יורד ל-{score} (לעומת {baseline} בסך הכול, {games} משחקים).",
    ),
    "warmup": (
        "אתה מתחיל סשנים קר: המשחק הראשון הוא החלש ביותר שלך",
        "אתה מקבל {first} במשחק הראשון של סשן לעומת {rest} בשאר ({n} סשנים). נסה משחק חימום או כמה פאזלים קודם.",
    ),
    "scramble": (
        "לחץ זמן עולה לך ביוקר: {rate} מהמשחקים נגמרים כמעט בלי זמן",
        "כשאתה בלחץ זמן הציון שלך {score} לעומת {other} אחרת ({n} משחקים).",
    ),
    "early_burn": (
        "אתה מבזבז יותר מדי זמן בתחילת המשחק",
        "כשנשאר לך פחות מ-70% מהזמן אחרי המהלך ה-15 הציון שלך {burn} לעומת {calm} ({n} משחקים).",
    ),
    "timeouts": (
        "{share} מההפסדים שלך הם בזמן",
        "{losses} משחקים הפסדת על השעון לעומת {wins} שניצחת כך. שקול בקרת זמן עם תוספת.",
    ),
    "lower_rated": (
        "אתה מפגר מהצפוי מול יריבים בדירוג נמוך יותר",
        "מול יריבים בדירוג נמוך מהשלך ב-30+ הדירוג צופה {expected} אבל אתה מקבל {actual} ({n} משחקים).",
    ),
    "color": (
        "הרפרטואר שלך עם {weak} צריך עבודה",
        "אתה מקבל {w} עם לבן ו-{b} עם שחור.",
    ),
}

LANGS = {"English": "en", "עברית": "he"}


def he_losses(n: int) -> str:
    return "הפסד אחד" if n == 1 else f"{n} הפסדים"


def lang() -> str:
    return st.session_state.get("lang", "en")


def t(key: str, **kw: object) -> str:
    table = HE if lang() == "he" else EN
    text = table.get(key) or EN.get(key) or key
    try:
        return text.format(**kw) if kw else text
    except (KeyError, IndexError):
        return text


def insight_text(item: Dict[str, object]) -> Dict[str, str]:
    """Title/detail of an insight in the current language (English template as fallback)."""
    params = item.get("params", {})
    if lang() == "he" and item["key"] in HE_INSIGHTS:
        title, detail = HE_INSIGHTS[item["key"]]
        if item["key"] == "color":  # translate the colour word inside the sentence
            params = {**params, "weak": "שחור" if params.get("weak") == "Black" else "לבן"}
        if item["key"] == "stop_loss":
            params = {**params, "n_he": he_losses(int(params.get("n", 1)))}
        return {"title": title.format(**params), "detail": detail.format(**params)}
    return {"title": str(item["title"]), "detail": str(item["detail"])}


def apply_direction() -> None:
    """Right-to-left layout for Hebrew; charts and tables keep their natural direction."""
    if lang() != "he":
        return
    st.markdown(
        "<style>"
        ".main .block-container, [data-testid='stMarkdownContainer'] {direction: rtl; text-align: right;}"
        ".js-plotly-plot, .stDataFrame, [data-testid='stMetric'] {direction: ltr; text-align: left;}"
        "</style>",
        unsafe_allow_html=True,
    )
