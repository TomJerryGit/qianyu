# -*- coding: utf-8 -*-
"""Simple LRC text editor with backup-on-save."""
from __future__ import annotations

from pathlib import Path

from ..qt import (
    QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout,
)


class LyricsEditorDialog(QDialog):
    def __init__(self, path: Path, text: str, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.setWindowTitle(f"编辑歌词 — {self.path.name}")
        self.resize(720, 560)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"保存到：{self.path}"))
        self._edit = QPlainTextEdit()
        self._edit.setPlainText(text)
        layout.addWidget(self._edit, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        save = QPushButton("保存")
        save.setDefault(True)
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                backup = self.path.with_suffix(self.path.suffix + ".bak")
                backup.write_bytes(self.path.read_bytes())
            except OSError:
                pass
        self.path.write_text(self._edit.toPlainText(), encoding="utf-8")
        self.accept()

    def text(self) -> str:
        return self._edit.toPlainText()
