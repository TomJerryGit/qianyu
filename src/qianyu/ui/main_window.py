# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Main window for the 0.9 music player.

Deliberately one window: library (left), lyrics (right), transport (bottom).
Video mode is not part of 0.9.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ..qt import DIALOG_ACCEPTED, QColor, QObject, QProcess, QSize, Qt, QThread, QTimer, QUrl, pyqtSignal
from ..qt import QDesktopServices, QIcon, QKeySequence, QPixmap
from ..qt import (
    QAbstractItemView, QAction, QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
    QMessageBox, QPushButton, QShortcut, QSlider, QSplitter, QStackedWidget,
    QStyle, QSystemTrayIcon, QTableView, QVBoxLayout, QWidget, QHeaderView,
)

from ..config import Config
from ..core.lyrics import decode_lrc, find_lrc, line_index_at, load_lrc
from ..core.models import Playlist, PlaylistItem, Track
from ..core.playlist import PlaylistStore
from ..engine.mpv_engine import EngineEvent, EngineState, MpvEngine
from ..library import Library, ScanResult
from ..platform.media_keys import MediaKeyManager
from .desktop_lyrics import DesktopLyricsWindow
from .album_view import AlbumView
from .batch_tag_dialog import BatchTagDialog
from .cue_dialog import CueDialog
from .duplicate_dialog import DuplicateDialog
from .eq_dialog import EqualizerDialog
from .lyrics_editor import LyricsEditorDialog
from .mini_player import MiniPlayer
from .now_playing import NowPlayingPage
from .radio_dialog import RadioDialog
from .podcast_dialog import PodcastDialog
from .remote_dialog import RemoteDialog, make_client
from .radio_window import RadioWindow
from .remote_album_dialog import RemoteAlbumDialog
from .unified_search import UnifiedSearchDialog
from .tag_dialog import TagEditDialog
from .theme_color import dominant_color
from ..core.cue import parse_cue
from ..core.metadata import fetch_cover, lookup_recording
from ..core.radio import RadioStation
from ..core.radio_presets import preset_stations
from ..core.podcast import Episode
from ..core.podcast_cache import PodcastCache
from ..core.subsonic import RemoteSong
from ..core.jellyfin import JellyfinClient, JellyfinItem
from ..core.scrobble import ListenBrainzScrobbler
from ..core.secure_store import SecretStore
from ..core.tagging import write_tags
from .settings_dialog import SettingsDialog
from .track_model import TrackTableModel
from .video_window import VideoWindow


def format_time(seconds: float) -> str:
    seconds = max(0, int(seconds or 0))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:02d}:{sec:02d}"


class EngineBridge(QObject):
    event = pyqtSignal(object)


