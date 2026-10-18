# -*- coding: utf-8 -*-
"""Pure equalizer definitions (no Qt, no libmpv).

Keeping this module dependency-free lets the settings UI and unit tests import
it on machines that do not ship libmpv.
"""
from __future__ import annotations

import math
from typing import Iterable

BAND_FREQS = (32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000)
EQ_PRESETS = {
    "flat": [0] * 10,
    "pop": [0, 1, 3, 4, 3, 1, 0, -1, -2, -2],
    "classical": [5, 4, 3, 1, 0, 0, 0, 1, 3, 4],
    "jazz": [4, 3, 1, 0, 0, 1, 2, 3, 3, 2],
    "rock": [3, 2, 1, 0, 0, 1, 3, 4, 4, 3],
    "electronic": [4, 4, 3, 0, -1, 0, 2, 3, 4, 4],
    "vocal": [-2, -1, 0, 2, 4, 4, 3, 2, 1, 0],
    "bass_boost": [6, 5, 3, 1, 0, 0, 0, 0, 0, 0],
}


def build_eq_filter(bands: Iterable[float], preamp_db: float = 0.0) -> str:
    """Build an FFmpeg filter chain for a 10-band equalizer."""
    values = list(bands)
    if len(values) != 10:
        raise ValueError(f"expected 10 bands, got {len(values)}")
    if any(not math.isfinite(float(v)) for v in values):
        raise ValueError("bands must be finite numbers")
    chain = []
    if preamp_db:
        chain.append(f"volume={preamp_db:.2f}dB")
    for freq, gain in zip(BAND_FREQS, values):
        chain.append(f"equalizer=f={freq}:t=q:w=1:g={float(gain):.2f}")
    return ",".join(chain)
