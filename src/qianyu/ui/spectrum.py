# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Spectrum visualizer for the classic now-playing page.

When a local file has been analysed by FFmpeg, real band levels are used and
follow the playback position. Until then (or for streams) a decorative
animation is shown.
"""
from __future__ import annotations

import math

from ..qt import QColor, QPainter, QPen, QTimer, QWidget, Qt

BARS = 48
FRAME_SECONDS = 512 / 8000


class SpectrumWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(86)
        self.setMaximumHeight(110)
        self._phase = 0.0
        self._playing = False
        self._levels = [0.0] * BARS
        self._frames: list[tuple[float, tuple[float, ...]]] | None = None
        self._position = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    def set_playing(self, playing: bool) -> None:
        self._playing = bool(playing)

    def set_frames(self, frames) -> None:
        self._frames = list(frames) if frames else None

    def set_position(self, seconds: float) -> None:
        self._position = max(0.0, float(seconds or 0.0))

    def _real_levels(self) -> list[float] | None:
        if not self._frames:
            return None
        index = int(self._position / FRAME_SECONDS)
        index = max(0, min(index, len(self._frames) - 1))
        levels = self._frames[index][1]
        if not levels:
            return None
        result = []
        for bar in range(BARS):
            position = bar / max(1, BARS - 1) * (len(levels) - 1)
            low = int(math.floor(position))
            high = min(len(levels) - 1, low + 1)
            fraction = position - low
            result.append(levels[low] * (1 - fraction) + levels[high] * fraction)
        return result

    def _advance(self) -> None:
        if not self.isVisible():
            return
        real = self._real_levels() if self._playing else None
        if real is not None:
            for index, target in enumerate(real):
                self._levels[index] += (target - self._levels[index]) * 0.45
        else:
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
