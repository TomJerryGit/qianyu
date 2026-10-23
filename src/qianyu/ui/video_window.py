# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""1.0 video mode MVP.

Embedding strategy is the one selected by the spike: mpv renders into a native
child window (`wid`) and Qt controls live *below* the video, never on top of it.
Fullscreen uses mpv's built-in OSC. render API overlays are a 1.2 item.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from ..qt import DIALOG_ACCEPTED, QEvent, QObject, QPoint, QRect, Qt, QTimer, QUrl, pyqtSignal
from ..qt import QKeySequence
from ..qt import (
    QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QMainWindow, QMenu, QMessageBox, QPushButton, QShortcut, QSlider,
    QStyle, QVBoxLayout, QWidget,
)

from ..config import Config
from ..engine import _loader  # noqa: F401  (set PATH before importing mpv)
import mpv
from .video_gesture import GestureOverlay
from .video_style_dialog import (
    ColorAdjustDialog, DEFAULT_COLOR, DEFAULT_HDR, DEFAULT_SUBTITLE, HdrDialog,
    SubtitleStyleDialog,
)

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".ts", ".m2ts", ".avi", ".mov", ".webm", ".flv"}


class VideoBridge(QObject):
    event = pyqtSignal(str, object)


def _fmt(seconds: float) -> str:
    seconds = max(0, int(seconds or 0))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:02d}:{sec:02d}"


