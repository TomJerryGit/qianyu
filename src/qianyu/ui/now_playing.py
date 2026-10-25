# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Full-screen now-playing page with large cover, lyrics and blurred backdrop."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..qt import (
    QGraphicsBlurEffect, QHBoxLayout, QLabel, QListWidget, QPixmap, QPushButton,
    QSize, QThread, QVBoxLayout, QWidget, Qt, pyqtSignal,
)
from ..core.models import Track
from ..core.artist_image import fetch_artist_image
from ..core.cover_cache import fetch_cover
from ..core.spectrum_analyzer import SAMPLE_RATE, analyze_pcm
from ..core.wasapi_loopback import WasapiLoopback
from .spectrum import SpectrumWidget


class SpectrumAnalyzerThread(QThread):
    analysed = pyqtSignal(list)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self._path = path

    def run(self) -> None:
        from ..core.spectrum_analyzer import analyze_file

        frames = analyze_file(self._path, cancelled=self.isInterruptionRequested)
        self.analysed.emit(frames)


class StreamSpectrumThread(QThread):
    """Decode a local file or remote stream with FFmpeg, progressively.

    Unlike WASAPI loopback this also works when the desktop has no audible
    output endpoint (CI/sandbox), and it starts displaying levels immediately
    instead of waiting for a whole track to be decoded.
    """

    levels = pyqtSignal(list)
    started = pyqtSignal()
    finished_with_data = pyqtSignal(bool)

    def __init__(self, source: str, live: bool = False, parent=None):
        super().__init__(parent)
        self._source = str(source)
        self._live = bool(live)
        self._process: subprocess.Popen | None = None

    def stop(self) -> None:
        self.requestInterruption()
        process = self._process
        if process is not None:
            try:
                process.kill()
            except Exception:
                pass

    def run(self) -> None:
        try:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            self.finished_with_data.emit(False)
            return
        command = [
            ffmpeg, "-v", "error",
        ]
        if self._live:
            command += [
                "-reconnect", "1", "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
            ]
        command += [
            "-i", self._source, "-vn", "-f", "s16le", "-ac", "1",
            "-ar", str(SAMPLE_RATE), "-",
        ]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            self._process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                creationflags=flags,
            )
        except Exception:
            self.finished_with_data.emit(False)
            return
        got_data = False
        try:
            stream = self._process.stdout
            while not self.isInterruptionRequested() and stream is not None:
                chunk = stream.read(4096)
                if not chunk:
                    break
                frames = analyze_pcm(chunk)
                if frames:
                    if not got_data:
                        got_data = True
                        self.started.emit()
                    self.levels.emit(list(frames[-1][1]))
        except Exception:
            pass
        finally:
            process = self._process
            if process is not None:
                try:
                    process.kill()
                except Exception:
                    pass
                try:
                    process.wait(timeout=2)
                except Exception:
                    pass
                try:
                    if process.stdout is not None:
                        process.stdout.close()
                except Exception:
                    pass
            self.finished_with_data.emit(got_data)


class WasapiSpectrumThread(QThread):
    levels = pyqtSignal(list)
    captured = pyqtSignal()

    def run(self) -> None:
        loop = WasapiLoopback()
        try:
            loop.start()
            while not self.isInterruptionRequested():
                pcm = loop.read()
                if pcm:
                    frames = analyze_pcm(pcm)
                    if frames:
                        self.captured.emit()
                        self.levels.emit(list(frames[-1][1]))
                self.msleep(80)
        except Exception:
            pass
        finally:
            try:
                loop.stop()
            except Exception:
                pass


class CoverImageThread(QThread):
    loaded = pyqtSignal(str)

    def __init__(self, url: str, cache_dir, parent=None):
        super().__init__(parent)
        self._url = url
        self._cache_dir = cache_dir

    def run(self) -> None:
        path = fetch_cover(self._url, self._cache_dir, timeout=4.0)
        self.loaded.emit(str(path) if path is not None else "")


class ArtistImageThread(QThread):
    loaded = pyqtSignal(str)

    def __init__(self, artist: str, cache_dir, parent=None):
        super().__init__(parent)
        self._artist = artist
        self._cache_dir = cache_dir

    def run(self) -> None:
        path = fetch_artist_image(self._artist, self._cache_dir, timeout=2.5)
        self.loaded.emit(str(path) if path is not None else "")


