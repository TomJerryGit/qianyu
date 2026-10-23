# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Frameless always-on-top desktop lyrics window (0.9)."""
from __future__ import annotations

from ..qt import QPoint, Qt, pyqtSignal
from ..qt import QLabel, QVBoxLayout, QWidget


class DesktopLyricsWindow(QWidget):
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowTitle("桌面歌词")
        self.resize(920, 132)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(2)
        self._current = QLabel("浅语影音")
        self._current.setAlignment(Qt.AlignCenter)
        self._current.setStyleSheet(
            "color:#ffffff;background:rgba(10,12,20,150);border-radius:10px;"
            "font-size:30px;font-weight:600;padding:6px 18px;"
        )
        self._next = QLabel("")
        self._next.setAlignment(Qt.AlignCenter)
        self._next.setStyleSheet(
            "color:rgba(255,255,255,190);background:rgba(10,12,20,110);"
            "border-radius:8px;font-size:18px;padding:2px 14px;"
        )
        layout.addWidget(self._current)
        layout.addWidget(self._next)
        self._drag_offset: QPoint | None = None

    def set_lines(self, current: str, upcoming: str = "") -> None:
        self._current.setText(current or "♪")
        self._next.setText(upcoming or "")

    def show_at_default(self) -> None:
        screen = self.screen() or self.window().screen()
        if screen is not None:
            area = screen.availableGeometry()
            self.move(area.center().x() - self.width() // 2, area.bottom() - self.height() - 80)
        self.show()

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

    def closeEvent(self, event) -> None:
        self.hide()
        self.closed.emit()
        event.ignore()
