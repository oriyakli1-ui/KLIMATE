"""Create profile pictures and banners for the social accounts from logo.png (run: py -3.13 tools/make_brand_assets.py)."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "brand"
OUT.mkdir(exist_ok=True)
logo = Image.open(ROOT / "logo.png").convert("RGBA")
BG = logo.getpixel((5, 5))[:3]          # the logo's own background colour, so edges blend


def canvas(w: int, h: int, logo_h_ratio: float, dx: float = 0.5) -> Image.Image:
    img = Image.new("RGB", (w, h), BG)
    target_h = int(h * logo_h_ratio)
    lw = int(logo.width * target_h / logo.height)
    if lw > w * 0.9:                     # never wider than the canvas
        lw = int(w * 0.9)
        target_h = int(logo.height * lw / logo.width)
    mark = logo.resize((lw, target_h), Image.LANCZOS)
    img.paste(mark, (int((w - lw) * dx), (h - target_h) // 2), mark)
    return img


canvas(1024, 1024, 0.62).save(OUT / "avatar-square-1024.png")                 # all platforms' profile picture
canvas(256, 256, 0.62).save(OUT / "reddit-avatar-256.png")
canvas(2560, 1440, 0.30).save(OUT / "youtube-banner-2560x1440.png")           # key content sits in the centre safe area
canvas(1640, 856, 0.40).save(OUT / "facebook-cover-1640x856.png")
canvas(1920, 384, 0.70).save(OUT / "reddit-banner-1920x384.png")
print(sorted(p.name for p in OUT.iterdir()))
