# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Playlist persistence (JSON, atomic replace)."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import Playlist


class PlaylistStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.playlist = Playlist()
        self.load()

    def load(self) -> Playlist:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.playlist = Playlist.from_dict(data)
        except (OSError, ValueError, TypeError):
            self.playlist = Playlist()
        return self.playlist

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(self.playlist.to_dict(), ensure_ascii=False, indent=2)
            fd, tmp = tempfile.mkstemp(prefix=self.path.name + ".", dir=str(self.path.parent))
        except OSError:
            return
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        except OSError:
            pass
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
