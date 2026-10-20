"""All LLM calls in one place: Gemini first, Groq as fallback, successes cached.

Both providers are free-tier friendly. Failures raise ``LLMUnavailable`` (and are
therefore never cached) so callers can show a friendly message.
"""
from __future__ import annotations

import datetime as dt
import os
import threading

import streamlit as st

GEMINI_MODEL = "gemini-2.5-flash-lite"      # about 3x cheaper than flash; plenty for 2-3 sentence answers
GROQ_MODEL = "llama-3.3-70b-versatile"
SYSTEM_PROMPT = "You are an elite chess psychology coach. Be concise, practical and encouraging."
UNAVAILABLE_MESSAGE = "AI Coach is currently resting. Please try again in a minute."
LIMIT_MESSAGE = "The AI explanation limit for this visit is reached. The built-in explanation above is always available."
DAILY_LIMIT = int(os.environ.get("KLIMATE_AI_DAILY_LIMIT", "300"))   # fresh (uncached) model calls per day, whole app
SESSION_LIMIT = int(os.environ.get("KLIMATE_AI_SESSION_LIMIT", "6"))  # AI requests per visitor session
_SPENT = {"day": "", "n": 0}
_SPENT_LOCK = threading.Lock()


def _spend() -> None:
    """Count one real (uncached) model call; refuse past the daily budget so cost can never run away."""
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    with _SPENT_LOCK:
        if _SPENT["day"] != today:
            _SPENT["day"], _SPENT["n"] = today, 0
        if _SPENT["n"] >= DAILY_LIMIT:
            raise LLMUnavailable("daily AI budget reached")
        _SPENT["n"] += 1


class LLMUnavailable(RuntimeError):
    """No configured provider could produce a usable answer."""


def _gemini(prompt: str, max_tokens: int) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            # Gemini 2.5 "thinking" tokens count against max_output_tokens and can eat the whole
            # budget, leaving a sentence cut in half. These are short answers: no thinking.
            max_output_tokens=max(max_tokens, 800),
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    candidates = getattr(resp, "candidates", None) or []
    if candidates and "MAX_TOKENS" in str(getattr(candidates[0], "finish_reason", "")):
        raise LLMUnavailable("Gemini answer was cut off")  # triggers the Groq fallback
    text = (resp.text or "").strip()
    if not text:
        raise LLMUnavailable("Gemini returned no text")
    return text


def _groq(prompt: str, max_tokens: int) -> str:
    from groq import Groq

    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    out = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=max_tokens,
    )
    text = (out.choices[0].message.content or "").strip()
    if not text:
        raise LLMUnavailable("Groq returned no text")
    return text


def looks_complete(text: str) -> bool:
    """Heuristic guard against answers cut off mid-sentence or mid-bold (provider quirks, token limits)."""
    s = text.strip()
    return bool(s) and s.endswith((".", "!", "?", ")", '"', "'", "”", "…")) and s.count("**") % 2 == 0


@st.cache_data(show_spinner=False, ttl=86400)
def generate(prompt: str, max_tokens: int = 400, version: int = 2) -> str:
    """Answer ``prompt``. Cached per prompt; raises LLMUnavailable (never cached) on failure.

    ``version`` is part of the cache key: bump it when the generation logic changes so stale
    answers (for example truncated ones) are not served from the cache.
    """
    _spend()
    errors = []
    for provider in (_gemini, _groq):
        try:
            text = provider(prompt, max_tokens)
        except Exception as exc:  # noqa: BLE001 - any provider failure means "try the next one"
            errors.append(f"{provider.__name__}: {exc}")
            continue
        if looks_complete(text):
            return text
        errors.append(f"{provider.__name__}: answer looks cut off")
    raise LLMUnavailable("; ".join(errors))


def safe_generate(prompt: str, max_tokens: int = 400) -> str:
    """Like ``generate`` but returns a friendly message instead of raising."""
    used = st.session_state.get("ai_calls", 0)
    if used >= SESSION_LIMIT:
        return LIMIT_MESSAGE
    st.session_state["ai_calls"] = used + 1
    try:
        return generate(prompt, max_tokens)
    except LLMUnavailable:
        return UNAVAILABLE_MESSAGE


def coach_explanation(fen: str, actual_move: str, best_move: str, win_loss_points: float) -> str:
    """Explain one mistake. ``win_loss_points`` is the win chance given away, in percentage points."""
    if not fen:
        return UNAVAILABLE_MESSAGE
    prompt = (
        f"FEN before the move: {fen}. Played: {actual_move}. Engine best: {best_move}. "
        f"Win chance lost: {round(float(win_loss_points))} points. "
        "In 2-3 short encouraging sentences, say why a human might have played it (only if the position supports it) "
        "and give one tip."
    )
    return safe_generate(prompt, 300)


def pattern_summary(stats_text: str) -> str:
    """Turn computed statistics into a short coaching summary. The numbers come from code, not the model."""
    prompt = (
        "Coaching summary (max 100 words) from these stats: biggest weakness, one strength, one habit for this week. "
        "Use only these facts.\n" + stats_text
    )
    return safe_generate(prompt, 350)
