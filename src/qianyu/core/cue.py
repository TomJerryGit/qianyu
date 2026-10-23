# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""CUE sheet parser for single-file and multi-file album playback."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import mutagen


@dataclass
class CueTrack:
    path: str
    title: str
    artist: str
    album: str
    track_no: int
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass
class CueSheet:
    cue_path: str
    title: str
    performer: str
    audio_path: str
    tracks: list[CueTrack] = field(default_factory=list)


def _timecode(value: str) -> float:
    parts = value.strip().split(":")
    try:
        if len(parts) == 3:
            minutes, seconds, frames = (int(p) for p in parts)
            return minutes * 60 + seconds + frames / 75.0
        if len(parts) == 2:
            minutes, seconds = (int(p) for p in parts)
            return minutes * 60 + seconds
    except ValueError:
        pass
    return 0.0


def _decode(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "gb18030", "big5"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def _duration(path: str) -> float:
    try:
        info = mutagen.File(path)
        return float(info.info.length) if info is not None else 0.0
    except Exception:
        return 0.0


def parse_cue(cue_path: str | Path) -> CueSheet:
    cue = Path(cue_path)
    text = _decode(cue)
    album = ""
    performer = ""
    current_file = ""
    tracks: list[CueTrack] = []
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"(\w+)\s*(.*)", line)
        if not match:
            continue
        key, value = match.group(1).upper(), match.group(2).strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        if key == "FILE":
            if '"' in value:
                current_file = value.split('"')[1]
            else:
                current_file = value.split()[0] if value.split() else ""
        elif key == "TRACK":
            if current is not None:
                tracks.append(current)
            number = int(value.split()[0]) if value.split() else 0
            current = CueTrack(
                path=str((cue.parent / current_file).resolve()) if current_file else "",
                title=f"Track {number:02d}", artist=performer,
                album=album, track_no=number, start=0.0, end=0.0,
            )
        elif key == "TITLE":
            if current is None:
                album = value
            else:
                current.title = value
        elif key == "PERFORMER":
            if current is None:
                performer = value
            else:
                current.artist = value
        elif key == "INDEX" and current is not None:
            parts = value.split()
            if len(parts) >= 2 and parts[0] == "01":
                current.start = _timecode(parts[1])
    if current is not None:
        tracks.append(current)

    if not tracks:
        candidates = [p for p in cue.parent.iterdir() if p.suffix.lower() in
                      (".flac", ".ape", ".wav", ".wv", ".m4a", ".mp3")]
        if candidates:
            tracks = [CueTrack(str(candidates[0]), cue.stem, performer, album, 1, 0.0, _duration(str(candidates[0])))]
    if not any(track.path for track in tracks):
        candidates = [p for p in cue.parent.iterdir() if p.suffix.lower() in
                      (".flac", ".ape", ".wav", ".wv", ".m4a", ".mp3")]
        fallback = str(candidates[0].resolve()) if candidates else ""
        for track in tracks:
            track.path = fallback

    # Compute ends per audio file: next track start in the same file, else file length.
    for index, track in enumerate(tracks):
        track.album = album or cue.stem
        track.artist = track.artist or performer
        next_track = tracks[index + 1] if index + 1 < len(tracks) else None
        if next_track is not None and next_track.path == track.path:
            track.end = next_track.start
        else:
            track.end = _duration(track.path)
        if track.end <= track.start:
            track.end = track.start
    audio_path = tracks[0].path if tracks else ""
    return CueSheet(str(cue), album or cue.stem, performer, audio_path, tracks)
