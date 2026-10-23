# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Virtualized table model for the music library.

QTableView only asks for visible rows, so a 10k-track library no longer rebuilds
thousands of QTableWidgetItem objects on every refresh.
"""
from __future__ import annotations

from typing import Iterable

from ..qt import QAbstractTableModel, QModelIndex, Qt

from ..core.models import Track

HEADERS = ("标题", "艺术家", "专辑", "时长")


def _format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds or 0))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:02d}:{sec:02d}"


class TrackTableModel(QAbstractTableModel):
    def __init__(self, tracks: Iterable[Track] | None = None, parent=None):
        super().__init__(parent)
        self._tracks: list[Track] = list(tracks or [])

    def set_tracks(self, tracks: Iterable[Track]) -> None:
        self.beginResetModel()
        self._tracks = list(tracks)
        self.endResetModel()

    def track_at(self, row: int) -> Track | None:
        if 0 <= row < len(self._tracks):
            return self._tracks[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._tracks)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._tracks)):
            return None
        track = self._tracks[index.row()]
        if role == Qt.DisplayRole:
            title = f"★ {track.title}" if getattr(track, "favorite", False) else track.title
            return (
                title,
                track.artist,
                track.album,
                _format_duration(track.duration),
            )[index.column()]
        if role == Qt.UserRole:
            return track
        if role == Qt.ToolTipRole:
            return track.path
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return HEADERS[section]
        return None
