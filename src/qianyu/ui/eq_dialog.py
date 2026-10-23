# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""10-band equalizer dialog."""
from __future__ import annotations

from ..qt import Qt
from ..qt import (
    QCheckBox, QComboBox, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QVBoxLayout,
)

from ..eq import BAND_FREQS, EQ_PRESETS


class EqualizerDialog(QDialog):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._enabled = False
        self.setWindowTitle("10 段均衡器")
        self.setMinimumWidth(560)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("预设"))
        self._preset = QComboBox()
        self._preset.addItems(list(EQ_PRESETS))
        self._preset.currentTextChanged.connect(self._apply_preset)
        top.addWidget(self._preset)
        self._enable = QCheckBox("启用均衡器")
        self._enable.toggled.connect(self._toggle)
        top.addWidget(self._enable)
        top.addStretch(1)
        layout.addLayout(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        self._sliders: list[QSlider] = []
        for index, freq in enumerate(BAND_FREQS):
            label = QLabel(f"{freq} Hz" if freq < 1000 else f"{freq // 1000} kHz")
            label.setAlignment(Qt.AlignHCenter)
            slider = QSlider(Qt.Vertical)
            slider.setRange(-12, 12)
            slider.setValue(0)
            slider.setTickPosition(QSlider.TicksBothSides)
            slider.valueChanged.connect(self._on_slider)
            grid.addWidget(slider, 0, index)
            grid.addWidget(label, 1, index)
            self._sliders.append(slider)
        layout.addLayout(grid)

        bottom = QHBoxLayout()
        reset = QPushButton("重置")
        reset.clicked.connect(self._reset)
        bottom.addWidget(reset)
        bottom.addStretch(1)
        close = QPushButton("关闭")
        close.clicked.connect(self.accept)
        bottom.addWidget(close)
        layout.addLayout(bottom)

    def _bands(self) -> list[int]:
        return [slider.value() for slider in self._sliders]

    def _apply(self) -> None:
        if self._enabled:
            self._engine.set_eq(self._bands())
        else:
            self._engine.clear_eq()

    def _toggle(self, enabled: bool) -> None:
        self._enabled = enabled
        self._apply()

    def _on_slider(self, _value: int) -> None:
        if self._enabled:
            self._apply()

    def _apply_preset(self, name: str) -> None:
        values = EQ_PRESETS.get(name)
        if not values:
            return
        for slider, value in zip(self._sliders, values):
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)
        self._apply()

    def _reset(self) -> None:
        for slider in self._sliders:
            slider.blockSignals(True)
            slider.setValue(0)
            slider.blockSignals(False)
        self._preset.setCurrentText("flat")
        self._apply()
