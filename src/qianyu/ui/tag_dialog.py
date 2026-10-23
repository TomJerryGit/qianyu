# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Single-track tag editor."""
from __future__ import annotations

from ..qt import (
    QApplication, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout, Qt,
)
from ..core.models import Track


class TagEditDialog(QDialog):
    def __init__(self, track: Track, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑标签")
        self.resize(460, 280)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._title = QLineEdit(track.title)
        self._artist = QLineEdit(track.artist)
        self._album = QLineEdit(track.album)
        self._track_no = QSpinBox()
        self._track_no.setRange(0, 9999)
        self._track_no.setValue(int(track.track_no or 0))
        self._disc_no = QSpinBox()
        self._disc_no.setRange(0, 99)
        self._disc_no.setValue(int(track.disc_no or 0))
        form.addRow("标题", self._title)
        form.addRow("艺术家", self._artist)
        form.addRow("专辑", self._album)
        form.addRow("音轨号", self._track_no)
        form.addRow("碟号", self._disc_no)
        layout.addLayout(form)
        lookup_row = QVBoxLayout()
        self._lookup_btn = QPushButton("在线补全（MusicBrainz）")
        self._lookup_btn.clicked.connect(self._online_lookup)
        self._lookup_status = QLabel("")
        self._lookup_status.setObjectName("stats")
        lookup_row.addWidget(self._lookup_btn)
        lookup_row.addWidget(self._lookup_status)
        layout.addLayout(lookup_row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "title": self._title.text().strip(),
            "artist": self._artist.text().strip(),
            "album": self._album.text().strip(),
            "track_no": int(self._track_no.value()),
            "disc_no": int(self._disc_no.value()),
        }

    def _online_lookup(self) -> None:
        from ..core.metadata import lookup_recording

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._lookup_status.setText("查询 MusicBrainz…")
        try:
            match = lookup_recording(self._title.text(), self._artist.text())
        finally:
            QApplication.restoreOverrideCursor()
        if match is None:
            self._lookup_status.setText("未找到匹配，或网络不可用")
            return
        if match.title:
            self._title.setText(match.title)
        if match.artist:
            self._artist.setText(match.artist)
        if match.album:
            self._album.setText(match.album)
        year = f" · {match.year}" if match.year else ""
        self._lookup_status.setText(f"已补全（匹配度 {match.score}{year}）")
