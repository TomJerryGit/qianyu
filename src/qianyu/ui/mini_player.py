# -*- coding: utf-8 -*-
"""Compact always-on-top player window."""
from __future__ import annotations

from pathlib import Path

from ..qt import QPoint, QSize, Qt, pyqtSignal
from ..qt import QPixmap
from ..qt import (
    QHBoxLayout, QLabel, QPushButton, QStyle, QVBoxLayout, QWidget,
)

from ..core.models import Track


class MiniPlayer(QWidget):
    restore_requested = pyqtSignal()

    def __init__(self, controller, parent=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self._controller = controller
        self._drag_offset: QPoint | None = None
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(380, 118)
        self.setWindowTitle("浅语影音 · 迷你")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self._cover = QLabel()
        self._cover.setFixedSize(94, 94)
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setStyleSheet(
            "background:#20263a;border:1px solid #2f3650;border-radius:8px;"
            "color:#3b6ef5;font-size:34px;"
        )
        self._cover.setText("♪")
        layout.addWidget(self._cover)

        info = QVBoxLayout()
        info.setSpacing(2)
        self._title = QLabel("未在播放")
        self._title.setStyleSheet("background:transparent;color:#f2f5ff;font-size:15px;font-weight:600;")
        self._title.setMaximumWidth(210)
        self._title.setWordWrap(False)
        self._meta = QLabel("")
        self._meta.setStyleSheet("background:transparent;color:#8b93ab;font-size:11px;")
        info.addWidget(self._title)
        info.addWidget(self._meta)
        buttons = QHBoxLayout()
        buttons.setSpacing(2)
        self._prev = self._button(QStyle.SP_MediaSkipBackward, controller._previous)
        self._play = self._button(QStyle.SP_MediaPlay, controller._toggle)
        self._next = self._button(QStyle.SP_MediaSkipForward, controller._next)
        restore = self._button(QStyle.SP_TitleBarNormalButton, lambda: self.restore_requested.emit())
        buttons.addWidget(self._prev)
        buttons.addWidget(self._play)
        buttons.addWidget(self._next)
        buttons.addStretch(1)
        buttons.addWidget(restore)
        info.addLayout(buttons)
        layout.addLayout(info, 1)

        self.setStyleSheet(
            "QWidget{background:rgba(18,21,32,235);border-radius:10px;}"
            "QPushButton{background:transparent;border:0;}"
            "QPushButton:hover{background:#2d3550;border-radius:4px;}"
        )

    def _button(self, icon, slot):
        button = QPushButton(self.style().standardIcon(icon), "")
        button.setFixedSize(28, 26)
        button.clicked.connect(slot)
        return button

    def set_track(self, track: Track | None) -> None:
        if track is None:
            self._title.setText("未在播放")
            self._meta.setText("")
            self._cover.setPixmap(QPixmap())
            self._cover.setText("♪")
            return
        self._title.setText(track.title or Path(track.path).name)
        meta = " · ".join(part for part in (track.artist, track.album) if part)
        self._meta.setText(meta or Path(track.path).parent.name)
        if track.cover and Path(track.cover).exists():
            pixmap = QPixmap(track.cover)
            if not pixmap.isNull():
                self._cover.setPixmap(
                    pixmap.scaled(QSize(94, 94), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return
        self._cover.setPixmap(QPixmap())
        self._cover.setText("♪")

    def set_playing(self, playing: bool) -> None:
        icon = QStyle.SP_MediaPause if playing else QStyle.SP_MediaPlay
        self._play.setIcon(self.style().standardIcon(icon))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        self.restore_requested.emit()
        event.accept()
