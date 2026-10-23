# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Classic tabletop-radio view for internet radio playback."""
from __future__ import annotations

import re

from ..qt import (
    QDial, QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout,
    QWidget, Qt, pyqtSignal,
)
from ..core.radio import RadioStation

RADIO_STYLE = """
#radioShell {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3a2416, stop:0.45 #24160e, stop:1 #120b07);
    border: 1px solid #6b4a2e;
    border-radius: 18px;
}
#radioBrand {
    color: #f3d9a4;
    font-size: 13px;
    letter-spacing: 5px;
    font-weight: 700;
}
#radioModel {
    color: #9e7a4e;
    font-size: 10px;
    letter-spacing: 2px;
}
#radioDisplay {
    background: #071b16;
    border: 2px solid #314f42;
    border-radius: 10px;
    color: #b9ffd8;
    font-family: "Consolas", monospace;
    font-size: 30px;
    font-weight: 700;
    padding: 12px;
}
#radioStation {
    color: #ffe7b0;
    font-size: 24px;
    font-weight: 700;
}
#radioMeta {
    color: #c2a77e;
    font-size: 12px;
}
#radioIcy {
    color: #9be8bf;
    font-size: 12px;
}
#radioPreset {
    background: #2a1a10;
    border: 1px solid #6b4a2e;
    border-radius: 6px;
    color: #e8cfa3;
    padding: 7px 12px;
    text-align: left;
}
#radioPreset:hover { background: #422818; }
#radioPowerOn {
    background: #1b5b3a;
    border: 1px solid #59c98b;
    border-radius: 9px;
    color: #b9ffd8;
    font-weight: 700;
}
#radioPowerOff {
    background: #3a1d18;
    border: 1px solid #8a4d3b;
    border-radius: 9px;
    color: #f0b7a2;
    font-weight: 700;
}
"""


class RadioWindow(QWidget):
    play_requested = pyqtSignal(object)
    stop_requested = pyqtSignal()
    volume_changed = pyqtSignal(int)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("浅语影音 · 经典电台")
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setStyleSheet(RADIO_STYLE)
        self.resize(560, 620)
        self._presets: list[RadioStation] = []

        shell = QFrame()
        shell.setObjectName("radioShell")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(shell)
        layout = QVBoxLayout(shell)
        layout.setContentsMargins(30, 22, 30, 24)
        layout.setSpacing(10)

        header = QHBoxLayout()
        brand = QLabel("QIANYU")
        brand.setObjectName("radioBrand")
        model = QLabel("MODEL FM-09 · INTERNET RECEIVER")
        model.setObjectName("radioModel")
        header.addWidget(brand)
        header.addStretch(1)
        header.addWidget(model)
        layout.addLayout(header)

        display = QFrame()
        display.setObjectName("radioDisplay")
        display_layout = QVBoxLayout(display)
        display_layout.setContentsMargins(14, 8, 14, 10)
        self._frequency = QLabel("--.- MHz")
        self._frequency.setObjectName("radioDisplay")
        self._frequency.setAlignment(Qt.AlignCenter)
        self._frequency.setStyleSheet("border: none; background: transparent; padding: 0;")
        self._status = QLabel("STANDBY")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet(
            "color:#5fae86; font-family:Consolas,monospace; font-size:11px; letter-spacing:2px;"
        )
        display_layout.addWidget(self._frequency)
        display_layout.addWidget(self._status)
        layout.addWidget(display)

        self._station = QLabel("未选择电台")
        self._station.setObjectName("radioStation")
        self._station.setAlignment(Qt.AlignCenter)
        self._meta = QLabel("搜索并播放一个公开网络电台")
        self._meta.setObjectName("radioMeta")
        self._meta.setAlignment(Qt.AlignCenter)
        self._icy = QLabel("")
        self._icy.setObjectName("radioIcy")
        self._icy.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._station)
        layout.addWidget(self._meta)
        layout.addWidget(self._icy)

        tuning_row = QHBoxLayout()
        self._dial = QDial()
        self._dial.setRange(0, 100)
        self._dial.setValue(42)
        self._dial.setNotchesVisible(True)
        self._dial.setFixedSize(118, 118)
        self._dial.setToolTip("装饰性调谐旋钮")
        self._dial.valueChanged.connect(self._dial_moved)
        scale = QLabel("AM\n88   92   96   100   104   108\nFM")
        scale.setObjectName("radioMeta")
        scale.setAlignment(Qt.AlignCenter)
        tuning_row.addStretch(1)
        tuning_row.addWidget(self._dial)
        tuning_row.addWidget(scale)
        tuning_row.addStretch(1)
        layout.addLayout(tuning_row)

        self._preset_box = QVBoxLayout()
        self._preset_box.setSpacing(5)
        layout.addLayout(self._preset_box)
        layout.addStretch(1)

        controls = QHBoxLayout()
        self._power = QPushButton("POWER")
        self._power.setObjectName("radioPowerOff")
        self._power.clicked.connect(self._toggle_power)
        self._volume = QSlider(Qt.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(70)
        self._volume.valueChanged.connect(self.volume_changed)
        close = QPushButton("返回音乐库")
        close.clicked.connect(self.close)
        controls.addWidget(self._power)
        controls.addWidget(QLabel("VOL"))
        controls.addWidget(self._volume, 1)
        controls.addWidget(close)
        layout.addLayout(controls)

    @staticmethod
    def frequency_for(station: RadioStation) -> str:
        match = re.search(r"(\d{2,3}\.\d)", station.name)
        if match:
            return f"{match.group(1)} MHz"
        value = 87.5 + (abs(hash(station.name)) % 200) / 10.0
        return f"{value:.1f} MHz"

    def set_station(self, station: RadioStation, icy_title: str = "") -> None:
        self._station.setText(station.name)
        self._meta.setText(" · ".join(part for part in (station.country, station.tags) if part)
                           or "PUBLIC INTERNET RADIO")
        self._frequency.setText(self.frequency_for(station))
        self._status.setText("ON AIR")
        self._power.setObjectName("radioPowerOn")
        self._power.style().unpolish(self._power)
        self._power.style().polish(self._power)
        self._icy.setText(icy_title)

    def set_icy_title(self, title: str) -> None:
        self._icy.setText(title or "")

    def set_presets(self, stations: list[RadioStation]) -> None:
        self._presets = list(stations)[:6]
        while self._preset_box.count():
            item = self._preset_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for index, station in enumerate(self._presets, 1):
            button = QPushButton(f"{index:02d}  {station.name}")
            button.setObjectName("radioPreset")
            button.clicked.connect(lambda _checked=False, value=station: self.play_requested.emit(value))
            self._preset_box.addWidget(button)

    def set_volume(self, value: int) -> None:
        self._volume.setValue(int(value))

    def set_stopped(self) -> None:
        self._status.setText("STANDBY")
        self._power.setObjectName("radioPowerOff")
        self._power.style().unpolish(self._power)
        self._power.style().polish(self._power)

    def _dial_moved(self, value: int) -> None:
        frequency = 87.5 + value / 2.0
        self._frequency.setText(f"{frequency:.1f} MHz")
        self._status.setText("TUNING")

    def _toggle_power(self) -> None:
        if self._status.text() == "STANDBY":
            if self._presets:
                self.play_requested.emit(self._presets[0])
        else:
            self.stop_requested.emit()
            self.set_stopped()

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)