class NowPlayingPage(QWidget):
    play_pause = pyqtSignal()
    previous_track = pyqtSignal()
    next_track = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None, cache_dir=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("浅语影音 · 正在播放")
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._cache_dir = cache_dir
        self._artist_thread: ArtistImageThread | None = None
        self._cover_thread: CoverImageThread | None = None
        self._spectrum_thread: SpectrumAnalyzerThread | None = None
        self._stream_thread: StreamSpectrumThread | None = None
        self._loopback_thread: WasapiSpectrumThread | None = None
        self._artist_token = 0
        self._cover_token = 0
        self._spectrum_token = 0
        self._stream_token = 0
        self._track: Track | None = None
        self._background = QLabel(self)
        self._background.setScaledContents(True)
        self._blur = QGraphicsBlurEffect(self._background)
        self._blur.setBlurRadius(42)
        self._background.setGraphicsEffect(self._blur)
        self._background.lower()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(70, 55, 70, 40)
        layout.setSpacing(18)
        body = QHBoxLayout()
        body.setSpacing(54)
        self._cover = QLabel()
        self._cover.setObjectName("nowPageCover")
        self._cover.setFixedSize(380, 380)
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setText("♪")
        left = QVBoxLayout()
        left.setSpacing(8)
        left.addWidget(self._cover, 0, Qt.AlignVCenter)
        self._spectrum = SpectrumWidget()
        self._spectrum.setObjectName("nowPageSpectrum")
        left.addWidget(self._spectrum)
        self._spectrum_source = QLabel("频谱：装饰")
        self._spectrum_source.setObjectName("stats")
        left.addWidget(self._spectrum_source)
        left.addStretch(1)
        body.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(8)
        self._title = QLabel("未在播放")
        self._title.setObjectName("nowPageTitle")
        self._meta = QLabel("")
        self._meta.setObjectName("nowPageMeta")
        self._lyrics = QListWidget()
        self._lyrics.setObjectName("nowPageLyrics")
        self._lyrics.setFocusPolicy(Qt.NoFocus)
        right.addWidget(self._title)
        right.addWidget(self._meta)
        right.addWidget(self._lyrics, 1)
        controls = QHBoxLayout()
        prev = QPushButton("上一首")
        prev.clicked.connect(self.previous_track)
        play = QPushButton("播放 / 暂停")
        play.clicked.connect(self.play_pause)
        nxt = QPushButton("下一首")
        nxt.clicked.connect(self.next_track)
        close = QPushButton("关闭")
        close.clicked.connect(self.close)
        controls.addWidget(prev)
        controls.addWidget(play)
        controls.addWidget(nxt)
        controls.addStretch(1)
        controls.addWidget(close)
        right.addLayout(controls)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)

    def set_track(self, track: Track) -> None:
        self._track = track
        self._title.setText(track.title or Path(track.path).stem)
        meta = " · ".join(part for part in (track.artist, track.album) if part)
        self._meta.setText(meta or Path(track.path).parent.name)
        self._spectrum.set_frames(None)
        self._spectrum.set_live_levels(None)
        path = str(track.path or "")
        local_file = bool(path) and not path.lower().startswith(("http://", "https://")) and Path(path).is_file()
        self._stop_loopback()
        self._stop_spectrum_analysis()
        self._stop_stream_analysis()
        if path and (local_file or path.lower().startswith(("http://", "https://"))):
            self._start_stream_analysis(path, live=not local_file)
        else:
            self._spectrum_source.setText("频谱：装饰")
        self._spectrum.set_playing(True)
        if str(track.cover or "").lower().startswith(("http://", "https://")):
            self._load_remote_cover(track.cover)
            return
        pixmap = QPixmap(track.cover) if track.cover else QPixmap()
        if pixmap.isNull():
            self._cover.setPixmap(QPixmap())
            self._cover.setText("♪")
            self._background.setPixmap(QPixmap())
            self._load_artist_image(track)
            return
        self._apply_cover(pixmap)

    def _load_remote_cover(self, url: str) -> None:
        self._cover.setText("♪")
        self._cover.setPixmap(QPixmap())
        self._background.setPixmap(QPixmap())
        if not self._cache_dir:
            self._load_artist_image(self._track) if self._track is not None else None
            return
        self._cover_token += 1
        token = self._cover_token
        if self._cover_thread is not None and self._cover_thread.isRunning():
            self._cover_thread.requestInterruption()
            self._cover_thread.wait(5000)
        thread = CoverImageThread(url, self._cache_dir, self)
        thread.loaded.connect(lambda path: self._on_remote_cover(token, path))
        self._cover_thread = thread
        thread.start()

    def _apply_cover(self, pixmap: QPixmap) -> None:
        self._cover.setText("")
        self._background.setPixmap(pixmap.scaled(
            self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        ))
        self._cover.setPixmap(pixmap.scaled(
            QSize(380, 380), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    def _on_remote_cover(self, token: int, path: str) -> None:
        if token != self._cover_token or not path:
            return
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self._apply_cover(pixmap)
        elif self._track is not None:
            self._load_artist_image(self._track)

    def _load_artist_image(self, track: Track) -> None:
        path_text = str(track.path or "")
        if path_text.lower().startswith(("http://", "https://")):
            return
        folder = Path(path_text).parent
        for name in ("artist.jpg", "artist.png", "folder.jpg", "folder.png"):
            local = folder / name
            if local.is_file():
                pixmap = QPixmap(str(local))
                if not pixmap.isNull():
                    self._apply_cover(pixmap)
                    return
        if not self._cache_dir or not str(track.artist or "").strip():
            return
        if self._artist_thread is not None and self._artist_thread.isRunning():
            self._artist_thread.requestInterruption()
            self._artist_thread.wait(3000)
        self._artist_token += 1
        token = self._artist_token
        thread = ArtistImageThread(str(track.artist), self._cache_dir, self)
        thread.loaded.connect(lambda path: self._on_artist_image(token, path))
        self._artist_thread = thread
        thread.start()

    def _on_artist_image(self, token: int, path: str) -> None:
        if token != self._artist_token or not path or self._track is None:
            return
        if self._track.cover:
            return
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self._apply_cover(pixmap)

    def set_lyrics(self, lines) -> None:
        self._lyrics.clear()
        for text in lines:
            self._lyrics.addItem(text)

    def set_playing(self, playing: bool) -> None:
        self._spectrum.set_playing(playing)

    def set_playback_position(self, seconds: float) -> None:
        self._spectrum.set_position(seconds)

    def _start_spectrum_analysis(self, path: str) -> None:
        self._spectrum_token += 1
        token = self._spectrum_token
        if self._spectrum_thread is not None and self._spectrum_thread.isRunning():
            self._spectrum_thread.requestInterruption()
            self._spectrum_thread.wait(2000)
        thread = SpectrumAnalyzerThread(path, self)
        thread.analysed.connect(lambda frames: self._on_spectrum(token, frames))
        self._spectrum_thread = thread
        thread.start()

    def _stop_spectrum_analysis(self) -> None:
        self._spectrum_token += 1
        if self._spectrum_thread is not None and self._spectrum_thread.isRunning():
            self._spectrum_thread.requestInterruption()
            self._spectrum_thread.wait(2000)

    def _start_stream_analysis(self, source: str, live: bool = False) -> None:
        self._stream_token += 1
        token = self._stream_token
        self._spectrum_source.setText("频谱：正在解码…")
        thread = StreamSpectrumThread(source, live, self)
        thread.started.connect(
            lambda: self._spectrum_source.setText(
                "频谱：实时 · 流分析" if live else "频谱：真实 · FFmpeg"
            )
        )
        thread.levels.connect(self._spectrum.set_live_levels)
        thread.finished_with_data.connect(
            lambda ok: self._on_stream_finished(token, ok, live)
        )
        self._stream_thread = thread
        thread.start()

    def _stop_stream_analysis(self) -> None:
        thread = self._stream_thread
        if thread is not None:
            thread.stop()
            if thread.isRunning():
                thread.wait(3000)
            self._stream_thread = None

    def _on_stream_finished(self, token: int, ok: bool, live: bool) -> None:
        if token != self._stream_token:
            return
        if ok:
            return
        if live and os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            self._spectrum_source.setText("频谱：流分析失败，尝试 WASAPI")
            self._start_loopback()
        else:
            self._spectrum_source.setText("频谱：装饰（无音频数据）")

    def _start_loopback(self) -> None:
        self._stop_loopback()
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            self._spectrum_source.setText("频谱：装饰（无音频输出）")
            return
        self._spectrum_source.setText("频谱：WASAPI（等待音频）")
        thread = WasapiSpectrumThread(self)
        thread.captured.connect(lambda: self._spectrum_source.setText("频谱：实时 · WASAPI"))
        thread.levels.connect(self._spectrum.set_live_levels)
        self._loopback_thread = thread
        thread.start()

    def _stop_loopback(self) -> None:
        if self._loopback_thread is not None and self._loopback_thread.isRunning():
            self._loopback_thread.requestInterruption()
            self._loopback_thread.wait(3000)
        self._loopback_thread = None

    def _on_spectrum(self, token: int, frames) -> None:
        if token != self._spectrum_token:
            return
        if frames:
            self._spectrum.set_frames(frames)
            self._spectrum_source.setText("频谱：真实 · FFmpeg")
        else:
            self._spectrum_source.setText("频谱：装饰（分析失败）")

    def set_position(self, index: int) -> None:
        if 0 <= index < self._lyrics.count():
            self._lyrics.setCurrentRow(index)
            self._lyrics.scrollToItem(self._lyrics.item(index), QListWidget.PositionAtCenter)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._background.setGeometry(self.rect())

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space:
            self.play_pause.emit()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._stop_stream_analysis()
        for thread in (self._artist_thread, self._cover_thread, self._spectrum_thread,
                       self._loopback_thread):
            if thread is not None and thread.isRunning():
                thread.requestInterruption()
                thread.wait(6000)
        self.closed.emit()
        super().closeEvent(event)
