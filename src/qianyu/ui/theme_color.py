# -*- coding: utf-8 -*-
"""Cover-derived accent color for the Qt stylesheet."""
from __future__ import annotations

from pathlib import Path

from ..qt import QColor

try:
    from PIL import Image
except Exception:  # pragma: no cover - Pillow is a runtime dependency
    Image = None


def dominant_color(path: str) -> QColor | None:
    if not path or Image is None or not Path(path).exists():
        return None
    try:
        image = Image.open(path).convert("RGB").resize((48, 48))
    except Exception:
        return None
    colors = image.getcolors(48 * 48) or []
    colors.sort(key=lambda item: item[0], reverse=True)
    # Prefer a reasonably saturated, non-near-black/white color.
    for count, (red, green, blue) in colors[:12]:
        high, low = max(red, green, blue), min(red, green, blue)
        if high < 40 or low > 225 or high - low < 18:
            continue
        return QColor(red, green, blue)
    for _count, (red, green, blue) in colors[:1]:
        return QColor(red, green, blue)
    return None
