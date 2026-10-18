# -*- coding: utf-8 -*-
"""Domain models shared by the music library, playlists and UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Track:
    path: str
    title: str
    artist: str = ""
    album: str = ""
    duration: float = 0.0
    track_no: int = 0
    disc_no: int = 0
    codec: str = ""
    sample_rate: int = 0
    channels: int = 0
    bitrate: int = 0
    cover: str = ""
    cue_path: str = ""
    start: float = 0.0
    end: float = 0.0
    favorite: bool = False
    play_count: int = 0
    last_played: float = 0.0
    added_at: float = 0.0

    @property
    def filename(self) -> str:
        return Path(self.path).name

    @property
    def display(self) -> str:
        if self.artist:
            return f"{self.artist} - {self.title}"
        return self.title or self.filename

    @property
    def exists(self) -> bool:
        return Path(self.path).is_file()


@dataclass
class PlaylistItem:
    path: str
    title: str = ""

    @property
    def display(self) -> str:
        return self.title or Path(self.path).name


@dataclass
class Playlist:
    name: str = "默认列表"
    items: list[PlaylistItem] = field(default_factory=list)
    current_index: int = -1
    loop_mode: str = "sequential"  # sequential | single

    def add(self, path: str, title: str = "") -> bool:
        path = str(Path(path).resolve())
        if any(item.path == path for item in self.items):
            return False
        self.items.append(PlaylistItem(path=path, title=title))
        return True

    def remove(self, index: int) -> bool:
        if not (0 <= index < len(self.items)):
            return False
        del self.items[index]
        if self.current_index >= len(self.items):
            self.current_index = len(self.items) - 1
        return True

    def clear(self) -> None:
        self.items.clear()
        self.current_index = -1

    def move(self, src: int, dst: int) -> bool:
        if not (0 <= src < len(self.items)) or not (0 <= dst < len(self.items)):
            return False
        item = self.items.pop(src)
        self.items.insert(dst, item)
        if self.current_index == src:
            self.current_index = dst
        return True

    @property
    def current(self) -> Optional[PlaylistItem]:
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None

    def select(self, index: int) -> Optional[PlaylistItem]:
        if not self.items:
            self.current_index = -1
            return None
        self.current_index = max(0, min(int(index), len(self.items) - 1))
        return self.current

    def next(self) -> Optional[PlaylistItem]:
        if not self.items:
            return None
        if self.loop_mode == "single" and self.current is not None:
            return self.current
        self.current_index = (self.current_index + 1) % len(self.items)
        return self.current

    def previous(self) -> Optional[PlaylistItem]:
        if not self.items:
            return None
        if self.loop_mode == "single" and self.current is not None:
            return self.current
        self.current_index = (self.current_index - 1) % len(self.items)
        return self.current

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "current_index": self.current_index,
            "loop_mode": self.loop_mode,
            "items": [{"path": i.path, "title": i.title} for i in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Playlist":
        items = [
            PlaylistItem(path=str(i.get("path", "")), title=str(i.get("title", "")))
            for i in data.get("items", [])
            if i.get("path")
        ]
        return cls(
            name=str(data.get("name", "默认列表")),
            items=items,
            current_index=int(data.get("current_index", -1)),
            loop_mode=str(data.get("loop_mode", "sequential")),
        )
