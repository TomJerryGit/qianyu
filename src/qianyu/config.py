# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""User configuration (JSON, atomic write, schema-tolerant)."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

DEFAULTS = {
    "theme": "dark",
    "volume": 70,
    "library_folders": [],
    "last_folder": "",
    "close_to_tray": True,
    "global_media_keys": True,
    "replaygain": "no",
    "audio_exclusive": False,
    "update_url": "",
    "update_public_key": "",
    "video_gesture_overlay": True,
    "video_gesture_windowed": False,
    "podcast_cache_limit_mb": 2048,
    "listenbrainz_enabled": False,
    "listenbrainz_token": "",
    "window": {"w": 1180, "h": 760},
}


class Config:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else Path.home() / ".qianyu_media" / "config.json"
        self._data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, value in raw.items():
                    self._data[key] = value
        except (OSError, ValueError):
            pass

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=self.path.name + ".", dir=str(self.path.parent))
        except OSError:
            return
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except OSError:
            pass
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
