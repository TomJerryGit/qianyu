# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Internet radio browser dialog."""
from __future__ import annotations

import json
from pathlib import Path

from ..qt import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QThread,
    QVBoxLayout, QAbstractItemView, Qt, pyqtSignal,
)
from ..core.radio import RadioStation, search_stations
from ..core.radio_presets import preset_stations


class RadioSearchThread(QThread):
    stations = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, keyword: str, country: str, parent=None):
        super().__init__(parent)
        self._keyword = keyword
        self._country = country

    def run(self) -> None:
        try:
            self.stations.emit(search_stations(self._keyword, self._country))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class RadioDialog(QDialog):
    play_requested = pyqtSignal(object)

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowTitle("网络电台")
        self.resize(820, 560)
        self._thread: RadioSearchThread | None = None
        self._stations: list[RadioStation] = []
        self._config = config

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索电台名称，例如 jazz、classical、news")
        self._search.returnPressed.connect(self._start_search)
        self._country = QComboBox()
        self._country.addItem("全部国家", "")
        for code, label in (("CN", "中国"), ("US", "美国"), ("GB", "英国"),
                            ("JP", "日本"), ("DE", "德国"), ("FR", "法国")):
            self._country.addItem(label, code)
        self._button = QPushButton("搜索")
        self._button.clicked.connect(self._start_search)
        top.addWidget(self._search, 1)
        top.addWidget(self._country)
        top.addWidget(self._button)
        layout.addLayout(top)

        self._status = QLabel("数据来源 Radio Browser；流媒体版权归各电台。输入名称后搜索。")
        self._status.setObjectName("stats")
        layout.addWidget(self._status)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["电台", "国家", "标签", "码率"])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.doubleClicked.connect(lambda _index: self._play_selected())
        layout.addWidget(self._table, 1)

        bottom = QHBoxLayout()
        favorite = QPushButton("收藏/取消收藏")
        favorite.clicked.connect(self._toggle_favorite)
        favorites = QPushButton("我的收藏")
        favorites.clicked.connect(self._show_favorites)
        recent = QPushButton("最近收听")
        recent.clicked.connect(self._show_recent)
        curated = QPushButton("精选电台")
        curated.clicked.connect(self._show_presets)
        export = QPushButton("导出")
        export.clicked.connect(self._export_favorites)
        import_button = QPushButton("导入")
        import_button.clicked.connect(self._import_favorites)
        play = QPushButton("播放")
        play.clicked.connect(self._play_selected)
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        bottom.addWidget(favorite)
        bottom.addWidget(favorites)
        bottom.addWidget(recent)
        bottom.addWidget(curated)
        bottom.addWidget(export)
        bottom.addWidget(import_button)
        bottom.addStretch(1)
        bottom.addWidget(play)
        bottom.addWidget(close)
        layout.addLayout(bottom)

    def _start_search(self) -> None:
        keyword = self._search.text().strip()
        if not keyword:
            self._status.setText("请输入电台名称。")
            return
        if self._thread is not None and self._thread.isRunning():
            return
        self._status.setText(f"正在搜索：{keyword} …")
        self._button.setEnabled(False)
        self._thread = RadioSearchThread(keyword, str(self._country.currentData() or ""), self)
        self._thread.stations.connect(self._show_stations)
        self._thread.failed.connect(self._show_error)
        self._thread.finished.connect(lambda: self._button.setEnabled(True))
        self._thread.start()

    def _show_stations(self, stations: list) -> None:
        self._stations = list(stations)
        self._render_stations()
        self._status.setText(f"找到 {len(self._stations)} 个电台。" if self._stations else "没有找到电台。")

    def _show_presets(self) -> None:
        self._stations = preset_stations()
        self._render_stations()
        self._status.setText(
            f"精选公开电台：{len(self._stations)} 个。版权归各电台，仅供在线收听。"
        )

    def _render_stations(self) -> None:
        self._table.setRowCount(len(self._stations))
        for row, station in enumerate(self._stations):
            self._table.setItem(row, 0, QTableWidgetItem(station.name))
            self._table.setItem(row, 1, QTableWidgetItem(station.country))
            self._table.setItem(row, 2, QTableWidgetItem(station.tags))
            quality = f"{station.bitrate} kbps" if station.bitrate else station.codec
            self._table.setItem(row, 3, QTableWidgetItem(quality))
            self._table.item(row, 0).setData(Qt.UserRole, station)

    def _favorites(self) -> list[RadioStation]:
        if self._config is None:
            return []
        result = []
        for item in self._config.get("radio_favorites", []) or []:
            station = RadioStation.from_dict(item)
            if station is not None:
                result.append(station)
        return result

    def _set_favorites(self, stations: list[RadioStation]) -> None:
        if self._config is None:
            return
        self._config.set("radio_favorites", [station.as_dict() for station in stations])

    def _toggle_favorite(self) -> None:
        row = self._table.currentRow()
        if not (0 <= row < len(self._stations)):
            self._status.setText("请先选择一个电台。")
            return
        station = self._stations[row]
        favorites = self._favorites()
        if any(item.url == station.url for item in favorites):
            favorites = [item for item in favorites if item.url != station.url]
            self._status.setText(f"已取消收藏：{station.name}")
        else:
            favorites.append(station)
            self._status.setText(f"已收藏：{station.name}")
        self._set_favorites(favorites)

    def _show_favorites(self) -> None:
        self._stations = self._favorites()
        self._render_stations()
        self._status.setText(f"我的收藏：{len(self._stations)} 个电台。" if self._stations else "还没有收藏电台。")

    def _recents(self) -> list[RadioStation]:
        if self._config is None:
            return []
        result = []
        for item in self._config.get("radio_recent", []) or []:
            station = RadioStation.from_dict(item)
            if station is not None:
                result.append(station)
        return result

    def _record_recent(self, station: RadioStation) -> None:
        if self._config is None:
            return
        recent = [item for item in self._recents() if item.url != station.url]
        recent.insert(0, station)
        self._config.set("radio_recent", [item.as_dict() for item in recent[:20]])

    def _show_recent(self) -> None:
        self._stations = self._recents()
        self._render_stations()
        self._status.setText(f"最近收听：{len(self._stations)} 个电台。" if self._stations else "还没有收听记录。")

    def _export_favorites(self) -> None:
        path, _selected = QFileDialog.getSaveFileName(
            self, "导出电台收藏", "qianyu-radio-favorites.json", "JSON (*.json)"
        )
        if not path:
            return
        try:
            Path(path).write_text(
                json.dumps([item.as_dict() for item in self._favorites()],
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._status.setText(f"已导出收藏：{path}")
        except OSError as exc:
            QMessageBox.warning(self, "导出收藏", str(exc))

    def _import_favorites(self) -> None:
        path, _selected = QFileDialog.getOpenFileName(
            self, "导入电台收藏", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "导入收藏", str(exc))
            return
        if not isinstance(raw, list):
            QMessageBox.warning(self, "导入收藏", "文件格式不是电台收藏列表。")
            return
        existing = self._favorites()
        seen = {item.url for item in existing}
        for item in raw:
            station = RadioStation.from_dict(item)
            if station is not None and station.url not in seen:
                existing.append(station)
                seen.add(station.url)
        self._set_favorites(existing)
        self._status.setText(f"已导入收藏，共 {len(existing)} 个电台。")

    def _show_error(self, message: str) -> None:
        self._status.setText("搜索失败。")
        QMessageBox.warning(self, "网络电台", message)

    def _play_selected(self) -> None:
        row = self._table.currentRow()
        if not (0 <= row < len(self._stations)):
            self._status.setText("请先选择一个电台。")
            return
        station = self._stations[row]
        self._record_recent(station)
        self.play_requested.emit(station)

    def closeEvent(self, event) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.wait(9000)
        super().closeEvent(event)
