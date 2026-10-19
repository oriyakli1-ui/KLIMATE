"""Small UI helpers shared by several pages."""
from __future__ import annotations

import re
from typing import Optional
import streamlit as st


def format_opening_label(raw: str) -> str:
    """
    Clean up a raw opening label that might be a URL or slug.

    - If it contains '/', keep only the last segment.
    - Replace '-' and '_' with spaces.
    - Strip and title-case.
    """
    if not isinstance(raw, str):
        return "Unknown"

    segment = raw.rsplit("/", 1)[-1]
    segment = re.sub(r"[-_]+", " ", segment)
    segment = segment.strip()
    if not segment:
        return "Unknown"
    return segment.title()


def render_metric_card(
    title: str,
    value_str: str,
    badge_text: Optional[str] = None,
    badge_variant: str = "neutral",
    value_class: str = "",
) -> None:
    """Render a single Bento-style metric card."""
    badge_class = {
        "neutral": "badge-neutral",
        "success": "badge-success",
        "danger": "badge-danger",
    }.get(badge_variant, "badge-neutral")

    badge_html = (
        f'<div class="klimate-metric-badge {badge_class}">{badge_text}</div>'
        if badge_text
        else ""
    )

    value_css = f" klimate-metric-value {value_class}".strip() if value_class else "klimate-metric-value"

    st.markdown(
        f"""
        <div class="klimate-card">
            <div class="klimate-metric-label">{title}</div>
            <div class="{value_css}">{value_str}</div>
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_metric_card(title: str, value_str: str, sub: str = "") -> None:
    """Render a Bento-style metric card (title + value, optional small line under the value)."""
    sub_html = f'<div class="klimate-metric-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="klimate-card">
            <div class="klimate-metric-label">{title}</div>
            <div class="klimate-metric-value">{value_str}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
