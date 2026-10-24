# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""First-run radio interests onboarding."""
from __future__ import annotations

from ..qt import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

INTERESTS = (
    ("jazz", "爵士"),
    ("classical", "古典"),
    ("electronic", "电子"),
    ("ambient", "氛围"),
    ("news", "新闻"),
    ("indie", "独立"),
    ("rock", "摇滚"),
)


class RadioInterestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择你感兴趣的电台")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        title = QLabel("第一次使用？选择兴趣，自动生成精选电台收藏。")
        title.setWordWrap(True)
        layout.addWidget(title)
        grid = QVBoxLayout()
        self._boxes: dict[str, QCheckBox] = {}
        for tag, label in INTERESTS:
            box = QCheckBox(label)
            box.setChecked(tag in ("jazz", "classical", "electronic"))
            self._boxes[tag] = box
            grid.addWidget(box)
        layout.addLayout(grid)
        note = QLabel("之后可在 在线 → 网络电台… → 精选电台 继续添加。")
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QHBoxLayout()
        skip = QPushButton("以后再说")
        skip.clicked.connect(self.reject)
        save = QPushButton("保存并生成收藏")
        save.setDefault(True)
        save.clicked.connect(self.accept)
        buttons.addStretch(1)
        buttons.addWidget(skip)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def selected_tags(self) -> list[str]:
        return [tag for tag, box in self._boxes.items() if box.isChecked()]
