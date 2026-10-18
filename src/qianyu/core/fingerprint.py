# -*- coding: utf-8 -*-
"""Optional Chromaprint fingerprinting through the external `fpcalc` binary."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def find_fpcalc() -> str | None:
    override = os.environ.get("QIANYU_FPCALC", "").strip()
    if override and Path(override).is_file():
        return override
    local = Path(__file__).resolve().parents[3] / "tools" / "fpcalc.exe"
    if local.is_file():
        return str(local)
    return shutil.which("fpcalc")


def audio_fingerprint(path: str, length: int = 120) -> tuple[int, ...] | None:
    executable = find_fpcalc()
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "-raw", "-json", "-length", str(length), path],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode != 0:
            return None
        payload = json.loads(result.stdout)
        return tuple(int(value) for value in payload.get("fingerprint", []))
    except Exception:
        return None


def similarity(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    left, right = left[:size], right[:size]
    equal = sum(1 for a, b in zip(left, right) if int(a) == int(b))
    return equal / size


def _ffmpeg_executable() -> str | None:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


def content_fingerprint(path: str, seconds: int = 60) -> tuple[int, ...] | None:
    """Offline PCM-envelope fingerprint used when Chromaprint is unavailable.

    This is deliberately lightweight: decode mono 4 kHz PCM, then quantize RMS
    over 50 ms windows. It catches transcoded/re-encoded copies of the same
    recording; it is not a replacement for Chromaprint's acoustic matching.
    """
    executable = _ffmpeg_executable()
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "-v", "error", "-i", path, "-t", str(seconds),
             "-ac", "1", "-ar", "4000", "-f", "s16le", "-"],
            capture_output=True, timeout=40,
        )
    except Exception:
        return None
    if result.returncode != 0 or not result.stdout:
        return None
    import array
    import math

    samples = array.array("h")
    samples.frombytes(result.stdout[: len(result.stdout) // 2 * 2])
    window = 200  # 50 ms at 4 kHz
    values = []
    for start in range(0, len(samples), window):
        chunk = samples[start:start + window]
        if not chunk:
            break
        rms = math.sqrt(sum(value * value for value in chunk) / len(chunk))
        values.append(min(255, int(rms / 40)))
    return tuple(values)


def envelope_similarity(left: tuple[int, ...], right: tuple[int, ...]) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    left, right = left[:size], right[:size]
    mean_left = sum(left) / size
    mean_right = sum(right) / size
    numerator = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    denom_left = sum((a - mean_left) ** 2 for a in left) ** 0.5
    denom_right = sum((b - mean_right) ** 2 for b in right) ** 0.5
    if not denom_left or not denom_right:
        return max(0.0, 1.0 - abs(mean_left - mean_right) / 255.0)
    return max(0.0, numerator / (denom_left * denom_right))
