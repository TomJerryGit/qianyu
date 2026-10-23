# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""CUE sheet track list dialog."""
from __future__ import annotations

from ..qt import QDialog, QHBoxLayout, QLabel, QListWidget, QPushButton, QVBoxLayout, pyqtSignal


class CueDialog(QDialog):
    play_requested = pyqtSignal(int)

    def __init__(self, sheet, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"CUE：{sheet.title}")
        self.resize(620, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{sheet.audio_path}\n{sheet.title} · {sheet.performer}"))
        self._list = QListWidget()
        for index, track in enumerate(sheet.tracks):
            self._list.addItem(
                f"{index + 1:02d}  {track.title}  —  {track.artist}  "
                f"({int(track.start // 60):02d}:{int(track.start % 60):02d})"
            )
        self._list.itemDoubleClicked.connect(self._play_selected)
        layout.addWidget(self._list, 1)
        buttons = QHBoxLayout()
        play_all = QPushButton("播放全部")
        play_all.clicked.connect(lambda: self._play(0))
        play = QPushButton("播放选中")
        play.clicked.connect(self._play_selected)
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        buttons.addWidget(play_all)
        buttons.addWidget(play)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        self._sheet = sheet

    def _play_selected(self, *_args) -> None:
        row = self._list.currentRow()
        if row >= 0:
            self._play(row)

    def _play(self, index: int) -> None:
        self.play_requested.emit(index)