class VideoWindow(QMainWindow):
    def __init__(self, parent=None, config: Config | None = None, ao: str = "auto"):
        super().__init__(parent)
        self._config = config or Config()
        self._ao = ao
        self._bridge = VideoBridge()
        self._bridge.event.connect(self._on_event)
        self._player = None
        self._duration = 0.0
        self._seeking = False
        self._pending_start = 0.0
        self._fullscreen = False
        self._gesture_overlay: GestureOverlay | None = None
        self._gesture_enabled = bool(self._config.get("video_gesture_overlay", True))
        self._gesture_windowed = bool(self._config.get("video_gesture_windowed", False))
        self._last_path = ""
        raw_resume = self._config.get("video_resume", {}) or {}
        raw_bookmarks = self._config.get("video_bookmarks", {}) or {}
        self._resume = dict(raw_resume) if isinstance(raw_resume, dict) else {}
        self._bookmarks = dict(raw_bookmarks) if isinstance(raw_bookmarks, dict) else {}
        self._queue: list[str] = []
        self._queue_index = -1
        self._chapters: list[dict] = []
        self._subtitle_style = {**DEFAULT_SUBTITLE,
                                **dict(self._config.get("subtitle_style", {}) or {})}
        self._color = {**DEFAULT_COLOR, **dict(self._config.get("video_color", {}) or {})}
        self._hdr = {**DEFAULT_HDR, **dict(self._config.get("video_hdr", {}) or {})}
        self._audio_delay = float(self._config.get("audio_delay", 0.0) or 0.0)
        self._tick_count = 0
        self._shortcuts = []
        self._build_ui()
        self._bind_shortcuts()
        self.setWindowTitle("浅语影音 · 视频")
        self.resize(1280, 760)
        self.setAcceptDrops(True)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._surface = QWidget()
        self._surface.setAttribute(Qt.WA_NativeWindow, True)
        self._surface.setStyleSheet("background:#000;")
        self._surface.setMinimumSize(640, 360)
        self._surface.mouseDoubleClickEvent = self._surface_double_click
        layout.addWidget(self._surface, 1)

        self._controls = QWidget()
        self._controls.setObjectName("videoControls")
        bar = QHBoxLayout(self._controls)
        bar.setContentsMargins(8, 6, 8, 6)
        bar.setSpacing(4)

        self._open_btn = self._btn("打开", self._open_dialog)
        self._url_btn = self._btn("URL", self._open_url_dialog)
        self._prev_btn = self._btn_icon(QStyle.SP_MediaSkipBackward, "上一段")
        self._play_btn = self._btn_icon(QStyle.SP_MediaPlay, "播放/暂停")
        self._stop_btn = self._btn_icon(QStyle.SP_MediaStop, "停止")
        self._next_btn = self._btn_icon(QStyle.SP_MediaSkipForward, "下一段")
        self._prev_btn.clicked.connect(self._previous_video)
        self._play_btn.clicked.connect(self.toggle)
        self._stop_btn.clicked.connect(self.stop)
        self._next_btn.clicked.connect(lambda: self._next_video())
        for button in (self._open_btn, self._url_btn, self._prev_btn, self._play_btn, self._stop_btn, self._next_btn):
            bar.addWidget(button)
        bar.addWidget(self._vline())

        self._progress = QSlider(Qt.Horizontal)
        self._progress.setRange(0, 1000)
        self._progress.sliderPressed.connect(self._begin_seek)
        self._progress.sliderReleased.connect(self._end_seek)
        bar.addWidget(self._progress, 1)
        self._time = QLabel("00:00 / 00:00")
        bar.addWidget(self._time)

        self._speed_combo = QComboBox()
        self._speed_combo.setMaximumWidth(72)
        for label, value in (("0.5×", 0.5), ("0.75×", 0.75), ("1.0×", 1.0),
                             ("1.25×", 1.25), ("1.5×", 1.5), ("2.0×", 2.0)):
            self._speed_combo.addItem(label, value)
        speed = float(self._config.get("video_speed", 1.0))
        index = self._speed_combo.findData(speed)
        self._speed_combo.setCurrentIndex(index if index >= 0 else 2)
        self._speed_combo.currentIndexChanged.connect(self._speed_changed)
        bar.addWidget(self._speed_combo)
        bar.addWidget(self._vline())

        self._volume = QSlider(Qt.Horizontal)
        self._volume.setRange(0, 100)
        self._volume.setValue(int(self._config.get("volume", 70)))
        self._volume.setMaximumWidth(100)
        self._volume.valueChanged.connect(self._on_volume)
        bar.addWidget(self._volume)
        self._mute = QPushButton("静音")
        self._mute.setCheckable(True)
        self._mute.toggled.connect(self._on_mute)
        bar.addWidget(self._mute)
        bar.addWidget(self._vline())

        self._sub_btn = self._btn("字幕", lambda: self._subtitle_menu())
        bar.addWidget(self._sub_btn)
        self._audio_combo = QComboBox()
        self._audio_combo.setMinimumWidth(110)
        self._audio_combo.currentIndexChanged.connect(self._audio_changed)
        bar.addWidget(self._audio_combo)
        self._sub_combo = QComboBox()
        self._sub_combo.setMinimumWidth(110)
        self._sub_combo.currentIndexChanged.connect(self._sub_changed)
        bar.addWidget(self._sub_combo)

        self._chapter_combo = QComboBox()
        self._chapter_combo.setMinimumWidth(120)
        self._chapter_combo.setVisible(False)
        self._chapter_combo.currentIndexChanged.connect(self._chapter_changed)
        bar.addWidget(self._chapter_combo)
        bar.addWidget(self._vline())

        self._book_btn = self._btn("书签", lambda: self._bookmark_menu())
        bar.addWidget(self._book_btn)
        self._audio_btn = self._btn("音频", lambda: self._audio_menu())
        bar.addWidget(self._audio_btn)
        self._picture_btn = self._btn("画面", lambda: self._picture_menu())
        bar.addWidget(self._picture_btn)
        self._shot_btn = self._btn("截图", self.screenshot)
        self._full_btn = self._btn("全屏", self.toggle_fullscreen)
        bar.addWidget(self._shot_btn)
        bar.addWidget(self._full_btn)
        layout.addWidget(self._controls)

        self._status = self.statusBar()
        self._status.showMessage("打开视频文件，或拖入窗口")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(200)

    def _btn(self, text, slot):
        button = QPushButton(text)
        button.clicked.connect(slot)
        return button

    @staticmethod
    def _vline() -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFixedWidth(1)
        line.setStyleSheet("color:#2f3650; background:#2f3650;")
        return line

    def _btn_icon(self, icon, tip):
        button = QPushButton(self.style().standardIcon(icon), "")
        button.setToolTip(tip)
        button.setFixedSize(34, 28)
        return button

    def _bind_shortcuts(self) -> None:
        def bind(sequence, slot):
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(slot)
            self._shortcuts.append(shortcut)

        bind("Space", self.toggle)
        bind("F", self.toggle_fullscreen)
        bind("Escape", self._escape)
        bind("S", self.screenshot)
        bind("Left", lambda: self._seek_relative(-5))
        bind("Right", lambda: self._seek_relative(5))
        bind("[", lambda: self._adjust_speed(-1))
        bind("]", lambda: self._adjust_speed(1))
        bind(",", lambda: self._frame_step(False))
        bind(".", lambda: self._frame_step(True))
        bind("A", self._set_ab_a)
        bind("B", self._set_ab_b)
        bind("Shift+A", self._clear_ab)

    # ------------------------------------------------------------------
    # player
    # ------------------------------------------------------------------
    def _ensure_player(self) -> bool:
        if self._player is not None:
            return True
        try:
            hwnd = int(self._surface.winId())
            self._player = mpv.MPV(
                wid=str(hwnd), vo="gpu-next", gpu_api="d3d11", hwdec="auto-safe",
                video_sync="display-resample", ao=self._ao,
                volume=int(self._config.get("volume", 70)), keep_open="yes",
                osc="no", input_default_bindings="yes", input_vo_keyboard="no",
                idle="yes",
                speed=float(self._config.get("video_speed", 1.0)),
            )
            self._observe()
            self._apply_subtitle_style()
            self._apply_color()
            self._apply_hdr()
            self._apply_audio_delay()
            return True
        except Exception as exc:
            QMessageBox.critical(self, "视频引擎失败", f"{type(exc).__name__}: {exc}")
            self._player = None
            return False

    def _observe(self) -> None:
        player = self._player

        @player.property_observer("time-pos")
        def _pos(_name, value):
            if value is not None:
                self._bridge.event.emit("position", float(value))

        @player.property_observer("duration")
        def _dur(_name, value):
            if value is not None:
                self._bridge.event.emit("duration", float(value))

        @player.property_observer("pause")
        def _pause(_name, value):
            self._bridge.event.emit("pause", bool(value))

        @player.property_observer("track-list")
        def _tracks(_name, value):
            self._bridge.event.emit("tracks", value)

        @player.property_observer("chapter-list")
        def _chapters(_name, value):
            self._bridge.event.emit("chapters", value)

        @player.property_observer("media-title")
        def _title(_name, value):
            if value:
                self._bridge.event.emit("title", str(value))

        @player.property_observer("eof-reached")
        def _eof(_name, value):
            if value:
                self._bridge.event.emit("eof", None)

    def open_path(self, path: str, queue: list[str] | None = None) -> None:
        if not self._ensure_player():
            return
        path = str(path)
        if queue is None:
            queue = self._folder_queue(path)
        self._queue = [str(item) for item in queue]
        if path in self._queue:
            self._queue_index = self._queue.index(path)
        else:
            self._queue.append(path)
            self._queue_index = len(self._queue) - 1
        self._open_current()

    @staticmethod
    def _folder_queue(path: str) -> list[str]:
        if "://" in path:
            return [path]
        file_path = Path(path)
        if not file_path.is_file():
            return [path]
        try:
            files = [
                str(item) for item in file_path.parent.iterdir()
                if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS
            ]
        except OSError:
            return [path]
        files.sort(key=lambda value: [int(part) if part.isdigit() else part.lower()
                                      for part in re.split(r"(\d+)", Path(value).name)])
        return files or [path]

    @staticmethod
    def _display_name(path: str) -> str:
        return path.rsplit("/", 1)[-1] if "://" in path else Path(path).name

    def _open_current(self) -> None:
        if not (0 <= self._queue_index < len(self._queue)):
            return
        path = self._queue[self._queue_index]
        self._last_path = path
        self._duration = 0.0
        self.setWindowTitle(f"浅语影音 · {self._display_name(path)}")
        start = float(self._resume.get(path, 0) or 0)
        self._pending_start = start if start > 5 else 0.0
        try:
            self._player.command("loadfile", path, "replace")
            self._status.showMessage(
                f"正在打开：{self._display_name(path)}  ({self._queue_index + 1}/{len(self._queue)})"
            )
            self._surface.setFocus()
        except Exception as exc:
            self._status.showMessage(f"打开失败：{exc}")

    def _next_video(self, auto: bool = False) -> bool:
        if not self._queue:
            return False
        self._save_resume()
        if self._queue_index + 1 < len(self._queue):
            self._queue_index += 1
            self._open_current()
            return True
        if auto:
            self._status.showMessage("播放队列结束")
        return False

    def _previous_video(self) -> None:
        if not self._queue:
            return
        self._save_resume()
        if self._queue_index > 0:
            self._queue_index -= 1
            self._open_current()

    def _open_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "打开视频", "", "视频文件 (*.mp4 *.mkv *.ts *.m2ts *.avi *.mov *.webm *.flv);;所有文件 (*.*)"
        )
        if path:
            self.open_path(path)

    def _open_url_dialog(self) -> None:
        url, ok = QInputDialog.getText(self, "打开 URL", "视频/流地址：")
        if ok and url.strip():
            self.open_path(url.strip())

    def toggle(self) -> None:
        if self._player is None:
            self._open_dialog()
            return
        try:
            self._player.pause = not bool(self._player.pause)
        except Exception:
            pass

    def stop(self) -> None:
        if self._player is not None:
            try:
                self._player.command("stop")
            except Exception:
                pass
        self._progress.setValue(0)
        self._time.setText("00:00 / 00:00")

    def _seek_relative(self, delta: float) -> None:
        duration = self._duration or (float(self._player.duration or 0) if self._player else 0.0)
        if self._player is None or duration <= 0:
            return
        pos = max(0.0, min(duration, float(self._player.time_pos or 0) + delta))
        try:
            self._player.command("seek", pos, "absolute")
        except Exception as exc:
            self._status.showMessage(f"跳转失败：{exc}")

    def _begin_seek(self) -> None:
        self._seeking = True

    def _end_seek(self) -> None:
        self._seeking = False
        if self._player is None:
            return
        duration = self._duration or float(self._player.duration or 0)
        if duration > 0:
            try:
                self._player.command("seek", self._progress.value() / 1000.0 * duration, "absolute")
            except Exception as exc:
                self._status.showMessage(f"跳转失败：{exc}")

    def _on_volume(self, value: int) -> None:
        if self._player is not None:
            try:
                self._player.volume = int(value)
            except Exception:
                pass

    def _on_mute(self, muted: bool) -> None:
        if self._player is not None:
            try:
                self._player.mute = bool(muted)
            except Exception:
                pass

    def _speed_changed(self, _index: int) -> None:
        speed = float(self._speed_combo.currentData() or 1.0)
        if self._player is not None:
            try:
                self._player.speed = speed
            except Exception:
                pass
        self._config.set("video_speed", speed)
        self._osd(f"速度 {speed:.2f}×")

    def _adjust_speed(self, delta: int) -> None:
        index = max(0, min(self._speed_combo.count() - 1, self._speed_combo.currentIndex() + delta))
        if index != self._speed_combo.currentIndex():
            self._speed_combo.setCurrentIndex(index)

    def _picture_menu(self) -> None:
        menu = QMenu(self)
        aspect = menu.addMenu("画面比例")
        for label, value in (("自动", "no"), ("16:9", "16:9"), ("4:3", "4:3"),
                             ("2.35:1", "2.35:1"), ("1:1", "1:1")):
            action = aspect.addAction(label)
            action.triggered.connect(lambda checked=False, v=value: self._set_aspect(v))
        rotate = menu.addMenu("旋转")
        for label, degrees in (("0°", 0), ("90°", 90), ("180°", 180), ("270°", 270)):
            action = rotate.addAction(label)
            action.triggered.connect(lambda checked=False, d=degrees: self._set_rotate(d))
        deinterlace = menu.addAction("去隔行")
        deinterlace.setCheckable(True)
        try:
            deinterlace.setChecked(bool(self._player.deinterlace) if self._player else False)
        except Exception:
            deinterlace.setChecked(False)
        deinterlace.triggered.connect(self._set_deinterlace)
        menu.addSeparator()
        menu.addAction("色彩调整…", self._edit_color)
        menu.addAction("HDR 色调映射…", self._edit_hdr)
        gesture = menu.addAction("窗口手势层")
        gesture.setCheckable(True)
        gesture.setChecked(self._gesture_windowed)
        gesture.triggered.connect(self._set_windowed_gesture)
        menu.addSeparator()
        menu.addAction("上一帧  (,) ", lambda: self._frame_step(False))
        menu.addAction("下一帧  (.) ", lambda: self._frame_step(True))
        menu.addSeparator()
        menu.addAction("设置 A 点  (A)", self._set_ab_a)
        menu.addAction("设置 B 点  (B)", self._set_ab_b)
        menu.addAction("清除 A-B  (Shift+A)", self._clear_ab)
        menu.exec_(self._picture_btn.mapToGlobal(self._picture_btn.rect().bottomLeft()))

    def _set_aspect(self, value: str) -> None:
        if self._player is None:
            return
        try:
            self._player.command("set", "video-aspect-override", value)
            self._status.showMessage("画面比例：" + ("自动" if value == "no" else value))
            self._osd("画面比例：" + ("自动" if value == "no" else value))
        except Exception as exc:
            self._status.showMessage(f"比例设置失败：{exc}")

    def _set_rotate(self, degrees: int) -> None:
        if self._player is None:
            return
        try:
            self._player.command("set", "video-rotate", str(int(degrees)))
            self._status.showMessage(f"旋转：{degrees}°")
            self._osd(f"旋转：{degrees}°")
        except Exception as exc:
            self._status.showMessage(f"旋转设置失败：{exc}")

    def _set_deinterlace(self, enabled: bool) -> None:
        if self._player is None:
            return
        try:
            self._player.command("set", "deinterlace", "yes" if enabled else "no")
            self._status.showMessage("去隔行：" + ("开" if enabled else "关"))
            self._osd("去隔行：" + ("开" if enabled else "关"))
        except Exception as exc:
            self._status.showMessage(f"去隔行设置失败：{exc}")

    def _frame_step(self, forward: bool) -> None:
        if self._player is None:
            return
        try:
            self._player.command("frame-step" if forward else "frame-back-step")
            self._osd(f"帧 {float(self._player.time_pos or 0):.3f}")
        except Exception as exc:
            self._status.showMessage(f"逐帧失败：{exc}")

    def _set_ab_a(self) -> None:
        if self._player is None:
            return
        position = float(self._player.time_pos or 0)
        try:
            self._player.command("set", "ab-loop-a", str(position))
            self._status.showMessage(f"A 点：{_fmt(position)}")
            self._osd(f"A 点：{_fmt(position)}")
        except Exception as exc:
            self._status.showMessage(f"设置 A 点失败：{exc}")

    def _set_ab_b(self) -> None:
        if self._player is None:
            return
        position = float(self._player.time_pos or 0)
        try:
            self._player.command("set", "ab-loop-b", str(position))
            self._status.showMessage(f"B 点：{_fmt(position)}")
            self._osd(f"B 点：{_fmt(position)}")
        except Exception as exc:
            self._status.showMessage(f"设置 B 点失败：{exc}")

    def _clear_ab(self) -> None:
        if self._player is None:
            return
        try:
            self._player.command("set", "ab-loop-a", "no")
            self._player.command("set", "ab-loop-b", "no")
            self._status.showMessage("已清除 A-B")
            self._osd("已清除 A-B")
        except Exception as exc:
            self._status.showMessage(f"清除 A-B 失败：{exc}")

    def _subtitle_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction("加载字幕…", self._load_subtitle)
        menu.addAction("字幕样式…", self._edit_subtitle_style)
        menu.addSeparator()
        menu.addAction("延迟 +0.5 s", lambda: self._adjust_sub_delay(0.5))
        menu.addAction("延迟 -0.5 s", lambda: self._adjust_sub_delay(-0.5))
        menu.addAction("隐藏字幕", self._hide_subtitles)
        menu.exec_(self._sub_btn.mapToGlobal(self._sub_btn.rect().bottomLeft()))

    def _edit_subtitle_style(self) -> None:
        dialog = SubtitleStyleDialog(self._subtitle_style, self)
        if dialog.exec() != DIALOG_ACCEPTED:
            return
        self._subtitle_style.update(dialog.values())
        self._config.set("subtitle_style", self._subtitle_style)
        self._apply_subtitle_style()
        self._status.showMessage("字幕样式已保存")

    def _apply_subtitle_style(self) -> None:
        if self._player is None:
            return
        style = self._subtitle_style
        try:
            self._player.command("set", "sub-font", str(style.get("font", "Microsoft YaHei")))
            self._player.command("set", "sub-font-size", str(int(style.get("size", 36))))
            self._player.command("set", "sub-color", str(style.get("color", "#FFFFFF")))
            self._player.command("set", "sub-border-size", str(float(style.get("border", 2.0))))
            self._player.command("set", "sub-delay", str(float(style.get("delay", 0.0))))
            self._player.command("set", "sub-align-y", str(style.get("position", "bottom")))
            self._player.command("set", "sub-bold", "yes" if style.get("bold") else "no")
            self._player.command("set", "sub-italic", "yes" if style.get("italic") else "no")
            self._player.command("set", "sub-codepage", str(style.get("codepage", "auto")))
            self._player.command("set", "sub-ass-override", "scale")
        except Exception:
            pass

    def _adjust_sub_delay(self, delta: float) -> None:
        self._subtitle_style["delay"] = round(float(self._subtitle_style.get("delay", 0.0)) + delta, 1)
        self._config.set("subtitle_style", self._subtitle_style)
        if self._player is not None:
            try:
                self._player.command("set", "sub-delay", str(self._subtitle_style["delay"]))
            except Exception:
                pass
        self._status.showMessage(f"字幕延迟：{self._subtitle_style['delay']:+.1f} s")
        self._osd(f"字幕延迟 {self._subtitle_style['delay']:+.1f} s")

    def _hide_subtitles(self) -> None:
        if self._player is not None:
            try:
                self._player.command("set", "sid", "no")
            except Exception:
                pass

    def _audio_menu(self) -> None:
        menu = QMenu(self)
        menu.addAction("音频延迟 +0.1 s", lambda: self._adjust_audio_delay(0.1))
        menu.addAction("音频延迟 -0.1 s", lambda: self._adjust_audio_delay(-0.1))
        menu.addAction("重置音频延迟", lambda: self._adjust_audio_delay(-self._audio_delay))
        menu.exec_(self._audio_btn.mapToGlobal(self._audio_btn.rect().bottomLeft()))

    def _set_windowed_gesture(self, enabled: bool) -> None:
        self._gesture_windowed = bool(enabled)
        self._config.set("video_gesture_windowed", self._gesture_windowed)
        if not self._gesture_windowed and self._gesture_overlay is not None:
            self._gesture_overlay.hide()
        else:
            self._sync_windowed_overlay()

    def _adjust_audio_delay(self, delta: float) -> None:
        self._audio_delay = round(self._audio_delay + delta, 2)
        self._apply_audio_delay()
        self._config.set("audio_delay", self._audio_delay)
        self._status.showMessage(f"音频延迟：{self._audio_delay:+.2f} s")
        self._osd(f"音频延迟 {self._audio_delay:+.2f} s")

    def _apply_audio_delay(self) -> None:
        if self._player is None:
            return
        try:
            self._player.command("set", "audio-delay", str(self._audio_delay))
        except Exception:
            pass

    def _edit_color(self) -> None:
        dialog = ColorAdjustDialog(self._color, self)
        if dialog.exec() != DIALOG_ACCEPTED:
            return
        self._color.update(dialog.values())
        self._config.set("video_color", self._color)
        self._apply_color()
        self._status.showMessage("色彩调整已保存")

    def _apply_color(self) -> None:
        if self._player is None:
            return
        for key in ("brightness", "contrast", "saturation", "gamma"):
            try:
                self._player.command("set", key, str(int(self._color.get(key, 0))))
            except Exception:
                pass

    def _edit_hdr(self) -> None:
        dialog = HdrDialog(self._hdr, self)
        if dialog.exec() != DIALOG_ACCEPTED:
            return
        self._hdr.update(dialog.values())
        self._config.set("video_hdr", self._hdr)
        self._apply_hdr()
        self._status.showMessage("HDR 映射设置已保存（下一个文件生效更可靠）")

    def _apply_hdr(self) -> None:
        if self._player is None:
            return
        try:
            self._player.command("set", "tone-mapping", str(self._hdr.get("tone_mapping", "bt.2390")))
            self._player.command("set", "target-peak", str(self._hdr.get("target_peak", "auto")))
            self._player.command("set", "hdr-compute-peak",
                                 "yes" if self._hdr.get("compute_peak", True) else "no")
            self._player.command("set", "target-colorspace-hint",
                                 "yes" if self._hdr.get("target_hint", True) else "no")
        except Exception:
            pass

    def _osd(self, text: str) -> None:
        if self._player is None:
            return
        try:
            self._player.command("show-text", text, "1500")
        except Exception:
            pass

    def _load_subtitle(self) -> None:
        if self._player is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "加载字幕", "", "字幕 (*.srt *.ass *.ssa *.sup);;所有文件 (*.*)"
        )
        if path:
            try:
                self._player.sub_add(path)
                self._status.showMessage(f"已加载字幕：{Path(path).name}")
            except Exception as exc:
                self._status.showMessage(f"字幕加载失败：{exc}")

    def _audio_changed(self, _index: int) -> None:
        if self._player is None:
            return
        value = self._audio_combo.currentData()
        if value is not None:
            try:
                self._player.aid = value
            except Exception:
                pass

    def _sub_changed(self, _index: int) -> None:
        if self._player is None:
            return
        value = self._sub_combo.currentData()
        if value is not None:
            try:
                self._player.sid = value
            except Exception:
                pass

    def screenshot(self) -> str:
        if self._player is None:
            return ""
        folder = Path.home() / "Pictures" / "QianYu"
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            import tempfile

            folder = Path(tempfile.mkdtemp(prefix="qianyu-shot-"))
        target = folder / f"qianyu-{time.strftime('%Y%m%d-%H%M%S')}.png"
        try:
            self._player.command("screenshot-to-file", str(target), "subtitles")
            self._status.showMessage(f"截图：{target}")
            return str(target)
        except Exception as exc:
            self._status.showMessage(f"截图失败：{exc}")
            return ""

    def _surface_double_click(self, event) -> None:
        self.toggle_fullscreen()
        event.accept()

    def toggle_fullscreen(self) -> None:
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            if self._gesture_overlay is not None:
                self._gesture_overlay.close()
                self._gesture_overlay = None
            self._controls.hide()
            self.statusBar().hide()
            self.showFullScreen()
            if self._gesture_enabled:
                self._gesture_overlay = GestureOverlay(self)
                self._gesture_overlay.show_overlay()
            if self._player is not None:
                try:
                    self._player.osc = not self._gesture_enabled
                except Exception:
                    pass
        else:
            if self._gesture_overlay is not None:
                self._gesture_overlay.close()
                self._gesture_overlay.deleteLater()
                self._gesture_overlay = None
            self._controls.show()
            self.statusBar().show()
            self.showNormal()
            if self._player is not None:
                try:
                    self._player.osc = False
                except Exception:
                    pass
            self._sync_windowed_overlay()

    def _escape(self) -> None:
        if self._fullscreen:
            self.toggle_fullscreen()
        else:
            self.close()

    # ------------------------------------------------------------------
    # events
    # ------------------------------------------------------------------
    def _on_event(self, kind: str, value) -> None:
        if kind == "position":
            self._apply_pending_start()
            if not self._seeking and self._duration > 0:
                self._progress.setValue(int(max(0.0, min(1.0, value / self._duration)) * 1000))
            self._time.setText(f"{_fmt(value)} / {_fmt(self._duration)}")
        elif kind == "duration":
            self._duration = float(value or 0)
            self._apply_pending_start()
        elif kind == "pause":
            icon = QStyle.SP_MediaPause if not value else QStyle.SP_MediaPlay
            self._play_btn.setIcon(self.style().standardIcon(icon))
        elif kind == "tracks":
            self._update_tracks(value or [])
        elif kind == "chapters":
            self._set_chapters(value or [])
        elif kind == "title":
            self.setWindowTitle(f"浅语影音 · {value}")
        elif kind == "eof":
            self._save_resume()
            self._next_video(auto=True)

    def _apply_pending_start(self) -> None:
        if self._pending_start <= 0 or self._player is None:
            return
        try:
            duration = float(self._player.duration or 0)
            if duration <= 0:
                return
            target = min(self._pending_start, max(0.0, duration - 1.0))
            self._player.command("seek", target, "absolute")
        except Exception:
            return
        self._pending_start = 0.0

    def _update_tracks(self, tracks) -> None:
        audio = [t for t in tracks if t.get("type") == "audio"]
        subs = [t for t in tracks if t.get("type") == "sub"]
        self._fill_combo(self._audio_combo, audio, "音轨")
        self._fill_combo(self._sub_combo, subs, "字幕")

    def _set_chapters(self, chapters) -> None:
        self._chapters = [dict(item) for item in chapters if item.get("time") is not None]
        self._chapter_combo.blockSignals(True)
        self._chapter_combo.clear()
        for index, chapter in enumerate(self._chapters):
            title = chapter.get("title") or f"章节 {index + 1}"
            self._chapter_combo.addItem(f"{_fmt(chapter['time'])}  {title}", float(chapter["time"]))
        self._chapter_combo.blockSignals(False)
        self._chapter_combo.setVisible(bool(self._chapters))

    def _chapter_changed(self, _index: int) -> None:
        if self._player is None:
            return
        value = self._chapter_combo.currentData()
        if value is not None:
            try:
                self._player.command("seek", float(value), "absolute")
            except Exception:
                pass

    def _bookmark_menu(self) -> None:
        if self._player is None or not self._last_path:
            return
        menu = QMenu(self)
        menu.addAction("添加当前书签…", self._add_bookmark)
        items = self._bookmarks.get(self._last_path, []) or []
        if items:
            menu.addSeparator()
            for item in items:
                label = item.get("label") or "书签"
                menu.addAction(f"{_fmt(item.get('pos', 0))}  {label}",
                               lambda checked=False, pos=item.get("pos", 0): self._jump_bookmark(pos))
            menu.addSeparator()
            menu.addAction("清除本书签", self._clear_bookmarks)
        menu.exec_(self._book_btn.mapToGlobal(self._book_btn.rect().bottomLeft()))

    def _add_bookmark(self) -> None:
        if self._player is None or not self._last_path:
            return
        position = float(self._player.time_pos or 0)
        label, ok = QInputDialog.getText(self, "添加书签", "名称：")
        if not ok:
            return
        items = self._bookmarks.setdefault(self._last_path, [])
        items.append({"pos": round(position, 1), "label": label.strip()})
        items.sort(key=lambda item: item["pos"])
        self._config.set("video_bookmarks", self._bookmarks)
        self._status.showMessage(f"已添加书签：{label or _fmt(position)}")

    def _jump_bookmark(self, position) -> None:
        if self._player is not None:
            try:
                self._player.command("seek", float(position), "absolute")
            except Exception:
                pass

    def _clear_bookmarks(self) -> None:
        if self._last_path in self._bookmarks:
            self._bookmarks.pop(self._last_path, None)
            self._config.set("video_bookmarks", self._bookmarks)
            self._status.showMessage("已清除本书签")

    @staticmethod
    def _fill_combo(combo: QComboBox, tracks, prefix: str) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(f"{prefix}：自动", "auto")
        for track in tracks:
            label = track.get("title") or track.get("lang") or f"#{track.get('id')}"
            combo.addItem(str(label), track.get("id"))
        combo.blockSignals(False)

    def _tick(self) -> None:
        self._tick_count += 1
        if self._player is not None:
            if self._duration <= 0:
                try:
                    self._duration = float(self._player.duration or 0)
                except Exception:
                    pass
            if self._tick_count % 15 == 0:
                self._save_resume()

    def _save_resume(self) -> None:
        if self._player is None or not self._last_path:
            return
        try:
            position = float(self._player.time_pos or 0)
            duration = float(self._player.duration or 0)
        except Exception:
            return
        if position > 5 and (duration <= 0 or position < duration - 5):
            self._resume[self._last_path] = round(position, 1)
        elif self._last_path in self._resume:
            self._resume.pop(self._last_path, None)
        if self._resume != (self._config.get("video_resume", {}) or {}):
            self._config.set("video_resume", self._resume)

    # ------------------------------------------------------------------
    # drag & drop / close
    # ------------------------------------------------------------------
    def _ensure_gesture_overlay(self) -> GestureOverlay:
        if self._gesture_overlay is None:
            self._gesture_overlay = GestureOverlay(self)
        return self._gesture_overlay

    def _sync_windowed_overlay(self) -> None:
        if not self._gesture_windowed or not self._gesture_enabled or self._fullscreen:
            return
        if (not self.isVisible() or self.isMinimized() or not self.isActiveWindow()):
            if self._gesture_overlay is not None:
                self._gesture_overlay.hide()
            return
        overlay = self._ensure_gesture_overlay()
        top_left = self._surface.mapToGlobal(QPoint(0, 0))
        overlay.show_at(QRect(top_left, self._surface.size()))

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._sync_windowed_overlay()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_windowed_overlay()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._sync_windowed_overlay)

    def hideEvent(self, event) -> None:
        if self._gesture_overlay is not None:
            self._gesture_overlay.hide()
        super().hideEvent(event)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange:
            self._sync_windowed_overlay()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.open_path(url.toLocalFile())
                break
            if url.scheme() in ("http", "https", "rtsp", "rtmp"):
                self.open_path(url.toString())
                break

    def closeEvent(self, event) -> None:
        self._save_resume()
        self._timer.stop()
        if self._gesture_overlay is not None:
            self._gesture_overlay.close()
            self._gesture_overlay = None
        if self._player is not None:
            try:
                self._player.terminate()
            except Exception:
                pass
            self._player = None
        super().closeEvent(event)
