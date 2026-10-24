# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Remote library browser for Subsonic-compatible servers."""
from __future__ import annotations

from ..qt import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QThread,
    QVBoxLayout, Qt, pyqtSignal,
)
from ..core.subsonic import RemoteSong, SubsonicClient, SubsonicError
from ..core.secure_store import SecretStore


def make_client(config) -> SubsonicClient:
    secret = SecretStore(config)
    return SubsonicClient(
        str(config.get("subsonic_url", "")),
        str(config.get("subsonic_user", "")),
        secret.get("subsonic_password"),
    )


class RemoteSearchThread(QThread):
    songs = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, client: SubsonicClient, query: str, parent=None):
        super().__init__(parent)
        self._client = client
        self._query = query

    def run(self) -> None:
        try:
            self.songs.emit(self._client.search_songs(self._query))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class RemoteTestThread(QThread):
    ok = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, client: SubsonicClient, parent=None):
        super().__init__(parent)
        self._client = client

    def run(self) -> None:
        try:
            self._client.ping()
            self.ok.emit()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class RemoteDialog(QDialog):
    play_requested = pyqtSignal(object)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("远程媒体库（Navidrome / Subsonic）")
        self.resize(880, 560)
        self._config = config
        self._client = make_client(config)
        self._thread: RemoteSearchThread | None = None
        self._test_thread: RemoteTestThread | None = None
        self._songs: list[RemoteSong] = []

        layout = QVBoxLayout(self)
        self._status = QLabel("")
        self._status.setObjectName("stats")
        layout.addWidget(self._status)
        top = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索远程曲库，例如 Artist、Album、Song")
        self._search.returnPressed.connect(self._start_search)
        self._button = QPushButton("搜索")
        self._button.clicked.connect(self._start_search)
        test = QPushButton("测试连接")
        test.clicked.connect(self._test_connection)
        top.addWidget(self._search, 1)
        top.addWidget(test)
        top.addWidget(self._button)
        layout.addLayout(top)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["歌曲", "艺术家", "专辑", "时长"])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.doubleClicked.connect(lambda _index: self._play_selected())
        layout.addWidget(self._table, 1)

        bottom = QHBoxLayout()
        self._detail = QLabel("")
        self._detail.setWordWrap(True)
        play = QPushButton("播放")
        play.clicked.connect(self._play_selected)
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        bottom.addWidget(self._detail, 1)
        bottom.addWidget(play)
        bottom.addWidget(close)
        layout.addLayout(bottom)
        self._update_configured()

    def _update_configured(self) -> None:
        if self._client.configured:
            self._status.setText("远程媒体库已配置；输入关键词搜索。")
        else:
            self._status.setText("请先在 设置 → 远程媒体库 填写服务器地址、用户名和密码。")

    def _test_connection(self) -> None:
        if not self._client.configured:
            QMessageBox.information(
                self, "远程媒体库",
                "请先在 设置 → 远程媒体库 填写服务器地址、用户名和密码。",
            )
            return
        if self._test_thread is not None and self._test_thread.isRunning():
            return
        self._status.setText("正在测试连接…")
        self._test_thread = RemoteTestThread(self._client, self)
        self._test_thread.ok.connect(lambda: self._status.setText("连接成功：Subsonic ping OK"))
        self._test_thread.failed.connect(lambda message: self._status.setText(f"连接失败：{message}"))
        self._test_thread.start()

    def _start_search(self) -> None:
        if not self._client.configured:
            QMessageBox.information(
                self, "远程媒体库",
                "请先在 设置 → 远程媒体库 填写服务器地址、用户名和密码。",
            )
            return
        query = self._search.text().strip()
        if not query:
            self._status.setText("请输入搜索关键词。")
            return
        if self._thread is not None and self._thread.isRunning():
            return
        self._status.setText(f"正在搜索：{query} …")
        self._button.setEnabled(False)
        self._thread = RemoteSearchThread(self._client, query, self)
        self._thread.songs.connect(self._show_songs)
        self._thread.failed.connect(self._show_error)
        self._thread.finished.connect(lambda: self._button.setEnabled(True))
        self._thread.start()

    def _show_songs(self, songs: list) -> None:
        self._songs = list(songs)
        self._table.setRowCount(len(self._songs))
        for row, song in enumerate(self._songs):
            self._table.setItem(row, 0, QTableWidgetItem(song.title))
            self._table.setItem(row, 1, QTableWidgetItem(song.artist))
            self._table.setItem(row, 2, QTableWidgetItem(song.album))
            minutes, seconds = divmod(int(song.duration or 0), 60)
            self._table.setItem(row, 3, QTableWidgetItem(
                f"{minutes}:{seconds:02d}" if song.duration else ""
            ))
            self._table.item(row, 0).setData(Qt.UserRole, song)
        self._status.setText(f"找到 {len(self._songs)} 首歌曲。" if self._songs else "没有找到歌曲。")
        if self._songs:
            self._table.selectRow(0)

    def _show_error(self, message: str) -> None:
        self._status.setText("远程搜索失败。")
        QMessageBox.warning(self, "远程媒体库", message)

    def _play_selected(self) -> None:
        row = self._table.currentRow()
        if not (0 <= row < len(self._songs)):
            self._status.setText("请先选择一首歌曲。")
            return
        self.play_requested.emit(self._songs[row])

    def closeEvent(self, event) -> None:
        for thread in (self._thread, self._test_thread):
            if thread is not None and thread.isRunning():
                thread.requestInterruption()
                thread.wait(9000)
        super().closeEvent(event)
