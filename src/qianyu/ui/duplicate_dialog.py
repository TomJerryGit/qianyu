# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Duplicate track review dialog (removes library rows, never deletes files)."""
from __future__ import annotations

from ..qt import (
    QDialog, QDialogButtonBox, QLabel, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, Qt,
)


class DuplicateDialog(QDialog):
    def __init__(self, groups, parent=None):
        super().__init__(parent)
        self.setWindowTitle("查找重复曲目")
        self.resize(820, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("勾选要从媒体库移除的重复项（不会删除磁盘文件）。"))
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["曲目", "路径"])
        self._tree.setColumnWidth(0, 280)
        for index, group in enumerate(groups, 1):
            root = QTreeWidgetItem([f"重复组 {index}", ""])
            self._tree.addTopLevelItem(root)
            for pos, track in enumerate(group):
                child = QTreeWidgetItem([track.display, track.path])
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked if pos == 0 else Qt.Checked)
                root.addChild(child)
            root.setExpanded(True)
        layout.addWidget(self._tree, 1)
        buttons = QDialogButtonBox()
        remove = QPushButton("从媒体库移除选中")
        remove.clicked.connect(self.accept)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        buttons.addButton(remove, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel, QDialogButtonBox.RejectRole)
        layout.addWidget(buttons)

    def selected_paths(self) -> list[str]:
        paths = []
        for i in range(self._tree.topLevelItemCount()):
            root = self._tree.topLevelItem(i)
            for j in range(root.childCount()):
                child = root.child(j)
                if child.checkState(0) == Qt.Checked:
                    paths.append(child.text(1))
        return paths
