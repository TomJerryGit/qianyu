# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Unified local + Subsonic + Jellyfin search."""
from __future__ import annotations

from ..qt import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QThread,
    QVBoxLayout, Qt, pyqtSignal,
)
from ..core.jellyfin import JellyfinClient, JellyfinError
from ..core.models import Track
from ..core.secure_store import SecretStore
from ..core.subsonic import RemoteSong
from .remote_dialog import make_client


class SubsonicThread(QThread):
    songs = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, client, query: str, parent=None):
        super().__init__(parent)
        self._client = client
        self._query = query

    def run(self) -> None:
        try:
            self.songs.emit(self._client.search_songs(self._query))
        except Exception as exc:
            self.failed.emit(f"Subsonic: {type(exc).__name__}: {exc}")


class JellyfinThread(QThread):
    songs = pyqtSignal(list)
    failed = pyqtSignal(str)
    token_ready = pyqtSignal(str, str)

    def __init__(self, client: JellyfinClient, query: str, parent=None):
        super().__init__(parent)
        self._client = client
        self._query = query

    def run(self) -> None:
        try:
            if not self._client.token or not self._client.user_id:
                self._client.login()
                self.token_ready.emit(self._client.token, self._client.user_id)
            try:
                songs = self._client.search_songs(self._query)
            except JellyfinError:
                self._client.login()
                self.token_ready.emit(self._client.token, self._client.user_id)
                songs = self._client.search_songs(self._query)
            self.songs.emit(songs)
        except Exception as exc:
            self.failed.emit(f"Jellyfin: {type(exc).__name__}: {exc}")


class UnifiedSearchDialog(QDialog):
    play_requested = pyqtSignal(object)

    def __init__(self, library, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("统一搜索：本地 + 远程")
        self.resize(960, 600)
        self._library = library
        self._config = config
        self._threads: list[QThread] = []
        self._results: dict[int, object] = {}

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索本地媒体库、Navidrome/Subsonic、Jellyfin")
        self._search.returnPressed.connect(self._start_search)
        button = QPushButton("搜索")
        button.clicked.connect(self._start_search)
        top.addWidget(self._search, 1)
        top.addWidget(button)
        layout.addLayout(top)

        self._status = QLabel("输入关键词；结果按来源标记，双击播放。")
        self._status.setObjectName("stats")
        layout.addWidget(self._status)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["来源", "歌曲", "艺术家", "专辑", "时长"])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
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

    def _start_search(self) -> None:
        query = self._search.text().strip()
        if not query:
            self._status.setText("请输入搜索关键词。")
            return
        self._table.setRowCount(0)
        self._results.clear()
        local = self._library.search(query)
        for track in local[:100]:
            self._add_row("本地", track.title, track.artist, track.album, track.duration, track)
        total = len(local)
        self._status.setText(f"本地 {len(local)} 首；正在查询远程…")

        subsonic = make_client(self._config)
        if subsonic.configured:
            thread = SubsonicThread(subsonic, query, self)
            thread.songs.connect(lambda songs: self._add_remote("Subsonic", songs, total))
            thread.failed.connect(self._show_error)
            self._threads.append(thread)
            thread.start()

        jellyfin = self._jellyfin_client()
        if jellyfin.configured:
            thread = JellyfinThread(jellyfin, query, self)
            thread.songs.connect(lambda songs: self._add_remote("Jellyfin", songs, total))
            thread.failed.connect(self._show_error)
            thread.token_ready.connect(self._save_jellyfin_token)
            self._threads.append(thread)
            thread.start()

    def _jellyfin_client(self) -> JellyfinClient:
        return JellyfinClient(
            str(self._config.get("jellyfin_url", "")),
            str(self._config.get("jellyfin_user", "")),
            SecretStore(self._config).get("jellyfin_password"),
            SecretStore(self._config).get("jellyfin_token"),
            str(self._config.get("jellyfin_user_id", "")),
        )

    def _save_jellyfin_token(self, token: str, user_id: str) -> None:
        from ..core.secure_store import SecretStore
        SecretStore(self._config).set("jellyfin_token", token)
        self._config.set("jellyfin_user_id", user_id)

    def _add_remote(self, source: str, songs: list, local_count: int) -> None:
        for song in songs:
            self._add_row(source, song.title, song.artist, song.album,
                          song.duration, song)
        self._status.setText(f"本地 {local_count} 首；{source} {len(songs)} 首。")

    def _add_row(self, source: str, title: str, artist: str, album: str,
                 duration: float, obj) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(source))
        self._table.setItem(row, 1, QTableWidgetItem(title))
        self._table.setItem(row, 2, QTableWidgetItem(artist))
        self._table.setItem(row, 3, QTableWidgetItem(album))
        minutes, seconds = divmod(int(duration or 0), 60)
        self._table.setItem(row, 4, QTableWidgetItem(
            f"{minutes}:{seconds:02d}" if duration else ""
        ))
        self._table.item(row, 0).setData(Qt.UserRole, obj)
        self._results[row] = obj

    def _show_error(self, message: str) -> None:
        self._status.setText(message)

    def _play_selected(self) -> None:
        row = self._table.currentRow()
        if row not in self._results:
            self._status.setText("请先选择一条结果。")
            return
        self.play_requested.emit(self._results[row])

    def closeEvent(self, event) -> None:
        for thread in self._threads:
            if thread.isRunning():
                thread.requestInterruption()
                thread.wait(9000)
        super().closeEvent(event)
