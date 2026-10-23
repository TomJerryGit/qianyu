# -*- coding: utf-8 -*-
"""Internet radio browser dialog."""
from __future__ import annotations

from ..qt import (
    QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QThread,
    QVBoxLayout, QAbstractItemView, Qt, pyqtSignal,
)
from ..core.radio import RadioStation, search_stations


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("网络电台")
        self.resize(820, 560)
        self._thread: RadioSearchThread | None = None
        self._stations: list[RadioStation] = []

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

        self._status = QLabel("输入名称后搜索；双击电台开始播放。")
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
        play = QPushButton("播放")
        play.clicked.connect(self._play_selected)
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
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
        self._table.setRowCount(len(self._stations))
        for row, station in enumerate(self._stations):
            self._table.setItem(row, 0, QTableWidgetItem(station.name))
            self._table.setItem(row, 1, QTableWidgetItem(station.country))
            self._table.setItem(row, 2, QTableWidgetItem(station.tags))
            quality = f"{station.bitrate} kbps" if station.bitrate else station.codec
            self._table.setItem(row, 3, QTableWidgetItem(quality))
            self._table.item(row, 0).setData(Qt.UserRole, station)
        self._status.setText(f"找到 {len(self._stations)} 个电台。" if self._stations else "没有找到电台。")

    def _show_error(self, message: str) -> None:
        self._status.setText("搜索失败。")
        QMessageBox.warning(self, "网络电台", message)

    def _play_selected(self) -> None:
        row = self._table.currentRow()
        if not (0 <= row < len(self._stations)):
            self._status.setText("请先选择一个电台。")
            return
        self.play_requested.emit(self._stations[row])

    def closeEvent(self, event) -> None:
        if self._thread is not None and self._thread.isRunning():
            self._thread.requestInterruption()
            self._thread.wait(9000)
        super().closeEvent(event)
