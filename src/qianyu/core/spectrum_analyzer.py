# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Local-file spectrum analysis using the bundled FFmpeg.

This is intentionally small and dependency-free: FFmpeg decodes a local file to
8 kHz mono PCM, then a Goertzel filter computes log-spaced band levels. It is a
real audio analysis (not the decorative fallback), intended for local files.
"""
from __future__ import annotations

import array
import math
import subprocess
from pathlib import Path
from typing import Callable

BANDS = 24
SAMPLE_RATE = 8000
FRAME = 512
HOP = 512
MIN_FREQ = 60.0
MAX_FREQ = 3600.0


def _frequencies(bands: int = BANDS) -> list[float]:
    low = math.log(MIN_FREQ)
    high = math.log(MAX_FREQ)
    return [math.exp(low + (high - low) * index / max(1, bands - 1))
            for index in range(bands)]


def analyze_pcm(pcm: bytes, sample_rate: int = SAMPLE_RATE,
                frame: int = FRAME, hop: int = HOP,
                bands: int = BANDS) -> list[tuple[float, tuple[float, ...]]]:
    samples = array.array("h")
    samples.frombytes(pcm[:len(pcm) // 2 * 2])
    if not samples:
        return []
    frequencies = _frequencies(bands)
    coeffs = [2.0 * math.cos(2.0 * math.pi * freq / sample_rate) for freq in frequencies]
    frames: list[tuple[float, tuple[float, ...]]] = []
    index = 0
    while index + frame <= len(samples):
        window = samples[index:index + frame]
        levels = []
        for coeff in coeffs:
            s0 = s1 = s2 = 0.0
            for value in window:
                s0 = value + coeff * s1 - s2
                s2, s1 = s1, s0
            power = max(0.0, s1 * s1 + s2 * s2 - coeff * s1 * s2)
            magnitude = math.sqrt(power) / frame / 32768.0
            decibels = 20.0 * math.log10(magnitude + 1e-9)
            level = (decibels + 60.0) / 60.0
            levels.append(max(0.0, min(1.0, level)))
        frames.append((index / sample_rate, tuple(levels)))
        index += hop
    return frames


def analyze_file(path: str, timeout: float = 600.0,
                 cancelled: Callable[[], bool] | None = None
                 ) -> list[tuple[float, tuple[float, ...]]]:
    path = str(path)
    if not Path(path).is_file():
        return []
    try:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return []
    command = [
        ffmpeg, "-v", "error", "-i", path,
        "-t", str(int(timeout)), "-f", "s16le", "-ac", "1",
        "-ar", str(SAMPLE_RATE), "-",
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    try:
        pcm = process.stdout.read() if process.stdout is not None else b""
        if cancelled is not None and cancelled():
            return []
        return analyze_pcm(pcm)
    except Exception:
        return []
    finally:
        try:
            process.kill()
        except Exception:
            pass
        try:
            process.wait(timeout=2)
        except Exception:
            pass
