from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def generate_scene_map(
    case_id: str,
    location: str,
    items: list[dict[str, Any]],
    width: int = 1400,
    height: int = 900,
) -> bytes:
    """
    Generates a clean schematic scene-of-crime map.
    Coordinate convention:
      X = 0..100 left-to-right (west to east)
      Y = 0..100 bottom-to-top (south to north)
    North is ALWAYS at the top.
    """
    img = Image.new("RGB", (width, height), "#F7F9FC")
    d = ImageDraw.Draw(img)

    navy = "#132238"
    blue = "#315EAF"
    red = "#B73B45"
    grid = "#D9E1EA"
    muted = "#65758B"
    white = "#FFFFFF"

    title_f = _font(38, True)
    sub_f = _font(20)
    label_f = _font(20, True)
    small_f = _font(16)
    tiny_f = _font(13)

    # Header
    d.rectangle((0, 0, width, 110), fill=navy)
    d.text((45, 24), "MORBIT — Scene of Crime Map", font=title_f, fill=white)
    d.text((45, 70), f"Case: {case_id}   |   Location: {location or 'Not recorded'}", font=sub_f, fill="#DDE8F7")

    # Plot area
    left, top, right, bottom = 90, 165, width - 90, height - 100
    d.rounded_rectangle((left, top, right, bottom), radius=18, fill=white, outline="#B9C7D8", width=3)

    # Grid
    for i in range(11):
        x = left + (right - left) * i / 10
        y = top + (bottom - top) * i / 10
        d.line((x, top, x, bottom), fill=grid, width=1)
        d.line((left, y, right, y), fill=grid, width=1)
        d.text((x - 8, bottom + 12), f"{i*10}", font=tiny_f, fill=muted)
        d.text((left - 38, bottom - (bottom-top)*i/10 - 8), f"{i*10}", font=tiny_f, fill=muted)

    # Axis annotations
    d.text((width//2 - 120, bottom + 44), "X coordinate: West → East", font=small_f, fill=muted)
    d.text((12, top + 260), "Y: South → North", font=small_f, fill=muted)

    # North arrow always up
    cx = width - 150
    d.text((cx - 10, 120), "N", font=label_f, fill=red)
    d.line((cx, 158, cx, 225), fill=red, width=7)
    d.polygon([(cx, 140), (cx-16, 174), (cx+16, 174)], fill=red)

    colors = {
        "Evidence": "#D43F52",
        "Entry/Exit": "#2166B1",
        "Body/Remains": "#7B3FA1",
        "Vehicle": "#E4932D",
        "Furniture/Object": "#357A5B",
        "Hazard": "#D16A25",
        "Reference Point": "#1E7E8C",
        "Other": "#5A6675",
    }

    # Plot items
    for idx, item in enumerate(items, start=1):
        try:
            x_pct = max(0, min(100, float(item.get("X", 50))))
            y_pct = max(0, min(100, float(item.get("Y", 50))))
        except Exception:
            continue
        x = left + (right-left) * x_pct / 100
        y = bottom - (bottom-top) * y_pct / 100
        typ = str(item.get("Type") or "Other")
        color = colors.get(typ, colors["Other"])
        r = 12
        d.ellipse((x-r, y-r, x+r, y+r), fill=color, outline=white, width=2)
        label = str(item.get("Label") or f"Item {idx}")
        d.text((x + 16, y - 12), label, font=small_f, fill=navy)

    # Legend
    legend_y = height - 64
    x = 90
    for typ, color in colors.items():
        d.rectangle((x, legend_y, x+15, legend_y+15), fill=color)
        d.text((x+22, legend_y-2), typ, font=tiny_f, fill=muted)
        x += 155
        if x > width - 170:
            break

    # Disclaimer
    d.text(
        (90, height - 28),
        "Schematic only — not to scale unless calibrated by the investigator. North is fixed at the top.",
        font=tiny_f,
        fill=muted,
    )

    out = BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()
