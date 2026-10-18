# -*- coding: utf-8 -*-
"""LRC lyrics parsing with encoding detection.

Pure functions, no UI and no Qt, so they can be fuzzed and unit-tested.
"""
from __future__ import annotations

import bisect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# [mm:ss.xx] / [mm:ss.xxx] / [mm:ss]
_TIME = re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")
_OFFSET = re.compile(r"\[offset:\s*([+-]?\d+)\s*\]", re.IGNORECASE)
_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "utf-16", "utf-16-le", "utf-16-be")


@dataclass(frozen=True)
class LrcLine:
    time_ms: int
    text: str


def decode_lrc(raw: bytes) -> str:
    for encoding in _ENCODINGS:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return raw.decode("utf-8", errors="replace")


def parse_lrc(text: str) -> list[LrcLine]:
    """Parse an LRC document into sorted, de-duplicated lines."""
    offset = 0
    match = _OFFSET.search(text)
    if match:
        try:
            offset = int(match.group(1))
        except ValueError:
            offset = 0

    lines: list[LrcLine] = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("[ti:") or raw.startswith("[ar:") or raw.startswith("[al:"):
            continue
        stamps = list(_TIME.finditer(raw))
        if not stamps:
            continue
        content = _TIME.sub("", raw).strip()
        if not content:
            continue
        for stamp in stamps:
            minutes = int(stamp.group(1))
            seconds = int(stamp.group(2))
            frac = stamp.group(3) or "0"
            # .5 means 500 ms, .50 means 500 ms, .500 means 500 ms
            millis = int((frac + "00")[:3]) if len(frac) < 3 else int(frac[:3])
            total = minutes * 60_000 + seconds * 1000 + millis + offset
            if total >= 0:
                lines.append(LrcLine(time_ms=total, text=content))

    lines.sort(key=lambda line: line.time_ms)
    deduped: list[LrcLine] = []
    for line in lines:
        if deduped and deduped[-1].time_ms == line.time_ms and deduped[-1].text == line.text:
            continue
        deduped.append(line)
    return deduped


def load_lrc(path: str | Path) -> list[LrcLine]:
    return parse_lrc(decode_lrc(Path(path).read_bytes()))


def find_lrc(audio_path: str | Path) -> Path | None:
    audio = Path(audio_path)
    for suffix in (".lrc", ".LRC"):
        candidate = audio.with_suffix(suffix)
        if candidate.exists():
            return candidate
    return None


def line_index_at(lines: Iterable[LrcLine], position_ms: int) -> int:
    """Return the index of the active line, or -1 before the first line."""
    ordered = list(lines)
    if not ordered:
        return -1
    times = [line.time_ms for line in ordered]
    return bisect.bisect_right(times, int(position_ms)) - 1
