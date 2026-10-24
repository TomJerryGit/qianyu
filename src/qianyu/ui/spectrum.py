# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Decorative spectrum visualizer for the classic now-playing page.

The animation is driven by the playback state and volume; it does not claim to
be a calibrated audio analyser.
"""
from __future__ import annotations

import math

from ..qt import QColor, QPainter, QPen, QTimer, QWidget, Qt, pyqtSignal

BARS = 48


class SpectrumWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(86)
        self.setMaximumHeight(110)
        self._phase = 0.0
        self._playing = False
        self._levels = [0.0] * BARS
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    def set_playing(self, playing: bool) -> None:
        self._playing = bool(playing)

    def _advance(self) -> None:
        if not self.isVisible():
            return
        self._phase += 0.12
        for index in range(BARS):
            if self._playing:
                wave = abs(math.sin(self._phase + index * 0.21))
                bass = max(0.0, 1.0 - index / (BARS * 0.6))
                target = 0.12 + 0.58 * wave + 0.25 * bass * abs(math.sin(self._phase * 0.7))
            else:
                target = 0.02
            self._levels[index] += (target - self._levels[index]) * 0.35
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        width = self.width() / BARS
        height = self.height()
        for index, level in enumerate(self._levels):
            bar_height = max(2, int(height * min(1.0, level)))
            ratio = index / max(1, BARS - 1)
            color = QColor(
                int(80 + 120 * ratio),
                int(210 - 60 * ratio),
                int(160 + 60 * (1 - ratio)),
                210,
            )
            painter.fillRect(
                int(index * width + 1), height - bar_height,
                max(1, int(width) - 2), bar_height, color,
            )
        painter.setPen(QPen(QColor(140, 220, 180, 80), 1))
        painter.drawLine(0, height - 1, self.width(), height - 1)
