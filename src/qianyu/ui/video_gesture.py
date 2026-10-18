# -*- coding: utf-8 -*-
"""Top-level fullscreen gesture layer.

Airspace blocks Qt *child* widgets over mpv's native child window, but a
separate top-level translucent window can sit above it. This layer is enabled
only in fullscreen (where covering the screen is expected) and forwards simple
mouse/touch gestures to VideoWindow.
"""
from __future__ import annotations

from ..qt import (
    QApplication, QColor, QFont, QPainter, QPoint, Qt, QTimer, QWidget,
)


class GestureOverlay(QWidget):
    def __init__(self, video):
        super().__init__(None)
        self._video = video
        self._press: QPoint | None = None
        self._message = ""
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._clear_message)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setFocusPolicy(Qt.NoFocus)
        self.setGeometry(QApplication.primaryScreen().geometry())

    def show_overlay(self) -> None:
        screen = self._video.screen() or QApplication.primaryScreen()
        self.setGeometry(screen.geometry())
        self.show()
        self.raise_()

    def show_at(self, rect) -> None:
        self.setGeometry(rect)
        self.show()
        self.raise_()

    def _feedback(self, text: str) -> None:
        self._message = text
        self._timer.start(1200)
        self.update()

    def _clear_message(self) -> None:
        self._message = ""
        self.update()

    def paintEvent(self, event) -> None:
        if not self._message:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bar = self.rect()
        painter.fillRect(0, bar.height() - 54, bar.width(), 54, QColor(0, 0, 0, 150))
        painter.setPen(QColor(255, 255, 255))
        font = QFont()
        font.setPointSize(16)
        painter.setFont(font)
        painter.drawText(24, bar.height() - 20, self._message)

    def mousePressEvent(self, event) -> None:
        self._press = event.pos()
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._press is None:
            return
        delta = event.pos() - self._press
        self._press = None
        if abs(delta.x()) > 60 and abs(delta.x()) > abs(delta.y()):
            seconds = 10 if delta.x() > 0 else -10
            self._video._seek_relative(seconds)
            self._feedback(f"跳转 {seconds:+d} s")
        elif abs(delta.y()) > 60:
            volume = self._video._volume.value() + (5 if delta.y() < 0 else -5)
            self._video._volume.setValue(max(0, min(100, volume)))
            self._feedback(f"音量 {self._video._volume.value()}%")
        else:
            self._video.toggle()
            self._feedback("播放/暂停")
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        self._video.toggle_fullscreen()
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self._video.toggle_fullscreen()
        elif event.key() == Qt.Key_Space:
            self._video.toggle()
        else:
            super().keyPressEvent(event)
