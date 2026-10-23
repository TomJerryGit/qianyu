# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Podcast browser: search by name, load RSS episodes, play an episode."""
from __future__ import annotations

from collections import deque

from ..qt import (
    QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem,
    QThread, QVBoxLayout, Qt, pyqtSignal,
)
from ..core.podcast import Episode, Podcast, fetch_episodes, search_podcasts
from ..core.podcast_cache import PodcastCache


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


class EpisodeDownloadThread(QThread):
    progress = pyqtSignal(str, int, int)
    downloaded = pyqtSignal(str, str)
    failed = pyqtSignal(str, str)

    def __init__(self, cache: PodcastCache, episode: Episode, parent=None):
        super().__init__(parent)
        self._cache = cache
        self._episode = episode

    def run(self) -> None:
        try:
            path = self._cache.download(
                self._episode.url,
                title=self._episode.title,
                progress=lambda done, total: self.progress.emit(self._episode.url, done, total),
                cancelled=self.isInterruptionRequested,
            )
            self.downloaded.emit(self._episode.url, str(path))
        except Exception as exc:
            self.failed.emit(self._episode.url, f"{type(exc).__name__}: {exc}")


class PodcastDialog(QDialog):
    play_requested = pyqtSignal(object)

    def __init__(self, parent=None, config=None, cache: PodcastCache | None = None):
        super().__init__(parent)
        self.setWindowTitle("播客")
        self.resize(900, 620)
        self._search_thread: PodcastSearchThread | None = None
        self._episode_thread: EpisodeLoadThread | None = None
        self._download_thread: EpisodeDownloadThread | None = None
        self._download_queue: deque[Episode] = deque()
        self._podcasts: list[Podcast] = []
        self._episodes: list[Episode] = []
        self._config = config
        self._cache = cache

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

        self._status = QLabel("播客数据由 iTunes Search 提供（Powered by iTunes）；内容版权归原作者。")
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
        subscribe = QPushButton("订阅/取消订阅")
        subscribe.clicked.connect(self._toggle_subscription)
        subscribed = QPushButton("我的订阅")
        subscribed.clicked.connect(self._show_subscriptions)
        download = QPushButton("下载单集")
        download.clicked.connect(self._download_selected)
        remove = QPushButton("删除下载")
        remove.clicked.connect(self._delete_selected)
        play = QPushButton("播放单集")
        play.clicked.connect(self._play_selected)
        close = QPushButton("关闭")
        close.clicked.connect(self.reject)
        bottom.addWidget(subscribe)
        bottom.addWidget(subscribed)
        bottom.addWidget(download)
        bottom.addWidget(remove)
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
        subscribed = {item.feed_url for item in self._subscriptions()}
        self._podcast_table.setRowCount(len(self._podcasts))
        for row, podcast in enumerate(self._podcasts):
            prefix = "★ " if podcast.feed_url in subscribed else ""
            self._podcast_table.setItem(row, 0, QTableWidgetItem(prefix + podcast.name))
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
        self._refresh_episode_marks()
        self._status.setText(f"{len(self._episodes)} 个单集。")
        if self._episodes:
            self._episode_table.selectRow(0)

    def _episode_prefix(self, episode: Episode) -> str:
        prefix = ""
        if episode.url in set(self._played()):
            prefix += "✓ "
        if self._cache is not None and self._cache.is_downloaded(episode.url):
            prefix += "⬇ "
        return prefix

    def _refresh_episode_marks(self) -> None:
        played = set(self._played())
        self._episode_table.setRowCount(len(self._episodes))
        for row, episode in enumerate(self._episodes):
            prefix = ("✓ " if episode.url in played else "")
            if self._cache is not None and self._cache.is_downloaded(episode.url):
                prefix += "⬇ "
            self._episode_table.setItem(row, 0, QTableWidgetItem(prefix + episode.title))
            self._episode_table.setItem(row, 1, QTableWidgetItem(episode.published))
            minutes, seconds = divmod(int(episode.duration or 0), 60)
            duration = f"{minutes}:{seconds:02d}" if episode.duration else ""
            self._episode_table.setItem(row, 2, QTableWidgetItem(duration))
            self._episode_table.item(row, 0).setData(Qt.UserRole, episode)
        if 0 <= self._episode_table.currentRow() < len(self._episodes):
            self._episode_table.selectRow(self._episode_table.currentRow())

    def _download_selected(self) -> None:
        if self._cache is None:
            self._status.setText("播客缓存不可用。")
            return
        if self._config is not None and not bool(self._config.get("podcast_download_ack", False)):
            answer = QMessageBox.question(
                self,
                "播客下载",
                "下载仅用于你个人离线收听。\n\n"
                "请确认你已获得该播客内容的合法访问权，并遵守节目发布者的条款；"
                "下载文件不会上传或分发。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return
            self._config.set("podcast_download_ack", True)
        row = self._episode_table.currentRow()
        if not (0 <= row < len(self._episodes)):
            self._status.setText("请先选择一个单集。")
            return
        episode = self._episodes[row]
        if self._cache.is_downloaded(episode.url):
            self._status.setText("该单集已经下载。")
            return
        if (self._download_thread is not None and self._download_thread.isRunning()
                and self._download_thread.property("url") == episode.url):
            self._status.setText("该单集正在下载。")
            return
        if any(item.url == episode.url for item in self._download_queue):
            self._status.setText("该单集已在下载队列中。")
            return
        self._download_queue.append(episode)
        self._status.setText(
            f"已加入下载队列：{episode.title}（队列 {len(self._download_queue)}）"
        )
        if self._download_thread is None or not self._download_thread.isRunning():
            self._start_next_download()

    def _start_next_download(self) -> None:
        if not self._download_queue:
            self._status.setText(
                f"下载队列为空。缓存 {self._cache.total_bytes() / 1024 / 1024:.1f} MB"
                if self._cache is not None else "缓存不可用。"
            )
            return
        if self._cache is None:
            return
        episode = self._download_queue.popleft()
        self._download_thread = EpisodeDownloadThread(self._cache, episode, self)
        self._download_thread.setProperty("url", episode.url)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.downloaded.connect(self._on_downloaded)
        self._download_thread.failed.connect(self._on_download_failed)
        self._download_thread.finished.connect(self._start_next_download)
        self._download_thread.start()
        self._status.setText(f"开始下载：{episode.title}")

    def _on_download_progress(self, url: str, done: int, total: int) -> None:
        if total > 0:
            self._status.setText(f"下载中：{done * 100 // total}%（{done / 1024 / 1024:.1f} MB）")
        else:
            self._status.setText(f"下载中：{done / 1024 / 1024:.1f} MB")

    def _on_downloaded(self, url: str, path: str) -> None:
        self._refresh_episode_marks()
        self._status.setText(f"下载完成，已缓存：{path}")

    def _on_download_failed(self, url: str, message: str) -> None:
        self._status.setText("下载失败。")
        QMessageBox.warning(self, "播客下载", message)

    def _delete_selected(self) -> None:
        if self._cache is None:
            return
        row = self._episode_table.currentRow()
        if not (0 <= row < len(self._episodes)):
            self._status.setText("请先选择一个单集。")
            return
        episode = self._episodes[row]
        if not self._cache.remove(episode.url):
            self._status.setText("该单集没有缓存。")
            return
        self._refresh_episode_marks()
        self._status.setText(f"已删除缓存：{episode.title}")

    def _subscriptions(self) -> list[Podcast]:
        if self._config is None:
            return []
        result = []
        for item in self._config.get("podcast_subscriptions", []) or []:
            podcast = Podcast.from_dict(item)
            if podcast is not None:
                result.append(podcast)
        return result

    def _set_subscriptions(self, podcasts: list[Podcast]) -> None:
        if self._config is None:
            return
        self._config.set("podcast_subscriptions", [item.as_dict() for item in podcasts])

    def _subscription_for_selected(self) -> Podcast | None:
        row = self._podcast_table.currentRow()
        if 0 <= row < len(self._podcasts):
            return self._podcasts[row]
        return None

    def _toggle_subscription(self) -> None:
        podcast = self._subscription_for_selected()
        if podcast is None:
            self._status.setText("请先选择一个播客。")
            return
        subscriptions = self._subscriptions()
        if any(item.feed_url == podcast.feed_url for item in subscriptions):
            subscriptions = [item for item in subscriptions if item.feed_url != podcast.feed_url]
            self._status.setText(f"已取消订阅：{podcast.name}")
        else:
            subscriptions.append(podcast)
            self._status.setText(f"已订阅：{podcast.name}")
        self._set_subscriptions(subscriptions)
        self._show_podcasts(self._podcasts)

    def _played(self) -> list[str]:
        if self._config is None:
            return []
        return list(self._config.get("podcast_played", []) or [])

    def _show_subscriptions(self) -> None:
        self._podcasts = self._subscriptions()
        self._show_podcasts(self._podcasts)
        self._status.setText(
            f"我的订阅：{len(self._podcasts)} 个播客。" if self._podcasts else "还没有订阅播客。"
        )

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
        self._download_queue.clear()
        for thread in (self._search_thread, self._episode_thread, self._download_thread):
            if thread is not None and thread.isRunning():
                thread.requestInterruption()
                thread.wait(9000)
        super().closeEvent(event)
