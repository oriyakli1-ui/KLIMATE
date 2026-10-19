"""All LLM calls in one place: Gemini first, Groq as fallback, successes cached.

Both providers are free-tier friendly. Failures raise ``LLMUnavailable`` (and are
therefore never cached) so callers can show a friendly message.
"""
from __future__ import annotations

import streamlit as st

GEMINI_MODEL = "gemini-2.5-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"
SYSTEM_PROMPT = "You are an elite chess psychology coach. Be concise, practical and encouraging."
UNAVAILABLE_MESSAGE = "AI Coach is currently resting. Please try again in a minute."


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
    try:
        return generate(prompt, max_tokens)
    except LLMUnavailable:
        return UNAVAILABLE_MESSAGE


def coach_explanation(fen: str, actual_move: str, best_move: str, user_loss: float) -> str:
    if not fen:
        return UNAVAILABLE_MESSAGE
    prompt = (
        f"The board position (FEN) is: {fen}. "
        f"The player played '{actual_move}', but the best engine move was '{best_move}'. "
        f"This mistake cost {round(float(user_loss), 2)} pawns of evaluation. "
        "Explain the 'why' behind the mistake from a human perspective. Decide whether it looks like: "
        "panic/defensive oversight, greed (grabbing a pawn and ignoring a threat), tunnel vision, "
        "or impatience in a winning position. Answer in 2-3 punchy, encouraging sentences and give "
        "one actionable tip for next time."
    )
    return safe_generate(prompt, 300)


def pattern_summary(stats_text: str) -> str:
    """Turn computed statistics into a short coaching summary. The numbers come from code, not the model."""
    prompt = (
        "Below are statistics computed from a chess player's recent games. Write a short coaching summary "
        "(max 120 words): the single biggest weakness, one strength, and one concrete habit to build this week. "
        "Use ONLY the facts below; do not invent numbers.\n\n" + stats_text
    )
    return safe_generate(prompt, 350)
