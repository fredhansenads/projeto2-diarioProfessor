"""Render the existing d. wordmark into opaque icons. Pass a bold serif TTF path."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

destination = Path(__file__).resolve().parents[1] / "static/diary"
for size in (180, 192, 512):
    # Supersampling and a centered mark contained within the maskable safe zone.
    canvas = Image.new("RGB", (size * 4, size * 4), "#244e43")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(sys.argv[1], size * 2)
    box = draw.textbbox((0, 0), "d.", font=font)
    x = (size * 4 - box[2] + box[0]) / 2 - box[0]
    y = (size * 4 - box[3] + box[1]) / 2 - box[1]
    draw.text((x, y), "d.", fill="white", font=font)
    canvas.resize((size, size), Image.Resampling.LANCZOS).save(destination / f"icon-{size}.png")
