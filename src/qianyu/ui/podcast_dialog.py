# -*- coding: utf-8 -*-
"""Podcast browser: search by name, load RSS episodes, play an episode."""
from __future__ import annotations

from ..qt import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QThread, QVBoxLayout, Qt, pyqtSignal,
)
from ..core.podcast import Episode, Podcast, fetch_episodes, search_podcasts


class PodcastSearchThread(QThread):
    podcasts = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, term: str, parent=None):
        super().__init__(parent)
        self._term = term

    def run(self) -> None:
        try:
            self.podcasts.emit(search_podcasts(self._term))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class EpisodeLoadThread(QThread):
    episodes = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, feed_url: str, parent=None):
        super().__init__(parent)
        self._feed_url = feed_url

    def run(self) -> None:
        try:
            self.episodes.emit(fetch_episodes(self._feed_url))
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class PodcastDialog(QDialog):
    play_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("播客")
        self.resize(900, 620)
        self._search_thread: PodcastSearchThread | None = None
        self._episode_thread: EpisodeLoadThread | None = None
        self._podcasts: list[Podcast] = []
        self._episodes: list[Episode] = []

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索播客，例如 科技、历史、BBC")
        self._search.returnPressed.connect(self._start_search)
        self._button = QPushButton("搜索")
        self._button.clicked.connect(self._start_search)
        top.addWidget(self._search, 1)
        top.addWidget(self._button)
        layout.addLayout(top)

        self._status = QLabel("搜索播客；选择后加载单集。")
        self._status.setObjectName("stats")
        layout.addWidget(self._status)

        splitter = QSplitter(Qt.Vertical)
        self._podcast_table = QTableWidget(0, 2)
        self._podcast_table.setHorizontalHeaderLabels(["播客", "作者"])
        self._podcast_table.verticalHeader().setVisible(False)
        self._podcast_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._podcast_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._podcast_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._podcast_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._podcast_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._podcast_table.itemSelectionChanged.connect(self._load_selected)
        splitter.addWidget(self._podcast_table)

        self._episode_table = QTableWidget(0, 3)
        self._episode_table.setHorizontalHeaderLabels(["单集", "日期", "时长"])
        self._episode_table.verticalHeader().setVisible(False)
        self._episode_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._episode_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._episode_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._episode_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._episode_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._episode_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._episode_table.doubleClicked.connect(lambda _index: self._play_selected())
        splitter.addWidget(self._episode_table)
        layout.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        self._detail = QLabel("")
        self._detail.setWordWrap(True)
        play = QPushButton("播放单集")
        play.clicked.connect(self._play_selected)
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        bottom.addWidget(self._detail, 1)
        bottom.addWidget(play)
        bottom.addWidget(close)
        layout.addLayout(bottom)

    def _start_search(self) -> None:
        term = self._search.text().strip()
        if not term:
            self._status.setText("请输入播客名称。")
            return
        if self._search_thread is not None and self._search_thread.isRunning():
            return
        self._status.setText(f"正在搜索：{term} …")
        self._button.setEnabled(False)
        self._search_thread = PodcastSearchThread(term, self)
        self._search_thread.podcasts.connect(self._show_podcasts)
        self._search_thread.failed.connect(self._show_error)
        self._search_thread.finished.connect(lambda: self._button.setEnabled(True))
        self._search_thread.start()

    def _show_podcasts(self, podcasts: list) -> None:
        self._podcasts = list(podcasts)
        self._podcast_table.setRowCount(len(self._podcasts))
        for row, podcast in enumerate(self._podcasts):
            self._podcast_table.setItem(row, 0, QTableWidgetItem(podcast.name))
            self._podcast_table.setItem(row, 1, QTableWidgetItem(podcast.artist))
            self._podcast_table.item(row, 0).setData(Qt.UserRole, podcast)
        self._status.setText(f"找到 {len(self._podcasts)} 个播客。" if self._podcasts else "没有找到播客。")
        if self._podcasts:
            self._podcast_table.selectRow(0)

    def _load_selected(self) -> None:
        row = self._podcast_table.currentRow()
        if not (0 <= row < len(self._podcasts)):
            return
        if self._episode_thread is not None and self._episode_thread.isRunning():
            return
        podcast = self._podcasts[row]
        self._status.setText(f"正在加载单集：{podcast.name} …")
        self._detail.setText(podcast.description[:300])
        self._episode_table.setRowCount(0)
        self._episode_thread = EpisodeLoadThread(podcast.feed_url, self)
        self._episode_thread.episodes.connect(self._show_episodes)
        self._episode_thread.failed.connect(self._show_error)
        self._episode_thread.start()

    def _show_episodes(self, episodes: list) -> None:
        self._episodes = list(episodes)
        self._episode_table.setRowCount(len(self._episodes))
        for row, episode in enumerate(self._episodes):
            self._episode_table.setItem(row, 0, QTableWidgetItem(episode.title))
            self._episode_table.setItem(row, 1, QTableWidgetItem(episode.published))
            minutes, seconds = divmod(int(episode.duration or 0), 60)
            duration = f"{minutes}:{seconds:02d}" if episode.duration else ""
            self._episode_table.setItem(row, 2, QTableWidgetItem(duration))
            self._episode_table.item(row, 0).setData(Qt.UserRole, episode)
        self._status.setText(f"{len(self._episodes)} 个单集。")
        if self._episodes:
            self._episode_table.selectRow(0)

    def _show_error(self, message: str) -> None:
        self._status.setText("操作失败。")
        QMessageBox.warning(self, "播客", message)

    def _play_selected(self) -> None:
        row = self._episode_table.currentRow()
        if not (0 <= row < len(self._episodes)):
            self._status.setText("请先选择一个单集。")
            return
        self.play_requested.emit(self._episodes[row])

    def closeEvent(self, event) -> None:
        for thread in (self._search_thread, self._episode_thread):
            if thread is not None and thread.isRunning():
                thread.requestInterruption()
                thread.wait(9000)
        super().closeEvent(event)