class ScanThread(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, library: Library, folder: str, parent=None):
        super().__init__(parent)
        self._library = library
        self._folder = folder
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            result = self._library.scan(
                self._folder,
                progress=lambda index, path: self.progress.emit(index, path),
                cancel=lambda: self._cancelled,
            )
            self.done.emit(result)
        except Exception as exc:  # pragma: no cover - UI fallback
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class MainWindow(QMainWindow):
    def __init__(self, config: Config, engine: MpvEngine | None = None, data_dir: str | Path | None = None):
        super().__init__()
        self._config = config
        self._secrets = SecretStore(config)
        try:
            self._secrets.migrate(["listenbrainz_token", "subsonic_password", "jellyfin_password", "jellyfin_token"])
        except Exception:
            pass
        base = Path(data_dir) if data_dir else Path.home() / ".qianyu_media"
        try:
            base.mkdir(parents=True, exist_ok=True)
            probe = base / ".write-test"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
        except OSError:
            # Locked-down profiles still get a usable session instead of a
            # startup crash; the data simply lives in a temp directory.
            base = Path(tempfile.mkdtemp(prefix="qianyu-data-"))
        self._artist_cache_dir = base / "artist_images"
        self._library = Library(base / "library.db")
        self._podcast_cache = PodcastCache(
            base / "podcast_cache",
            limit_mb=int(config.get("podcast_cache_limit_mb", 2048)),
        )
        self._scrobbler = ListenBrainzScrobbler(config)
        self._playlist_store = PlaylistStore(base / "playlist.json")
        self._playlist: Playlist = self._playlist_store.playlist
        self._tracks: list[Track] = []
        self._current: Track | None = None
        self._radio_station: RadioStation | None = None
        self._radio_retries = 0
        self._radio_stream_title = ""
        self._radio_window: RadioWindow | None = None
        self._remote_queue: list[Track] = []
        self._remote_queue_index = -1
        self._lyrics = []
        self._lyrics_index = -1
        self._lyrics_offset_ms = 0
        self._current_lrc_path: Path | None = None
        self._cover_cache: dict[tuple[str, float], QPixmap] = {}
        self._base_qss = ""
        self._accent: QColor | None = None
        self._lyrics_map = dict(self._config.get("lyrics_map", {}) or {})
        self._lyrics_offsets = dict(self._config.get("lyrics_offsets", {}) or {})
        self._seeking = False
        self._scan_thread: ScanThread | None = None
        self._volume_before_mute = 70
        self._shortcuts = []
        self._tray: QSystemTrayIcon | None = None
        self._force_quit = False
        self._shutdown_done = False
        self._theme_actions: dict[str, QAction] = {}
        self._desktop_lyrics: DesktopLyricsWindow | None = None
        self._mini: MiniPlayer | None = None
        self._now_page: NowPlayingPage | None = None
        self._cue_tracks = None
        self._cue_sheet = None
        self._album_dirty = True
        self._library_signature = None
        self._library_mode = "all"
        self._media_keys: MediaKeyManager | None = None
        self._video: VideoWindow | None = None

        self._bridge = EngineBridge()
        self._bridge.event.connect(self._on_engine_event)
        self._engine = engine or MpvEngine(
            on_event=lambda event: self._bridge.event.emit(event),
            volume=int(config.get("volume", 70)),
        )
        self._engine.set_event_callback(lambda event: self._bridge.event.emit(event))
        self._build_ui()
        self._build_menu()
        self._build_tray()
        self._init_media_keys()
        self._bind_shortcuts()
        self._refresh_library()
        self._refresh_playlist()

        self._engine.volume = int(config.get("volume", 70))
        try:
            self._engine.set_replaygain(str(config.get("replaygain", "no")))
            self._engine.set_audio_exclusive(bool(config.get("audio_exclusive", False)))
        except Exception:
            pass
        self._volume.setValue(int(config.get("volume", 70)))
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        if not os.environ.get("QIANYU_NO_TIMER"):
            self._timer.start(200)

        self.setWindowTitle("浅语影音 0.9")
        width = int(config.get("window", {}).get("w", 1180))
        height = int(config.get("window", {}).get("h", 760))
        self.resize(width, height)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(10, 10, 10, 8)
        outer.setSpacing(8)

        toolbar = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("搜索标题、艺术家、专辑…")
        self._search.setClearButtonEnabled(True)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(160)
        self._search_timer.timeout.connect(self._refresh_library)
        self._search.textChanged.connect(lambda _text: self._search_timer.start())
        self._playlist_save_timer = QTimer(self)
        self._playlist_save_timer.setSingleShot(True)
        self._playlist_save_timer.setInterval(500)
        self._playlist_save_timer.timeout.connect(self._playlist_store.save)
        toolbar.addWidget(self._search, 1)
        open_folder = QPushButton("扫描文件夹")
        open_folder.setObjectName("primaryButton")
        open_folder.clicked.connect(self._choose_folder)
        toolbar.addWidget(open_folder)
        self._cancel_scan_btn = QPushButton("取消扫描")
        self._cancel_scan_btn.setEnabled(False)
        self._cancel_scan_btn.clicked.connect(self._cancel_scan)
        toolbar.addWidget(self._cancel_scan_btn)
        add_selected = QPushButton("加入播放列表")
        add_selected.clicked.connect(self._add_selected)
        toolbar.addWidget(add_selected)
        edit_tags = QPushButton("编辑标签")
        edit_tags.clicked.connect(self._edit_tags)
        toolbar.addWidget(edit_tags)
        self._grid_toggle = QPushButton("封面")
        self._grid_toggle.setCheckable(True)
        self._grid_toggle.setToolTip("切换封面网格（专辑/艺术家）")
        self._grid_toggle.toggled.connect(self._toggle_grid)
        toolbar.addWidget(self._grid_toggle)
        outer.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        outer.addWidget(splitter, 1)

        # library
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        library_header = QHBoxLayout()
        library_title = QLabel("媒体库")
        library_title.setObjectName("sectionTitle")
        self._library_filter = QComboBox()
        self._library_filter.setMinimumWidth(90)
        self._library_filter.addItem("全部", "all")
        self._library_filter.addItem("收藏", "favorite")
        self._library_filter.addItem("最近播放", "recent")
        self._library_filter.addItem("最近添加", "added")
        self._library_filter.addItem("最常播放", "most_played")
        self._library_filter.addItem("未播放", "unplayed")
        self._library_filter.currentIndexChanged.connect(lambda _index: self._refresh_library())
        self._favorite_btn = QPushButton("收藏")
        self._favorite_btn.setToolTip("收藏/取消收藏选中曲目")
        self._favorite_btn.clicked.connect(self._toggle_favorite)
        self._stats = QLabel("")
        self._stats.setObjectName("stats")
        library_header.addWidget(library_title)
        library_header.addWidget(self._library_filter)
        library_header.addWidget(self._favorite_btn)
        library_header.addStretch(1)
        library_header.addWidget(self._stats)
        left_layout.addLayout(library_header)
        self._table = QTableView()
        self._track_model = TrackTableModel(parent=self._table)
        self._table.setModel(self._track_model)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(30)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setColumnWidth(3, 90)
        self._table.doubleClicked.connect(lambda index: self._play_library_row(index.row()))
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._library_context_menu)
        self._album_view = AlbumView()
        self._album_view.activated.connect(self._on_album_activated)
        self._library_stack = QStackedWidget()
        self._library_stack.addWidget(self._table)
        self._library_stack.addWidget(self._album_view)
        self._empty_hint = QLabel("媒体库还是空的\n点击「扫描文件夹」开始")
        self._empty_hint.setObjectName("emptyHint")
        self._empty_hint.setAlignment(Qt.AlignCenter)
        self._empty_hint.setVisible(False)
        self._library_stack.addWidget(self._empty_hint)
        left_layout.addWidget(self._library_stack, 3)

        playlist_header = QHBoxLayout()
        playlist_title = QLabel("播放队列")
        playlist_title.setObjectName("sectionTitle")
        self._queue_toggle = QPushButton("收起队列")
        self._queue_toggle.setCheckable(True)
        self._queue_toggle.toggled.connect(self._toggle_queue)
        playlist_header.addWidget(playlist_title)
        playlist_header.addStretch(1)
        playlist_header.addWidget(self._queue_toggle)
        left_layout.addLayout(playlist_header)
        self._playlist_view = QListWidget()
        self._playlist_view.setAlternatingRowColors(True)
        self._playlist_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._playlist_view.setDragDropMode(QAbstractItemView.InternalMove)
        self._playlist_view.setDefaultDropAction(Qt.MoveAction)
        self._playlist_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self._playlist_view.customContextMenuRequested.connect(self._playlist_context_menu)
        self._playlist_view.itemDoubleClicked.connect(self._play_playlist_row)
        self._playlist_view.model().rowsMoved.connect(self._on_playlist_rows_moved)
        left_layout.addWidget(self._playlist_view, 2)
        pl_buttons = QHBoxLayout()
        self._remove_btn = QPushButton("移除")
        self._remove_btn.clicked.connect(self._remove_playlist_row)
        self._clear_btn = QPushButton("清空")
        self._clear_btn.clicked.connect(self._clear_playlist)
        pl_buttons.addWidget(self._remove_btn)
        pl_buttons.addWidget(self._clear_btn)
        pl_buttons.addStretch(1)
        left_layout.addLayout(pl_buttons)
        splitter.addWidget(left)

        # right: cover + now playing + lyrics
        right = QWidget()
        right_layout = QVBoxLayout(right)
        self._cover = QLabel()
        self._cover.setObjectName("cover")
        self._cover.setFixedSize(168, 168)
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setText("♪")
        right_layout.addWidget(self._cover, 0, Qt.AlignHCenter)
        self._now_title = QLabel("未在播放")
        self._now_title.setObjectName("nowTitle")
        self._now_title.setAlignment(Qt.AlignHCenter)
        self._now_meta = QLabel("")
        self._now_meta.setObjectName("nowMeta")
        self._now_meta.setAlignment(Qt.AlignHCenter)
        right_layout.addWidget(self._now_title)
        right_layout.addWidget(self._now_meta)
        lyrics_bar = QHBoxLayout()
        associate = QPushButton("关联歌词")
        associate.clicked.connect(self._associate_lyrics)
        edit = QPushButton("编辑歌词")
        edit.clicked.connect(self._edit_lyrics)
        online = QPushButton("在线歌词")
        online.clicked.connect(self._fetch_online_lyrics)
        minus = QPushButton("−0.5 s")
        minus.clicked.connect(lambda: self._nudge_lyrics_offset(-500))
        plus = QPushButton("+0.5 s")
        plus.clicked.connect(lambda: self._nudge_lyrics_offset(500))
        self._offset_label = QLabel("偏移 0 ms")
        self._offset_label.setObjectName("offsetLabel")
        lyrics_bar.addWidget(associate)
        lyrics_bar.addWidget(edit)
        lyrics_bar.addWidget(online)
        lyrics_bar.addWidget(minus)
        lyrics_bar.addWidget(plus)
        lyrics_bar.addStretch(1)
        lyrics_bar.addWidget(self._offset_label)
        right_layout.addLayout(lyrics_bar)
        self._lyrics_view = QListWidget()
        self._lyrics_view.setSelectionMode(QAbstractItemView.NoSelection)
        right_layout.addWidget(self._lyrics_view, 1)
        splitter.addWidget(right)
        splitter.setSizes([720, 380])

        # transport
        transport = QHBoxLayout()
        self._prev_btn = self._icon_button(QStyle.SP_MediaSkipBackward, "上一首")
        self._play_btn = self._icon_button(QStyle.SP_MediaPlay, "播放/暂停")
        self._stop_btn = self._icon_button(QStyle.SP_MediaStop, "停止")
        self._next_btn = self._icon_button(QStyle.SP_MediaSkipForward, "下一首")
        self._prev_btn.clicked.connect(self._previous)
        self._play_btn.clicked.connect(self._toggle)
        self._stop_btn.clicked.connect(self._stop_playback)
        self._next_btn.clicked.connect(self._next)
        for button in (self._prev_btn, self._play_btn, self._stop_btn, self._next_btn):
            transport.addWidget(button)

        self._progress = QSlider(Qt.Horizontal)
        self._progress.setRange(0, 1000)
        self._progress.sliderPressed.connect(self._begin_seek)
        self._progress.sliderReleased.connect(self._end_seek)
        transport.addWidget(self._progress, 1)
        self._time = QLabel("00:00 / 00:00")
        transport.addWidget(self._time)

        self._mute = QPushButton("静音")
        self._mute.setCheckable(True)
        self._mute.toggled.connect(self._toggle_mute)
        transport.addWidget(self._mute)
        self._volume = QSlider(Qt.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(70)
        self._volume.setMaximumWidth(110)
        self._volume.valueChanged.connect(self._on_volume)
        self._volume.sliderReleased.connect(lambda: self._config.set("volume", self._volume.value()))
        transport.addWidget(self._volume)
        eq = QPushButton("均衡器")
        eq.clicked.connect(self._show_eq)
        transport.addWidget(eq)
        outer.addLayout(transport)

        self._status = self.statusBar()
        self._status.showMessage("就绪")

    def _icon_button(self, icon, tooltip):
        button = QPushButton(self.style().standardIcon(icon), "")
        button.setToolTip(tooltip)
        button.setFixedSize(36, 30)
        return button

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        open_action = QAction("扫描文件夹…", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._choose_folder)
        file_menu.addAction(open_action)
        cue_action = QAction("打开 CUE…", self)
        cue_action.triggered.connect(self._open_cue)
        file_menu.addAction(cue_action)
        video_action = QAction("打开视频…", self)
        video_action.setShortcut(QKeySequence("Ctrl+Shift+O"))
        video_action.triggered.connect(self._open_video_dialog)
        file_menu.addAction(video_action)
        file_menu.addSeparator()
        quit_action = QAction("退出", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self._quit)
        file_menu.addAction(quit_action)

        online_menu = self.menuBar().addMenu("在线")
        online_menu.addAction("统一搜索…", self._show_unified_search)
        online_menu.addAction("网络电台…", self._show_radio)
        online_menu.addAction("经典电台窗口", self._show_radio_window)
        online_menu.addAction("播客…", self._show_podcasts)
        online_menu.addAction("远程媒体库…", self._show_remote)
        online_menu.addAction("远程专辑…", self._show_remote_albums)
        online_menu.addAction("打开网络流…", self._open_stream)

        playback = self.menuBar().addMenu("播放")
        playback.addAction("播放/暂停", self._toggle)
        playback.addAction("停止", self._stop_playback)
        playback.addAction("上一首", self._previous)
        playback.addAction("下一首", self._next)
        playback.addSeparator()
        mute = QAction("静音", self)
        mute.setCheckable(True)
        mute.toggled.connect(self._mute.setChecked)
        playback.addAction(mute)

        tools = self.menuBar().addMenu("工具")
        tools.addAction("查找重复曲目…", self._find_duplicates)
        tools.addAction("深度去重（音频指纹）…", self._find_duplicates_deep)
        tools.addAction("注册文件关联…", self._register_association)
        tools.addAction("取消文件关联", self._unregister_association)

        view = self.menuBar().addMenu("视图")
        view.addAction("经典音乐模式（全屏播放页）", self._show_now_page)
        view.addAction("经典电台模式", self._show_radio_window)
        view.addAction("均衡器", self._show_eq)
        view.addAction("设置…", self._show_settings)
        self._desktop_action = QAction("桌面歌词", self)
        self._desktop_action.setCheckable(True)
        self._desktop_action.toggled.connect(self._toggle_desktop_lyrics)
        view.addAction(self._desktop_action)
        self._mini_action = QAction("迷你模式", self)
        self._mini_action.setCheckable(True)
        self._mini_action.toggled.connect(self._toggle_mini)
        view.addAction(self._mini_action)
        theme_menu = view.addMenu("主题")
        for name, label in (("dark", "深色"), ("light", "浅色")):
            action = QAction(label, self)
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, n=name: self._set_theme(n))
            theme_menu.addAction(action)
            self._theme_actions[name] = action
        self._theme_actions.get(str(self._config.get("theme", "dark")), self._theme_actions["dark"]).setChecked(True)

        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction("检查更新…", self._check_updates)
        help_menu.addAction("关于", self._about)

    def _build_tray(self) -> None:
        if os.environ.get("QIANYU_NO_TRAY"):
            return
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        tray = QSystemTrayIcon(icon, self)
        menu = QMenu(self)
        self._tray_menu = menu
        menu.addAction("显示主窗口", self._show_window)
        menu.addAction("播放/暂停", self._toggle)
        menu.addAction("上一首", self._previous)
        menu.addAction("下一首", self._next)
        menu.addSeparator()
        menu.addAction("退出", self._quit)
        tray.setContextMenu(menu)
        tray.setToolTip("浅语影音 0.9")
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self._tray = tray

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._show_window()

    def _init_media_keys(self) -> None:
        if os.environ.get("QIANYU_NO_TRAY") or os.environ.get("QIANYU_NO_MEDIA_KEYS"):
            return
        if not bool(self._config.get("global_media_keys", True)):
            return
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self._media_keys = MediaKeyManager(QApplication.instance(), self)
        self._media_keys.register(self._toggle, self._next, self._previous, self._stop_playback)

    def _show_window(self) -> None:
        if self._mini is not None:
            self._mini.hide()
        if hasattr(self, "_mini_action"):
            self._mini_action.blockSignals(True)
            self._mini_action.setChecked(False)
            self._mini_action.blockSignals(False)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit(self) -> None:
        self._force_quit = True
        self._shutdown()
        QApplication.quit()

    def _set_theme(self, name: str) -> None:
        path = Path(__file__).resolve().parent / "theme" / f"{name}.qss"
        try:
            self._base_qss = path.read_text(encoding="utf-8")
            self._apply_qss()
        except OSError:
            return
        self._config.set("theme", name)
        for key, action in self._theme_actions.items():
            action.setChecked(key == name)

    def _apply_qss(self) -> None:
        app = QApplication.instance()
        if app is None or not self._base_qss:
            return
        qss = self._base_qss
        if self._accent is not None:
            qss = qss.replace("#3b6ef5", self._accent.name())
            qss = qss.replace("#4c7dff", self._accent.lighter(115).name())
            qss = qss.replace("#2f4a9e", self._accent.darker(135).name())
            qss = qss.replace("#2f5fe0", self._accent.darker(115).name())
        app.setStyleSheet(qss)

    def _apply_cover_accent(self, cover: str) -> None:
        color = dominant_color(cover) if cover else None
        if (color is None) == (self._accent is None):
            if color is not None and self._accent is not None and color == self._accent:
                return
        self._accent = color
        self._apply_qss()

    def _bind_shortcuts(self) -> None:
        def shortcut(sequence, slot):
            sc = QShortcut(QKeySequence(sequence), self)
            sc.activated.connect(slot)
            self._shortcuts.append(sc)
            return sc

        shortcut("Space", self._toggle)
        shortcut("Ctrl+Left", lambda: self._seek_relative(-5))
        shortcut("Ctrl+Right", lambda: self._seek_relative(5))
        shortcut("Ctrl+Up", lambda: self._nudge_volume(5))
        shortcut("Ctrl+Down", lambda: self._nudge_volume(-5))

    # ------------------------------------------------------------------
    # library / playlist
    # ------------------------------------------------------------------
    def _refresh_library(self, force: bool = False) -> None:
        keyword = self._search.text() if hasattr(self, "_search") else ""
        try:
            tracks = self._library.search(keyword)
        except Exception as exc:
            self._status.showMessage(f"读取媒体库失败：{exc}")
            tracks = []
        mode = self._library_filter.currentData() if hasattr(self, "_library_filter") else "all"
        if mode == "favorite":
            tracks = [track for track in tracks if track.favorite]
        elif mode == "recent":
            tracks = [track for track in tracks if track.last_played > 0]
            tracks.sort(key=lambda track: track.last_played, reverse=True)
            tracks = tracks[:200]
        elif mode == "added":
            tracks.sort(key=lambda track: track.added_at, reverse=True)
            tracks = tracks[:200]
        elif mode == "most_played":
            tracks = [track for track in tracks if track.play_count > 0]
            tracks.sort(key=lambda track: track.play_count, reverse=True)
            tracks = tracks[:200]
        elif mode == "unplayed":
            tracks = [track for track in tracks if track.play_count == 0]
        signature = tuple(
            (track.path, track.title, track.artist, track.album, track.duration,
             track.favorite, track.play_count, track.last_played, track.added_at,
             track.cover, track.cue_path, track.start, track.end)
            for track in tracks
        )
        if not force and signature == self._library_signature and mode == self._library_mode:
            return
        self._library_signature = signature
        self._library_mode = mode
        self._tracks = tracks
        self._track_model.set_tracks(self._tracks)
        self._album_dirty = True
        if self._grid_toggle.isChecked():
            try:
                self._album_view.set_tracks(self._tracks)
                self._album_dirty = False
            except Exception:
                pass
        total = sum(max(0.0, track.duration or 0.0) for track in self._tracks)
        hours, remainder = divmod(int(total), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            duration = f"{hours}:{minutes:02d}:{seconds:02d}"
        elif minutes:
            duration = f"{minutes} 分钟"
        else:
            duration = f"{seconds} 秒"
        self._stats.setText(f"{len(self._tracks)} 首 · {duration}")
        if not self._tracks:
            self._library_stack.setCurrentWidget(self._empty_hint)
            self._empty_hint.setText(
                "没有匹配结果\n换个关键词试试" if keyword
                else "媒体库还是空的\n点击「扫描文件夹」开始"
            )
        elif self._grid_toggle.isChecked():
            self._library_stack.setCurrentWidget(self._album_view)
        else:
            self._library_stack.setCurrentWidget(self._table)

    def _toggle_favorite(self) -> None:
        track = self._selected_track()
        if track is None:
            self._status.showMessage("请先在媒体库中选择一首曲目")
            return
        favorite = not track.favorite
        self._library.set_favorite(track.path, favorite)
        self._refresh_library()
        self._status.showMessage("已收藏" if favorite else "已取消收藏")

    def _toggle_grid(self, checked: bool) -> None:
        if checked and self._tracks:
            if self._album_dirty:
                self._album_view.set_tracks(self._tracks)
                self._album_dirty = False
            self._library_stack.setCurrentWidget(self._album_view)
        elif self._tracks:
            self._library_stack.setCurrentWidget(self._table)
        else:
            self._library_stack.setCurrentWidget(self._empty_hint)

    def _toggle_queue(self, hidden: bool) -> None:
        self._playlist_view.setVisible(not hidden)
        self._remove_btn.setVisible(not hidden)
        self._clear_btn.setVisible(not hidden)
        self._queue_toggle.setText("展开队列" if hidden else "收起队列")

    def _on_album_activated(self, key: str) -> None:
        self._search_timer.stop()
        self._grid_toggle.blockSignals(True)
        self._grid_toggle.setChecked(False)
        self._grid_toggle.blockSignals(False)
        self._search.setText(key)
        self._search_timer.stop()
        self._refresh_library()
        needle = key.casefold()
        for index, track in enumerate(self._tracks):
            if (track.album or "未知专辑").casefold() == needle or \
                    (track.artist or "未知艺术家").casefold() == needle:
                self._play_library_row(index)
                return
        self._status.showMessage(f"没有找到分组：{key}")

    def _refresh_playlist(self) -> None:
        items = self._playlist.items
        self._playlist_view.setUpdatesEnabled(False)
        try:
            while self._playlist_view.count() > len(items):
                self._playlist_view.takeItem(self._playlist_view.count() - 1)
            for index, item in enumerate(items):
                existing = self._playlist_view.item(index)
                if existing is None:
                    existing = QListWidgetItem(item.display)
                    existing.setData(Qt.UserRole, item.path)
                    self._playlist_view.addItem(existing)
                else:
                    if existing.text() != item.display:
                        existing.setText(item.display)
                    if existing.data(Qt.UserRole) != item.path:
                        existing.setData(Qt.UserRole, item.path)
            if 0 <= self._playlist.current_index < self._playlist_view.count():
                self._playlist_view.setCurrentRow(self._playlist.current_index)
                self._playlist_view.scrollToItem(
                    self._playlist_view.item(self._playlist.current_index),
                    QAbstractItemView.PositionAtCenter,
                )
        finally:
            self._playlist_view.setUpdatesEnabled(True)

    def _on_playlist_rows_moved(self, _parent, start, end, _dest, row) -> None:
        # Rebuild the model from the view; handle the common single-row move in
        # mpv too so the running queue keeps its new order.
        items = []
        for i in range(self._playlist_view.count()):
            entry = self._playlist_view.item(i)
            items.append(PlaylistItem(path=entry.data(Qt.UserRole), title=entry.text()))
        self._playlist.items = items
        self._playlist.current_index = self._playlist_view.currentRow()
        if start == end and self._engine.queue:
            dest = row - 1 if row > start else row
            self._engine.move_index(start, dest)
        self._playlist_store.save()

    def _playlist_context_menu(self, pos) -> None:
        item = self._playlist_view.itemAt(pos)
        if item is None:
            return
        self._playlist_view.setCurrentItem(item)
        path = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("播放", lambda: self._play_playlist_row(item))
        menu.addAction("在文件夹中显示", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent))))
        menu.addAction("复制路径", lambda: QApplication.clipboard().setText(str(path)))
        menu.addSeparator()
        menu.addAction("从列表移除", self._remove_playlist_row)
        menu.exec_(self._playlist_view.viewport().mapToGlobal(pos))

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择音乐文件夹", self._config.get("last_folder", ""))
        if not folder:
            return
        self._config.set("last_folder", folder)
        folders = list(self._config.get("library_folders", []))
        if folder not in folders:
            folders.append(folder)
            self._config.set("library_folders", folders)
        self._status.showMessage(f"正在扫描：{folder}")
        self._scan_thread = ScanThread(self._library, folder, self)
        self._scan_thread.progress.connect(self._on_scan_progress)
        self._scan_thread.done.connect(self._on_scan_done)
        self._scan_thread.failed.connect(self._on_scan_failed)
        self._cancel_scan_btn.setEnabled(True)
        self._scan_thread.start()

    def _on_scan_failed(self, message: str) -> None:
        self._status.showMessage(f"扫描失败：{message}")
        self._cancel_scan_btn.setEnabled(False)
        self._scan_thread = None

    def _cancel_scan(self) -> None:
        if self._scan_thread is not None:
            self._scan_thread.cancel()
            self._status.showMessage("正在取消扫描…")

    def _on_scan_progress(self, index: int, path: str) -> None:
        self._status.showMessage(f"正在扫描 {index}：{os.path.basename(path)}")

    def _on_scan_done(self, result: ScanResult) -> None:
        self._status.showMessage(
            f"扫描完成：新增 {result.added}，更新 {result.updated}，跳过 {result.skipped}，错误 {result.errors}"
        )
        self._refresh_library()
        self._scan_thread = None
        self._cancel_scan_btn.setEnabled(False)

    def _selected_track(self) -> Track | None:
        index = self._table.currentIndex()
        row = index.row() if index.isValid() else -1
        if not (0 <= row < len(self._tracks)):
            rows = self._table.selectionModel().selectedRows()
            row = rows[0].row() if rows else -1
        return self._tracks[row] if 0 <= row < len(self._tracks) else None

    def _library_context_menu(self, pos) -> None:
        index = self._table.indexAt(pos)
        if not index.isValid():
            return
        self._table.setCurrentIndex(index)
        track = self._tracks[index.row()]
        menu = QMenu(self)
        menu.addAction("播放", lambda: self._play_library_row(index.row()))
        menu.addAction("加入播放列表", self._add_selected)
        menu.addSeparator()
        menu.addAction("取消收藏" if track.favorite else "收藏", self._toggle_favorite)
        menu.addAction("编辑标签…", self._edit_tags)
        menu.addAction("批量编辑标签…", self._batch_edit_tags)
        menu.addAction("获取在线封面", self._fetch_online_cover)
        menu.addAction("在文件夹中显示",
                       lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(track.path).parent))))
        menu.addAction("复制路径", lambda: QApplication.clipboard().setText(track.path))
        menu.exec(self._table.viewport().mapToGlobal(pos))

    def _fetch_online_cover(self) -> None:
        track = self._selected_track()
        if track is None:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            match = lookup_recording(track.title, track.artist)
            data = fetch_cover(match.release_id) if match is not None else None
        finally:
            QApplication.restoreOverrideCursor()
        if not data:
            self._status.showMessage("未找到在线封面，或网络不可用")
            return
        import hashlib

        digest = hashlib.sha1(track.path.encode("utf-8")).hexdigest()[:16]
        target = self._library.covers_dir / f"online-{digest}.jpg"
        try:
            target.write_bytes(data)
        except OSError as exc:
            self._status.showMessage(f"封面保存失败：{exc}")
            return
        self._library.set_cover(track.path, str(target))
        self._refresh_library()
        if self._current is not None and (
            self._current.path == track.path
            or (track.cue_path and self._current.cue_path == track.cue_path)
        ):
            updated = self._library.get(self._current.path)
            if updated is not None:
                self._current = updated
                self._set_now_playing(updated)
        self._status.showMessage("已保存在线封面")

    def _edit_tags(self) -> None:
        track = self._selected_track()
        if track is None:
            self._status.showMessage("请先在媒体库中选择一首曲目")
            return
        if track.cue_path:
            self._status.showMessage("CUE 曲目请编辑 CUE/整轨标签，避免影响整轨文件")
            return
        dialog = TagEditDialog(track, self)
        if dialog.exec() != DIALOG_ACCEPTED:
            return
        values = dialog.values()
        if not values["title"]:
            values["title"] = Path(track.path).stem
        tags = {
            "title": values["title"],
            "artist": values["artist"],
            "album": values["album"],
            "tracknumber": str(values["track_no"]),
            "discnumber": str(values["disc_no"]),
        }
        try:
            write_tags(track.path, tags)
            self._library.update_metadata(track.path, values)
        except Exception as exc:
            QMessageBox.warning(self, "标签写入失败", f"{type(exc).__name__}: {exc}")
            return
        self._refresh_library()
        if self._current is not None and self._current.path == track.path:
            updated = self._library.get(track.path)
            if updated is not None:
                self._current = updated
                self._set_now_playing(updated)
        self._status.showMessage(f"标签已更新：{values['title']}")

    def _find_duplicates_deep(self) -> None:
        from ..core.fingerprint import find_fpcalc

        if not find_fpcalc():
            answer = QMessageBox.question(
                self, "深度去重",
                "未安装 Chromaprint 的 fpcalc.exe。\n\n"
                "将使用内置 PCM 包络指纹（可识别转码/重封装副本，"
                "但弱于 Chromaprint）。是否继续？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            if answer != QMessageBox.Yes:
                return
        self._run_duplicate_scan(deep=True)

    def _find_duplicates(self) -> None:
        self._run_duplicate_scan(deep=False)

    def _run_duplicate_scan(self, deep: bool = False) -> None:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            groups = self._library.find_duplicates(deep=deep)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "查找重复失败", f"{type(exc).__name__}: {exc}")
            return
        QApplication.restoreOverrideCursor()
        if not groups:
            QMessageBox.information(self, "查找重复曲目", "没有发现重复曲目。")
            return
        dialog = DuplicateDialog(groups, self)
        if dialog.exec() != DIALOG_ACCEPTED:
            return
        paths = dialog.selected_paths()
        if not paths:
            return
        removed = self._library.remove_paths(paths)
        self._refresh_library()
        self._status.showMessage(f"已从媒体库移除 {removed} 首重复项（文件未删除）")

    def _batch_edit_tags(self) -> None:
        rows = sorted({index.row() for index in self._table.selectionModel().selectedRows()})
        if not rows:
            self._status.showMessage("请先在媒体库中多选曲目")
            return
        dialog = BatchTagDialog(len(rows), self)
        if dialog.exec() != DIALOG_ACCEPTED:
            return
        values = dialog.values()
        if not values:
            self._status.showMessage("没有勾选要修改的字段")
            return
        updated = 0
        errors = 0
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for row in rows:
                if not (0 <= row < len(self._tracks)):
                    continue
                track = self._tracks[row]
                if track.cue_path:
                    continue
                try:
                    write_tags(track.path, values)
                    self._library.update_metadata(track.path, values)
                    updated += 1
                except Exception:
                    errors += 1
        finally:
            QApplication.restoreOverrideCursor()
        self._refresh_library()
        self._status.showMessage(f"批量标签完成：{updated} 首，失败 {errors} 首")

    def _add_selected(self) -> None:
        rows = sorted({index.row() for index in self._table.selectionModel().selectedRows()})
        if not rows:
            self._status.showMessage("请先在媒体库中选择曲目")
            return
        added = 0
        for row in rows:
            if not (0 <= row < len(self._tracks)):
                continue
            track = self._tracks[row]
            if self._playlist.add(track.path, track.display):
                added += 1
        self._playlist_store.save()
        self._refresh_playlist()
        self._status.showMessage(f"已加入 {added} 首")

    def _remove_playlist_row(self) -> None:
        rows = sorted({index.row() for index in self._playlist_view.selectedIndexes()}, reverse=True)
        if not rows and self._playlist_view.currentRow() >= 0:
            rows = [self._playlist_view.currentRow()]
        if not rows:
            return
        for row in rows:
            if 0 <= row < len(self._playlist.items):
                self._playlist.remove(row)
                self._engine.remove_index(row)
        self._playlist_store.save()
        self._refresh_playlist()

    def _clear_playlist(self) -> None:
        self._playlist.clear()
        self._engine.clear_queue()
        self._playlist_store.save()
        self._refresh_playlist()
        self._current = None
        self._now_title.setText("未在播放")
        self._now_meta.setText("")
        self._cover.setPixmap(QPixmap())
        self._cover.setText("♪")
        self._lyrics = []
        self._lyrics_view.clear()
        self._progress.setValue(0)
        self._time.setText("00:00 / 00:00")
        if self._mini is not None:
            self._mini.set_track(None)

    # ------------------------------------------------------------------
    # playback
    # ------------------------------------------------------------------
    def _play_library_row(self, row: int, _column: int = 0) -> None:
        if not (0 <= row < len(self._tracks)):
            return
        track = self._tracks[row]
        if track.cue_path:
            self._play_cue_track(track)
            return
        if not any(item.path == track.path for item in self._playlist.items):
            self._playlist.add(track.path, track.display)
            self._playlist.select(len(self._playlist.items) - 1)
            self._playlist_store.save()
            self._refresh_playlist()
        else:
            index = next(i for i, item in enumerate(self._playlist.items) if item.path == track.path)
            self._playlist.select(index)
            self._refresh_playlist()
        self._start_track(track, self._playlist.current_index)

    def _play_playlist_row(self, item: QListWidgetItem) -> None:
        row = self._playlist_view.row(item)
        self._playlist.select(row)
        path = item.data(Qt.UserRole)
        track = self._library.get(path) or Track(path=path, title=Path(path).stem)
        self._start_track(track, row)

    def _start_track(self, track: Track, index: int | None = None) -> None:
        self._save_podcast_progress()
        self._podcast_url = None
        self._radio_station = None
        self._radio_stream_title = ""
        self._remote_queue = []
        self._remote_queue_index = -1
        if self._radio_window is not None:
            self._radio_window.hide()
        self._scrobbler.track_started(track)
        self._cue_tracks = None
        self._cue_sheet = None
        self._current = track
        try:
            self._library.mark_played(track.path)
        except Exception:
            pass
        self._set_now_playing(track)
        paths = [item.path for item in self._playlist.items]
        if not paths:
            paths = [track.path]
            index = 0
        if index is None:
            index = 0
        # One mpv playlist means the next file is already queued: gapless.
        self._engine.set_queue(paths, index)
        self._load_lyrics(track)
        self._progress.setValue(0)
        self._time.setText("00:00 / 00:00")
        self._update_now_page()
        self._status.showMessage(f"正在播放：{track.display}")

    def _set_now_playing(self, track: Track) -> None:
        self._now_title.setText(track.title or Path(track.path).name)
        meta = " · ".join(part for part in (track.artist, track.album) if part)
        self._now_meta.setText(meta or Path(track.path).parent.name)
        if track.cover and Path(track.cover).exists():
            cover_path = Path(track.cover)
            try:
                key = (str(cover_path), cover_path.stat().st_mtime)
            except OSError:
                key = (str(cover_path), 0.0)
            pixmap = self._cover_cache.get(key)
            if pixmap is None:
                pixmap = QPixmap(str(cover_path))
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(
                        QSize(168, 168), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    if len(self._cover_cache) >= 8:
                        self._cover_cache.pop(next(iter(self._cover_cache)))
                    self._cover_cache[key] = pixmap
            if pixmap is not None and not pixmap.isNull():
                self._cover.setPixmap(pixmap)
                self._apply_cover_accent(str(cover_path))
                if self._mini is not None:
                    self._mini.set_track(track)
                return
        self._cover.setPixmap(QPixmap())
        self._cover.setText("♪")
        self._apply_cover_accent("")
        if self._mini is not None:
            self._mini.set_track(track)

    def _show_now_page(self) -> None:
        if self._now_page is None:
            self._now_page = NowPlayingPage(self, self._artist_cache_dir)
            self._now_page.play_pause.connect(self._toggle)
            self._now_page.previous_track.connect(self._previous)
            self._now_page.next_track.connect(self._next)
        self._update_now_page()
        if self._now_page is not None:
            self._now_page.set_playing(self._engine.state == EngineState.PLAYING)
        self._now_page.showFullScreen()
        self._now_page.raise_()

    def _update_now_page(self) -> None:
        if self._now_page is None or self._current is None:
            return
        if self._now_page.isVisible():
            self._now_page.set_track(self._current)
        else:
            self._now_page.set_track(self._current)
        self._now_page.set_lyrics([line.text for line in self._lyrics])
        self._now_page.set_position(self._lyrics_index)

    def _load_lyrics(self, track: Track) -> None:
        self._lyrics = []
        self._lyrics_index = -1
        self._lyrics_offset_ms = int(self._lyrics_offsets.get(track.path, 0) or 0)
        self._update_offset_label()
        self._lyrics_view.clear()
        mapped = self._lyrics_map.get(track.path)
        lrc_path = Path(mapped) if mapped and Path(mapped).is_file() else find_lrc(track.path)
        self._current_lrc_path = lrc_path if lrc_path else None
        if not lrc_path:
            self._lyrics_view.addItem("未找到同名 .lrc；可点“关联歌词”手动选择")
            self._update_desktop_lyrics(-1)
            return
        try:
            self._lyrics = load_lrc(lrc_path)
        except Exception as exc:
            self._lyrics_view.addItem(f"歌词读取失败：{exc}")
            return
        for line in self._lyrics:
            self._lyrics_view.addItem(line.text)
        self._update_desktop_lyrics(-1)

    def _update_offset_label(self) -> None:
        if hasattr(self, "_offset_label"):
            self._offset_label.setText(f"偏移 {self._lyrics_offset_ms:+d} ms")

    def _associate_lyrics(self) -> None:
        if self._current is None:
            self._status.showMessage("请先播放一首歌曲")
            return
        path, _ = QFileDialog.getOpenFileName(self, "选择歌词文件", "", "LRC 歌词 (*.lrc);;所有文件 (*.*)")
        if not path:
            return
        self._lyrics_map[self._current.path] = path
        self._config.set("lyrics_map", self._lyrics_map)
        self._load_lyrics(self._current)
        self._status.showMessage(f"已关联歌词：{Path(path).name}")

    def _fetch_online_lyrics(self) -> None:
        if self._current is None:
            self._status.showMessage("请先播放一首歌曲")
            return
        from ..core.online import fetch_lyrics

        target = Path(self._current.path).with_suffix(".lrc")
        if target.exists():
            answer = QMessageBox.question(
                self, "在线歌词", f"{target.name} 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            text = fetch_lyrics(self._current.title, self._current.artist)
        finally:
            QApplication.restoreOverrideCursor()
        if not text:
            self._status.showMessage("未找到在线歌词，或网络不可用")
            return
        try:
            target.write_text(text.rstrip() + "\n", encoding="utf-8")
        except OSError as exc:
            self._status.showMessage(f"歌词保存失败：{exc}")
            return
        self._lyrics_map[self._current.path] = str(target)
        self._config.set("lyrics_map", self._lyrics_map)
        self._load_lyrics(self._current)
        self._status.showMessage(f"已保存在线歌词：{target.name}")

    def _nudge_lyrics_offset(self, delta_ms: int) -> None:
        if self._current is None:
            return
        self._lyrics_offset_ms += int(delta_ms)
        self._lyrics_offsets[self._current.path] = self._lyrics_offset_ms
        self._config.set("lyrics_offsets", self._lyrics_offsets)
        self._update_offset_label()
        self._lyrics_index = -2
        self._tick()

    def _edit_lyrics(self) -> None:
        if self._current is None:
            self._status.showMessage("请先播放一首歌曲")
            return
        path = self._current_lrc_path
        if path is None:
            default = str(Path(self._current.path).with_suffix(".lrc"))
            chosen, _ = QFileDialog.getSaveFileName(self, "新建歌词文件", default, "LRC 歌词 (*.lrc)")
            if not chosen:
                return
            path = Path(chosen)
        if path.exists():
            text = decode_lrc(path.read_bytes())
        else:
            text = "[ti:]\n[ar:]\n[al:]\n[00:00.00]\n"
        dialog = LyricsEditorDialog(path, text, self)
        if dialog.exec() != DIALOG_ACCEPTED:
            return
        self._lyrics_map[self._current.path] = str(path)
        self._config.set("lyrics_map", self._lyrics_map)
        self._current_lrc_path = path
        self._load_lyrics(self._current)
        self._status.showMessage(f"歌词已保存：{path.name}")

    def _toggle(self) -> None:
        if self._current is None:
            if self._playlist.items:
                self._play_playlist_row(self._playlist_view.item(max(0, self._playlist.current_index)))
            return
        if self._engine.state == EngineState.IDLE:
            self._start_track(self._current, max(0, self._playlist.current_index))
            return
        self._engine.toggle()

    def _stop_playback(self) -> None:
        self._radio_station = None
        self._remote_queue = []
        self._remote_queue_index = -1
        self._engine.stop()
        self._progress.setValue(0)
        self._time.setText("00:00 / 00:00")
        if self._radio_window is not None:
            self._radio_window.set_stopped()

    def _next(self) -> None:
        if self._engine.queue:
            self._engine.next()
            return
        item = self._playlist.next()
        if item:
            self._playlist_store.save()
            self._refresh_playlist()
            self._start_track(self._library.get(item.path) or Track(path=item.path, title=item.title))

    def _previous(self) -> None:
        if self._engine.queue:
            self._engine.previous()
            return
        item = self._playlist.previous()
        if item:
            self._playlist_store.save()
            self._refresh_playlist()
            self._start_track(self._library.get(item.path) or Track(path=item.path, title=item.title))

    def _begin_seek(self) -> None:
        self._seeking = True

    def _end_seek(self) -> None:
        self._seeking = False
        duration = self._engine.duration
        if duration > 0:
            self._engine.seek(self._progress.value() / 1000.0 * duration)

    def _seek_relative(self, seconds: float) -> None:
        if self._engine.duration > 0:
            self._engine.seek(max(0.0, min(self._engine.duration, self._engine.position + seconds)))

    def _on_volume(self, value: int) -> None:
        self._engine.volume = value
        if self._mute.isChecked():
            # Unmute without bouncing the value back to the pre-mute level.
            self._mute.blockSignals(True)
            self._mute.setChecked(False)
            self._mute.blockSignals(False)
            self._mute.setText("静音")

    def _nudge_volume(self, delta: int) -> None:
        self._volume.setValue(max(0, min(100, self._volume.value() + delta)))

    def _toggle_mute(self, muted: bool) -> None:
        if muted:
            self._volume_before_mute = self._volume.value()
            self._engine.volume = 0
            self._mute.setText("取消静音")
        else:
            self._engine.volume = self._volume_before_mute
            self._volume.setValue(self._volume_before_mute)
            self._mute.setText("静音")

    def _tick(self) -> None:
        duration = self._engine.duration
        position = self._engine.position
        if duration > 0:
            if not self._seeking:
                self._progress.setValue(int(min(1.0, max(0.0, position / duration)) * 1000))
            self._time.setText(f"{format_time(position)} / {format_time(duration)}")
        if self._lyrics:
            index = line_index_at(self._lyrics, int(position * 1000) - self._lyrics_offset_ms)
            if index != self._lyrics_index:
                self._lyrics_index = index
                self._lyrics_view.setCurrentRow(index)
                if index >= 0:
                    self._lyrics_view.scrollToItem(self._lyrics_view.item(index), QAbstractItemView.PositionAtCenter)
                self._update_desktop_lyrics(index)
                if self._now_page is not None and self._now_page.isVisible():
                    self._now_page.set_position(index)
        if self._current is not None:
            self._scrobbler.tick(
                self._current, position, duration or float(self._current.duration or 0)
            )
        if self._now_page is not None:
            self._now_page.set_playback_position(position)
        if self._radio_station is not None:
            title = self._engine.stream_title
            if title and title != self._radio_stream_title:
                self._radio_stream_title = title
                self._status.showMessage(f"{self._radio_station.name} — {title}")
                if self._radio_window is not None:
                    self._radio_window.set_icy_title(title)

    def _update_desktop_lyrics(self, index: int) -> None:
        if self._desktop_lyrics is None or not self._desktop_lyrics.isVisible():
            return
        current = self._lyrics[index].text if 0 <= index < len(self._lyrics) else "♪"
        upcoming = self._lyrics[index + 1].text if 0 <= index + 1 < len(self._lyrics) else ""
        self._desktop_lyrics.set_lines(current, upcoming)

    # ------------------------------------------------------------------
    # engine events
    # ------------------------------------------------------------------
    def _on_engine_event(self, event: EngineEvent) -> None:
        if event.kind == "state":
            playing = event.value == EngineState.PLAYING
            if playing:
                self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            elif event.value in (EngineState.PAUSED, EngineState.IDLE, EngineState.ERROR):
                self._play_btn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            if self._mini is not None:
                self._mini.set_playing(playing)
            if self._now_page is not None:
                self._now_page.set_playing(playing)
        elif event.kind == "error":
            if self._radio_station is not None and self._radio_retries < 3:
                self._radio_retries += 1
                self._status.showMessage(f"电台断流，{3} 秒后重连（{self._radio_retries}/3）")
                QTimer.singleShot(3000, self._retry_radio)
            else:
                self._status.showMessage(f"播放错误：{event.value}")
        elif event.kind == "eof":
            if self._remote_queue and self._remote_queue_index + 1 < len(self._remote_queue):
                next_index = self._remote_queue_index + 1
                QTimer.singleShot(0, lambda: self._play_remote_queue_at(next_index))
            elif self._radio_station is not None and self._radio_retries < 3:
                self._radio_retries += 1
                QTimer.singleShot(1500, self._retry_radio)
        elif event.kind == "index":
            self._sync_index(int(event.value))

    def _retry_radio(self) -> None:
        station = self._radio_station
        if station is None:
            return
        try:
            self._engine.play(station.url)
            self._status.showMessage(f"正在重连电台：{station.name}")
        except Exception as exc:
            self._status.showMessage(f"重连失败：{exc}")

    def _sync_index(self, index: int) -> None:
        """Follow mpv's own playlist position (gapless transitions)."""
        if self._cue_tracks:
            if 0 <= index < len(self._cue_tracks):
                cue = self._cue_tracks[index]
                track = Track(
                    path=cue.path, title=cue.title, artist=cue.artist,
                    album=self._cue_sheet.title if self._cue_sheet else "", duration=cue.duration,
                    cue_path=str(self._cue_sheet.cue_path) if self._cue_sheet else "",
                    start=cue.start, end=cue.end,
                )
                self._current = track
                self._set_now_playing(track)
                self._lyrics = []
                self._lyrics_view.clear()
                self._update_now_page()
                self._progress.setValue(0)
                self._time.setText("00:00 / 00:00")
                self._status.showMessage(f"CUE：{cue.title}")
            return
        if not (0 <= index < len(self._playlist.items)):
            return
        path = self._playlist.items[index].path
        if self._current is not None and self._current.path == path:
            self._playlist.select(index)
            return
        self._playlist.select(index)
        self._playlist_save_timer.start()
        self._refresh_playlist()
        track = self._library.get(path) or Track(path=path, title=Path(path).stem)
        self._current = track
        self._set_now_playing(track)
        self._load_lyrics(track)
        self._progress.setValue(0)
        self._time.setText("00:00 / 00:00")
        self._status.showMessage(f"正在播放：{track.display}")

    def _show_eq(self) -> None:
        EqualizerDialog(self._engine, self).exec()

    def _show_settings(self) -> None:
        old_theme = str(self._config.get("theme", "dark"))
        old_media_keys = bool(self._config.get("global_media_keys", True))
        dialog = SettingsDialog(self._config, self._engine, self)
        if dialog.exec() != DIALOG_ACCEPTED:
            return
        try:
            self._podcast_cache.limit_bytes = (
                int(self._config.get("podcast_cache_limit_mb", 2048)) * 1024 * 1024
            )
            self._podcast_cache.prune()
        except Exception:
            pass
        self._scrobbler.reload()
        if str(self._config.get("theme", "dark")) != old_theme:
            self._set_theme(str(self._config.get("theme", "dark")))
        new_media_keys = bool(self._config.get("global_media_keys", True))
        if old_media_keys and not new_media_keys and self._media_keys is not None:
            self._media_keys.unregister()
            self._media_keys = None
        elif new_media_keys and not old_media_keys:
            self._init_media_keys()
        self._status.showMessage("设置已保存")

    def _toggle_desktop_lyrics(self, enabled: bool) -> None:
        if enabled:
            if self._desktop_lyrics is None:
                self._desktop_lyrics = DesktopLyricsWindow(self)
                self._desktop_lyrics.closed.connect(lambda: self._desktop_action.setChecked(False))
            self._desktop_lyrics.show_at_default()
            self._update_desktop_lyrics(self._lyrics_index)
        elif self._desktop_lyrics is not None:
            self._desktop_lyrics.hide()

    def _toggle_mini(self, enabled: bool) -> None:
        if enabled:
            if self._mini is None:
                self._mini = MiniPlayer(self)
                self._mini.restore_requested.connect(lambda: self._mini_action.setChecked(False))
            self._mini.set_track(self._current)
            self._mini.set_playing(self._engine.state == EngineState.PLAYING)
            screen = self.screen()
            if screen is not None:
                area = screen.availableGeometry()
                self._mini.move(area.right() - self._mini.width() - 24, area.top() + 24)
            self._mini.show()
            self.hide()
        elif self._mini is not None:
            self._mini.hide()
            self.showNormal()
            self.raise_()

    def _about(self) -> None:
        QMessageBox.about(
            self, "关于浅语影音",
            "浅语影音 0.9（音乐版）\n\n"
            "Copyright (C) 2026 TomJerryGit and QianYu contributors\n"
            "GPL-3.0-only · 不提供任何担保\n\n"
            "libmpv 内核 · 本地音乐库 · 歌词 · 播放列表 · 均衡器\n"
            "在线数据：Radio Browser / iTunes Search / RSS / MusicBrainz / LRCLIB / CAA\n"
            "音频、播客、歌词和封面版权归各自权利方所有。\n\n"
            "https://github.com/TomJerryGit/qianyu",
        )

    def _check_updates(self) -> None:
        from .. import __version__
        from ..update import download_update, fetch_manifest, is_newer

        url = str(self._config.get("update_url", "") or "").strip()
        if not url:
            QMessageBox.information(
                self, "检查更新",
                "尚未配置更新源。\n请在 设置 → 更新源 中填写 manifest.json 地址。",
            )
            return
        public_key = str(self._config.get("update_public_key", "") or "").strip()
        if not public_key:
            answer = QMessageBox.warning(
                self, "未配置签名公钥",
                "尚未配置更新公钥，无法验证 manifest 签名。\n\n"
                "继续只做 SHA-256 校验，可能被中间人替换。是否继续？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            info = fetch_manifest(url, public_key=public_key)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "检查更新失败", f"{type(exc).__name__}: {exc}")
            return
        QApplication.restoreOverrideCursor()
        if not is_newer(__version__, info.version):
            QMessageBox.information(self, "检查更新", f"已是最新版本：{__version__}")
            return
        notes = f"\n\n{info.notes}" if info.notes else ""
        if QMessageBox.question(
            self, "发现新版本",
            f"当前 {__version__}，最新 {info.version}。{notes}\n\n是否下载更新包？",
        ) != QMessageBox.Yes:
            return
        target = Path(tempfile.gettempdir()) / "QianYu-update" / f"QianYu-{info.version}.exe"
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            path = download_update(info, target)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "下载失败", f"{type(exc).__name__}: {exc}")
            return
        QApplication.restoreOverrideCursor()
        run = QMessageBox.question(
            self, "下载完成",
            f"更新包已保存：\n{path}\n\n是否立即退出并运行安装包？\n（未签名，请确认来源可信）",
        )
        if run == QMessageBox.Yes:
            if path.suffix.lower() == ".exe":
                QProcess.startDetached(str(path), [])
                QApplication.quit()
                return
            if path.suffix.lower() == ".ps1":
                QProcess.startDetached("powershell.exe",
                                       ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)])
                QApplication.quit()
                return
        QMessageBox.information(self, "下载完成", f"更新包已保存：\n{path}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))

    def _register_association(self) -> None:
        try:
            from ..platform.windows import register

            register()
        except Exception as exc:
            QMessageBox.warning(self, "注册失败", f"无法写入当前用户的文件关联：\n{exc}")
            return
        QMessageBox.information(
            self, "已注册",
            "已注册音频文件关联。\n\n如需设为默认，请在 Windows 设置 → 应用 → 默认应用 中选择“浅语影音”。",
        )

    def _unregister_association(self) -> None:
        try:
            from ..platform.windows import unregister

            unregister()
        except Exception as exc:
            QMessageBox.warning(self, "取消失败", f"{exc}")
            return
        QMessageBox.information(self, "已取消", "已移除当前用户的文件关联。")

    def open_path(self, path: str) -> None:
        """Open an audio file from CLI / file association."""
        file_path = Path(path)
        if not file_path.is_file():
            return
        suffix = file_path.suffix.lower()
        if suffix in {".mp4", ".mkv", ".ts", ".m2ts", ".avi", ".mov", ".webm", ".flv"}:
            self.open_video(str(file_path))
            return
        track = self._library.get(str(file_path)) or Track(
            path=str(file_path), title=file_path.stem
        )
        if not any(item.path == track.path for item in self._playlist.items):
            self._playlist.add(track.path, track.display)
            self._playlist.select(len(self._playlist.items) - 1)
            self._playlist_store.save()
            self._refresh_playlist()
        else:
            index = next(i for i, item in enumerate(self._playlist.items) if item.path == track.path)
            self._playlist.select(index)
        self._refresh_playlist()
        self._start_track(track, self._playlist.current_index)

    def _open_cue(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "打开 CUE", "", "CUE (*.cue);;所有文件 (*.*)")
        if not path:
            return
        try:
            sheet = parse_cue(path)
        except Exception as exc:
            QMessageBox.warning(self, "CUE 解析失败", f"{type(exc).__name__}: {exc}")
            return
        if not sheet.tracks or not sheet.audio_path:
            QMessageBox.warning(self, "CUE 解析失败", "没有找到音轨或音频文件。")
            return
        dialog = CueDialog(sheet, self)
        dialog.play_requested.connect(lambda index, s=sheet: self._play_cue(s, index))
        dialog.exec()

    def _play_cue_track(self, track: Track) -> None:
        try:
            sheet = parse_cue(track.cue_path)
        except Exception as exc:
            self._status.showMessage(f"CUE 解析失败：{exc}")
            return
        index = 0
        for pos, cue in enumerate(sheet.tracks):
            if abs(cue.start - track.start) < 0.01 and cue.path == track.path.split("#cue:", 1)[0]:
                index = pos
                break
        self._play_cue(sheet, index)

    def _play_cue(self, sheet, index: int) -> None:
        cue = sheet.tracks[max(0, min(index, len(sheet.tracks) - 1))]
        self._cue_tracks = sheet.tracks
        self._cue_sheet = sheet
        track = Track(
            path=cue.path, title=cue.title, artist=cue.artist,
            album=sheet.title, duration=cue.duration,
            cue_path=str(sheet.cue_path), start=cue.start, end=cue.end,
        )
        self._current = track
        self._set_now_playing(track)
        self._lyrics = []
        self._lyrics_view.clear()
        self._update_now_page()
        self._engine.set_queue(
            [item.path for item in sheet.tracks], index,
            ranges=[(item.start, item.end) for item in sheet.tracks],
        )
        self._status.showMessage(f"CUE：{sheet.title} / {cue.title}")

    def _show_unified_search(self) -> None:
        dialog = UnifiedSearchDialog(self._library, self._config, self)
        dialog.play_requested.connect(self._play_unified_result)
        dialog.exec()

    def _play_unified_result(self, result) -> None:
        if isinstance(result, Track):
            if not any(item.path == result.path for item in self._playlist.items):
                self._playlist.add(result.path, result.display)
                self._playlist.select(len(self._playlist.items) - 1)
                self._playlist_store.save()
                self._refresh_playlist()
            self._start_track(result, self._playlist.current_index)
            return
        if isinstance(result, RemoteSong):
            self._play_remote_song(result)
            return
        if isinstance(result, JellyfinItem):
            self._play_jellyfin_item(result)

    def _play_jellyfin_item(self, item: JellyfinItem) -> None:
        client = JellyfinClient(
            str(self._config.get("jellyfin_url", "")),
            str(self._config.get("jellyfin_user", "")),
            self._secrets.get("jellyfin_password"),
            self._secrets.get("jellyfin_token"),
            str(self._config.get("jellyfin_user_id", "")),
        )
        try:
            if not client.token or not client.user_id:
                client.login()
                self._secrets.set("jellyfin_token", client.token)
                self._config.set("jellyfin_user_id", client.user_id)
            url = client.stream_url(item)
        except Exception as exc:
            self._status.showMessage(f"Jellyfin 播放失败：{exc}")
            return
        track = Track(
            path=url,
            title=item.title,
            artist=item.artist,
            album=item.album or "Jellyfin",
            duration=item.duration,
            cover=client.cover_url(item),
        )
        self._play_online_track(track, f"Jellyfin：{item.title}")

    def _show_radio(self) -> None:
        dialog = RadioDialog(self, self._config)
        dialog.play_requested.connect(self._play_radio)
        dialog.exec()

    def _show_radio_window(self) -> None:
        if self._radio_station is None:
            self._show_radio()
            return
        self._ensure_radio_window()
        self._radio_window.show()
        self._radio_window.raise_()

    def _ensure_radio_window(self) -> None:
        if self._radio_window is not None:
            return
        window = RadioWindow(self)
        window.play_requested.connect(self._play_radio)
        window.stop_requested.connect(self._stop_playback)
        window.volume_changed.connect(lambda value: setattr(self._engine, "volume", value))
        window.closed.connect(window.hide)
        self._radio_window = window

    def _radio_presets(self) -> list[RadioStation]:
        result = []
        seen = set()
        for key in ("radio_recent", "radio_favorites"):
            for item in self._config.get(key, []) or []:
                station = RadioStation.from_dict(item)
                if station is not None and station.url not in seen:
                    result.append(station)
                    seen.add(station.url)
        if not result:
            result = preset_stations()
        return result[:6]

    def _show_radio_view(self, station: RadioStation) -> None:
        self._ensure_radio_window()
        self._radio_window.set_presets(self._radio_presets())
        self._radio_window.set_station(station)
        self._radio_window.set_volume(self._engine.volume)
        self._radio_window.show()
        self._radio_window.raise_()

    def _open_stream(self) -> None:
        url, ok = QInputDialog.getText(
            self, "打开网络流", "请输入 HTTP/HTTPS 音频或视频流地址：",
            QLineEdit.Normal, "",
        )
        if not ok:
            return
        url = url.strip()
        if not url.lower().startswith(("http://", "https://")):
            QMessageBox.warning(self, "打开网络流", "只支持 http:// 或 https:// 地址。")
            return
        self._play_radio(RadioStation(name=url, url=url))

    def _show_podcasts(self) -> None:
        dialog = PodcastDialog(self, self._config, self._podcast_cache)
        dialog.play_requested.connect(self._play_episode)
        dialog.exec()

    def _show_remote(self) -> None:
        dialog = RemoteDialog(self._config, self)
        dialog.play_requested.connect(self._play_remote_song)
        dialog.exec()

    def _show_remote_albums(self) -> None:
        dialog = RemoteAlbumDialog(self._config, self)
        dialog.queue_requested.connect(self._play_remote_album)
        dialog.exec()

    def _play_remote_album(self, songs: list, index: int) -> None:
        tracks: list[Track] = []
        subsonic = make_client(self._config)
        jellyfin = None
        for song in songs:
            if isinstance(song, RemoteSong):
                try:
                    url = subsonic.stream_url(song)
                except Exception:
                    continue
                tracks.append(Track(path=url, title=song.title, artist=song.artist,
                                    album=song.album or "远程媒体库",
                                    duration=song.duration,
                                    cover=subsonic.cover_url(song)))
            elif isinstance(song, JellyfinItem):
                if jellyfin is None:
                    jellyfin = JellyfinClient(
                        str(self._config.get("jellyfin_url", "")),
                        str(self._config.get("jellyfin_user", "")),
                        self._secrets.get("jellyfin_password"),
                        self._secrets.get("jellyfin_token"),
                        str(self._config.get("jellyfin_user_id", "")),
                    )
                    try:
                        if not jellyfin.token or not jellyfin.user_id:
                            jellyfin.login()
                            self._secrets.set("jellyfin_token", jellyfin.token)
                            self._config.set("jellyfin_user_id", jellyfin.user_id)
                    except Exception:
                        return
                tracks.append(Track(path=jellyfin.stream_url(song), title=song.title,
                                    artist=song.artist, album=song.album or "Jellyfin",
                                    duration=song.duration,
                                    cover=jellyfin.cover_url(song)))
        if not tracks:
            self._status.showMessage("远程专辑没有可播放曲目")
            return
        self._remote_queue = tracks
        self._play_remote_queue_at(max(0, min(index, len(tracks) - 1)))

    def _play_remote_queue_at(self, index: int) -> None:
        if not (0 <= index < len(self._remote_queue)):
            return
        self._remote_queue_index = index
        track = self._remote_queue[index]
        self._save_podcast_progress()
        self._podcast_url = None
        self._radio_station = None
        self._radio_stream_title = ""
        self._scrobbler.stop()
        self._cue_tracks = None
        self._cue_sheet = None
        self._current = track
        self._set_now_playing(track)
        self._lyrics = []
        self._lyrics_view.clear()
        self._update_now_page()
        self._progress.setValue(0)
        self._time.setText("00:00 / 00:00")
        try:
            self._engine.play(track.path)
        except Exception as exc:
            self._status.showMessage(f"远程播放失败：{exc}")
            return
        self._status.showMessage(f"远程：{track.title}（{index + 1}/{len(self._remote_queue)}）")

    def _play_remote_song(self, song: RemoteSong) -> None:
        client = make_client(self._config)
        try:
            url = client.stream_url(song)
        except Exception as exc:
            self._status.showMessage(f"远程播放失败：{exc}")
            return
        track = Track(
            path=url,
            title=song.title,
            artist=song.artist,
            album=song.album or "远程媒体库",
            duration=song.duration,
            cover=client.cover_url(song),
        )
        self._play_online_track(track, f"远程：{song.title}")

    def _play_episode(self, episode: Episode) -> None:
        cached = self._podcast_cache.get(episode.url)
        track = Track(
            path=str(cached) if cached is not None else episode.url,
            title=episode.title,
            artist=episode.podcast_name,
            album="播客",
            duration=episode.duration or 0.0,
            cover="",
        )
        self._play_online_track(
            track, f"播客：{episode.title}" + ("（缓存）" if cached is not None else "")
        )
        self._podcast_url = episode.url
        played = list(self._config.get("podcast_played", []) or [])
        if episode.url not in played:
            played.append(episode.url)
            self._config.set("podcast_played", played[-500:])
        progress = self._config.get("podcast_progress", {}) or {}
        start = float(progress.get(episode.url, 0) or 0)
        if start > 5:
            QTimer.singleShot(700, lambda: self._resume_podcast(episode.url, start))

    def _resume_podcast(self, url: str, start: float) -> None:
        if self._podcast_url != url:
            return
        try:
            self._engine.seek(start)
            self._status.showMessage(f"从 {format_time(start)} 继续播放")
        except Exception:
            pass

    def _save_podcast_progress(self) -> None:
        url = getattr(self, "_podcast_url", None)
        if not url or self._current is None:
            return
        try:
            position = float(self._engine.position or 0)
        except Exception:
            return
        if position <= 5:
            return
        duration = float(self._current.duration or 0)
        if duration > 0 and position >= duration - 10:
            return
        progress = dict(self._config.get("podcast_progress", {}) or {})
        progress[url] = round(position, 1)
        self._config.set("podcast_progress", progress)

    def _play_radio(self, station: RadioStation) -> None:
        track = Track(
            path=station.url,
            title=station.name,
            artist=station.country,
            album=station.tags,
            duration=0.0,
            cover="",
        )
        self._play_online_track(track, f"网络电台：{station.name}")
        self._radio_station = station
        self._radio_retries = 0
        self._radio_stream_title = ""
        self._show_radio_view(station)

    def _play_online_track(self, track: Track, status: str) -> None:
        if self._radio_window is not None:
            self._radio_window.hide()
        self._remote_queue = []
        self._remote_queue_index = -1
        self._scrobbler.stop()
        self._save_podcast_progress()
        self._podcast_url = None
        self._radio_station = None
        self._radio_stream_title = ""
        self._cue_tracks = None
        self._cue_sheet = None
        self._current = track
        self._set_now_playing(track)
        self._lyrics = []
        self._lyrics_view.clear()
        self._update_now_page()
        self._progress.setValue(0)
        self._time.setText("00:00 / 00:00")
        try:
            self._engine.play(track.path)
        except Exception as exc:
            self._status.showMessage(f"在线播放失败：{exc}")
            return
        self._status.showMessage(status)

    def _open_video_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "打开视频", "", "视频文件 (*.mp4 *.mkv *.ts *.m2ts *.avi *.mov *.webm *.flv);;所有文件 (*.*)"
        )
        if path:
            self.open_video(path)

    def open_video(self, path: str) -> None:
        if self._video is None:
            self._video = VideoWindow(self, self._config)
        self._engine.stop()
        self._video.show()
        self._video.raise_()
        self._video.activateWindow()
        self._video.open_path(path)

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        if self._shutdown_done:
            return
        self._shutdown_done = True
        try:
            self._save_podcast_progress()
            self._config.set("window", {"w": self.width(), "h": self.height()})
            self._config.set("volume", self._volume.value())
            self._playlist_store.save()
        finally:
            self._timer.stop()
            self._engine.shutdown()
            if self._media_keys is not None:
                self._media_keys.unregister()
            if self._desktop_lyrics is not None:
                self._desktop_lyrics.close()
            if self._mini is not None:
                self._mini.close()
            if self._video is not None:
                self._video.close()
            if self._now_page is not None:
                self._now_page.close()
            if self._radio_window is not None:
                self._radio_window.close()

    def closeEvent(self, event) -> None:
        if not self._force_quit and self._tray is not None and bool(self._config.get("close_to_tray", True)):
            self.hide()
            event.ignore()
            return
        self.shutdown()
        super().closeEvent(event)
