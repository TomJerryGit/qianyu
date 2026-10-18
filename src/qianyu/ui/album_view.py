# -*- coding: utf-8 -*-
"""Album / artist cover grid."""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

from ..qt import (
    QColor, QComboBox, QHBoxLayout, QIcon, QLabel, QListWidget,
    QListWidgetItem, QPainter, QPixmap, QSize, Qt, QVBoxLayout, QWidget,
    pyqtSignal,
)
from ..core.models import Track

GRID_SIZE = QSize(190, 232)
ICON_SIZE = QSize(160, 160)


class AlbumView(QWidget):
    activated = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("分组"))
        self._mode = QComboBox()
        self._mode.addItem("专辑", "album")
        self._mode.addItem("艺术家", "artist")
        self._mode.currentIndexChanged.connect(lambda _i: self._mode_changed())
        bar.addWidget(self._mode)
        bar.addStretch(1)
        layout.addLayout(bar)
        self._grid = QListWidget()
        self._grid.setViewMode(QListWidget.IconMode)
        self._grid.setResizeMode(QListWidget.Adjust)
        self._grid.setMovement(QListWidget.Static)
        self._grid.setSpacing(12)
        self._grid.setIconSize(ICON_SIZE)
        self._grid.setGridSize(GRID_SIZE)
        self._grid.setWordWrap(True)
        self._grid.itemDoubleClicked.connect(self._on_activated)
        layout.addWidget(self._grid, 1)
        self._tracks: list[Track] = []
        self._cover_cache: dict[str, QIcon] = {}
        self._signature = None

    def set_tracks(self, tracks) -> None:
        tracks = list(tracks)
        signature = (
            self._mode.currentData(),
            tuple((track.path, track.album, track.artist, track.cover) for track in tracks),
        )
        if signature == self._signature:
            return
        self._signature = signature
        self._tracks = tracks
        self._rebuild()

    def _mode_changed(self) -> None:
        self._signature = None
        self._rebuild()

    def _group_key(self, track: Track) -> str:
        mode = self._mode.currentData()
        if mode == "artist":
            return track.artist or "未知艺术家"
        return track.album or "未知专辑"

    def _rebuild(self) -> None:
        groups: "OrderedDict[str, list[Track]]" = OrderedDict()
        for track in self._tracks:
            groups.setdefault(self._group_key(track), []).append(track)
        self._grid.clear()
        for key, tracks in groups.items():
            cover = next((t.cover for t in tracks if t.cover and Path(t.cover).exists()), "")
            item = QListWidgetItem(self._icon(cover, key), self._label(key, tracks))
            item.setData(Qt.UserRole, key)
            item.setTextAlignment(Qt.AlignHCenter)
            item.setToolTip(f"{key}\n{len(tracks)} 首")
            self._grid.addItem(item)

    def _label(self, key: str, tracks: list[Track]) -> str:
        if self._mode.currentData() == "artist":
            return f"{key}\n{len(tracks)} 首"
        artist = tracks[0].artist or "未知艺术家"
        return f"{key}\n{artist} · {len(tracks)} 首"

    def _icon(self, cover: str, key: str) -> QIcon:
        if cover:
            cached = self._cover_cache.get(cover)
            if cached is not None:
                return cached
            pixmap = QPixmap(cover)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(ICON_SIZE, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                icon = QIcon(pixmap)
                self._cover_cache[cover] = icon
                return icon
        return QIcon(self._placeholder(key))

    @staticmethod
    def _placeholder(key: str) -> QPixmap:
        pixmap = QPixmap(ICON_SIZE)
        hue = abs(hash(key)) % 360
        color = QColor.fromHsv(hue, 95, 120)
        pixmap.fill(color)
        painter = QPainter(pixmap)
        painter.setPen(QColor(235, 240, 255))
        font = painter.font()
        font.setPointSize(44)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "♪")
        painter.end()
        return pixmap

    def _on_activated(self, item: QListWidgetItem) -> None:
        key = item.data(Qt.UserRole)
        if key:
            self.activated.emit(str(key))
