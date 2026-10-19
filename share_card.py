"""Render the Wrapped stats as a shareable PNG (Pillow only, no font files needed)."""
from __future__ import annotations

import io
from typing import Dict

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
NAVY_TOP, NAVY_BOTTOM = (15, 23, 42), (2, 6, 23)
CYAN, GREEN, TEXT, MUTED, TILE = (6, 182, 212), (16, 185, 129), (248, 250, 252), (148, 163, 184), (30, 41, 59)


def _font(size: int) -> ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def _center(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (box[2] - box[0])) / 2, y), text, font=font, fill=fill)


def _fit(draw: ImageDraw.ImageDraw, text: str, max_w: int, start: int):
    """Largest font (down to 22px) whose rendering of ``text`` fits ``max_w``."""
    for size in range(start, 21, -2):
        f = _font(size)
        if draw.textlength(text, font=f) <= max_w:
            return f
    return _font(22)


def render_wrapped_png(username: str, stats: Dict[str, str], url: str = "klimate.streamlit.app") -> bytes:
    img = Image.new("RGB", (W, H), NAVY_BOTTOM)
    d = ImageDraw.Draw(img)
    for y in range(H):  # vertical gradient
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(NAVY_TOP[i] + (NAVY_BOTTOM[i] - NAVY_TOP[i]) * t) for i in range(3)))

    _center(d, 90, "KLIMATE CHESS DNA", _font(34), MUTED)
    _center(d, 150, username.upper(), _fit(d, username.upper(), 900, 96), CYAN)
    _center(d, 300, str(stats.get("peak_rating", "N/A")), _font(190), GREEN)
    _center(d, 520, str(stats.get("peak_label", "All-time peak")).upper(), _font(34), MUTED)

    tiles = [
        ("WINS", stats.get("wins", "N/A")),
        ("BEST OPENING", stats.get("best_opening", "N/A")),
        ("PRIME TIME", stats.get("prime_time", "N/A")),
        ("PLAYS LIKE (FOR FUN)", stats.get("gm_match", "N/A")),
    ]
    x0, y0, tw, th, gap = 60, 620, 450, 250, 60
    for i, (label, value) in enumerate(tiles):
        x, y = x0 + (i % 2) * (tw + gap), y0 + (i // 2) * (th + gap)
        d.rounded_rectangle([x, y, x + tw, y + th], radius=28, fill=TILE)
        d.text((x + 30, y + 30), label, font=_font(28), fill=MUTED)
        value = str(value)
        f = _fit(d, value, tw - 60, 44)
        # wrap to two lines when still long
        if d.textlength(value, font=f) > tw - 60 and " " in value:
            mid = value.rfind(" ", 0, len(value) // 2 + 6) or value.find(" ")
            d.text((x + 30, y + 100), value[:mid], font=f, fill=TEXT)
            d.text((x + 30, y + 100 + 56), value[mid + 1 :], font=f, fill=TEXT)
        else:
            d.text((x + 30, y + 110), value, font=f, fill=TEXT)

    _center(d, 1230, f"Find your chess DNA at {url}", _font(32), CYAN)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_weekly_png(username: str, period: str, tiles: list, footer: str = "klimate.streamlit.app") -> bytes:
    """Shareable weekly summary. ``tiles`` is a list of (label, value, change_text) with up to four entries."""
    img = Image.new("RGB", (W, H), NAVY_BOTTOM)
    d = ImageDraw.Draw(img)
    for y in range(H):
        t_ = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(NAVY_TOP[i] + (NAVY_BOTTOM[i] - NAVY_TOP[i]) * t_) for i in range(3)))
    _center(d, 90, "MY WEEK ON KLIMATE", _font(38), MUTED)
    _center(d, 170, username.upper(), _fit(d, username.upper(), 900, 84), CYAN)
    _center(d, 290, period, _font(34), TEXT)
    x0, y0, tw, th, gap = 60, 400, 450, 330, 60
    for i, (label, value, change) in enumerate(tiles[:4]):
        x, y = x0 + (i % 2) * (tw + gap), y0 + (i // 2) * (th + gap)
        d.rounded_rectangle([x, y, x + tw, y + th], radius=28, fill=TILE)
        d.text((x + 30, y + 30), label.upper(), font=_font(30), fill=MUTED)
        d.text((x + 30, y + 100), str(value), font=_fit(d, str(value), tw - 60, 96), fill=TEXT)
        colour = GREEN if str(change).startswith("+") else ((239, 68, 68) if str(change).startswith("-") else MUTED)
        d.text((x + 30, y + 240), str(change), font=_font(32), fill=colour)
    _center(d, 1230, footer, _font(32), CYAN)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
