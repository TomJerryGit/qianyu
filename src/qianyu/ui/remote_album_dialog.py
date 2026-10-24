# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Remote album browser for Subsonic and Jellyfin."""
from __future__ import annotations

from ..qt import (
    QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QThread, QVBoxLayout, Qt, pyqtSignal,
)
from ..core.jellyfin import JellyfinClient, JellyfinError
from ..core.secure_store import SecretStore
from ..core.subsonic import RemoteAlbum, RemoteSong
from .remote_dialog import make_client


class AlbumLoadThread(QThread):
    albums = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, provider: str, config, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._config = config

    def run(self) -> None:
        try:
            if self._provider == "jellyfin":
                client = JellyfinClient(
                    str(self._config.get("jellyfin_url", "")),
                    str(self._config.get("jellyfin_user", "")),
                    SecretStore(self._config).get("jellyfin_password"),
                    SecretStore(self._config).get("jellyfin_token"),
                    str(self._config.get("jellyfin_user_id", "")),
                )
                if not client.token or not client.user_id:
                    client.login()
                self.albums.emit(client.albums())
            else:
                client = make_client(self._config)
                self.albums.emit(client.albums())
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class AlbumSongsThread(QThread):
    songs = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, provider: str, config, album_id: str, parent=None):
        super().__init__(parent)
        self._provider = provider
        self._config = config
        self._album_id = album_id

    def run(self) -> None:
        try:
            if self._provider == "jellyfin":
                client = JellyfinClient(
                    str(self._config.get("jellyfin_url", "")),
                    str(self._config.get("jellyfin_user", "")),
                    SecretStore(self._config).get("jellyfin_password"),
                    SecretStore(self._config).get("jellyfin_token"),
                    str(self._config.get("jellyfin_user_id", "")),
                )
                if not client.token or not client.user_id:
                    client.login()
                self.songs.emit(client.album_songs(self._album_id))
            else:
                client = make_client(self._config)
                self.songs.emit(client.album_songs(self._album_id))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class RemoteAlbumDialog(QDialog):
    queue_requested = pyqtSignal(list, int)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("远程专辑")
        self.resize(900, 620)
        self._config = config
        self._albums: list = []
        self._songs: list = []
        self._threads: list[QThread] = []

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self._provider = QComboBox()
        self._provider.addItem("Navidrome / Subsonic", "subsonic")
        self._provider.addItem("Jellyfin", "jellyfin")
        load = QPushButton("加载专辑")
        load.clicked.connect(self._load_albums)
        self._status = QLabel("选择服务器后加载专辑。")
        self._status.setObjectName("stats")
        top.addWidget(self._provider)
        top.addWidget(load)
        top.addWidget(self._status, 1)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Vertical)
        self._album_table = QTableWidget(0, 4)
        self._album_table.setHorizontalHeaderLabels(["专辑", "艺术家", "年份", "曲数"])
        self._album_table.verticalHeader().setVisible(False)
        self._album_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._album_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._album_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._album_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._album_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._album_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._album_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._album_table.itemSelectionChanged.connect(self._load_songs)
        splitter.addWidget(self._album_table)

        self._song_table = QTableWidget(0, 3)
        self._song_table.setHorizontalHeaderLabels(["歌曲", "艺术家", "时长"])
        self._song_table.verticalHeader().setVisible(False)
        self._song_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._song_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._song_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._song_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._song_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._song_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._song_table.doubleClicked.connect(lambda _index: self._play_row())
        splitter.addWidget(self._song_table)
        layout.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        play = QPushButton("播放选中")
        play.clicked.connect(self._play_row)
        queue = QPushButton("播放整张专辑")
        queue.clicked.connect(self._queue_album)
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        bottom.addStretch(1)
        bottom.addWidget(play)
        bottom.addWidget(queue)
        bottom.addWidget(close)
        layout.addLayout(bottom)

    def _load_albums(self) -> None:
        provider = str(self._provider.currentData())
        self._status.setText("正在加载专辑…")
        thread = AlbumLoadThread(provider, self._config, self)
        thread.albums.connect(self._show_albums)
        thread.failed.connect(self._show_error)
        self._threads.append(thread)
        thread.start()

    def _show_albums(self, albums: list) -> None:
        self._albums = list(albums)
        self._album_table.setRowCount(len(self._albums))
        for row, album in enumerate(self._albums):
            self._album_table.setItem(row, 0, QTableWidgetItem(album.name))
            self._album_table.setItem(row, 1, QTableWidgetItem(album.artist))
            self._album_table.setItem(row, 2, QTableWidgetItem(str(album.year or "")))
            self._album_table.setItem(row, 3, QTableWidgetItem(str(album.song_count or "")))
            self._album_table.item(row, 0).setData(Qt.UserRole, album)
        self._status.setText(f"{len(self._albums)} 张专辑。")
        if self._albums:
            self._album_table.selectRow(0)

    def _load_songs(self) -> None:
        row = self._album_table.currentRow()
        if not (0 <= row < len(self._albums)):
            return
        album = self._albums[row]
        thread = AlbumSongsThread(str(self._provider.currentData()), self._config,
                                  album.id, self)
        thread.songs.connect(self._show_songs)
        thread.failed.connect(self._show_error)
        self._threads.append(thread)
        thread.start()

    def _show_songs(self, songs: list) -> None:
        self._songs = list(songs)
        self._song_table.setRowCount(len(self._songs))
        for row, song in enumerate(self._songs):
            self._song_table.setItem(row, 0, QTableWidgetItem(song.title))
            self._song_table.setItem(row, 1, QTableWidgetItem(song.artist))
            minutes, seconds = divmod(int(song.duration or 0), 60)
            self._song_table.setItem(row, 2, QTableWidgetItem(
                f"{minutes}:{seconds:02d}" if song.duration else ""
            ))
        if self._songs:
            self._song_table.selectRow(0)

    def _show_error(self, message: str) -> None:
        self._status.setText("加载失败。")
        QMessageBox.warning(self, "远程专辑", message)

    def _play_row(self) -> None:
        row = self._song_table.currentRow()
        if 0 <= row < len(self._songs):
            self.queue_requested.emit(self._songs, row)

    def _queue_album(self) -> None:
        if self._songs:
            self.queue_requested.emit(self._songs, 0)

    def closeEvent(self, event) -> None:
        for thread in self._threads:
            if thread.isRunning():
                thread.requestInterruption()
                thread.wait(9000)
        super().closeEvent(event)
