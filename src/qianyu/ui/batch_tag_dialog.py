# -*- coding: utf-8 -*-
"""Batch tag editor for selected tracks."""
from __future__ import annotations

from ..qt import (
    QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit,
    QVBoxLayout,
)


class BatchTagDialog(QDialog):
    def __init__(self, count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("批量编辑标签")
        self.resize(480, 240)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"将修改 {count} 首曲目；未勾选的字段保持不变。"))
        form = QFormLayout()
        self._artist_check = QCheckBox("修改艺术家")
        self._artist = QLineEdit()
        self._album_check = QCheckBox("修改专辑")
        self._album = QLineEdit()
        form.addRow(self._artist_check, self._artist)
        form.addRow(self._album_check, self._album)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict[str, str]:
        values = {}
        if self._artist_check.isChecked():
            values["artist"] = self._artist.text().strip()
        if self._album_check.isChecked():
            values["album"] = self._album.text().strip()
        return values
