# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Audio/video playback engine built on libmpv.

The engine is UI-agnostic: it accepts commands and pushes plain callbacks.
Qt (or any other shell) adapts those callbacks to signals.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, Optional

from ..eq import BAND_FREQS, EQ_PRESETS, build_eq_filter
from . import _loader  # noqa: F401  (sets PATH before importing mpv)
import mpv


class EngineState(str, Enum):
    IDLE = "idle"
    LOADING = "loading"
    PLAYING = "playing"
    PAUSED = "paused"
    ERROR = "error"


class LoopMode(str, Enum):
    SEQUENTIAL = "sequential"
    SINGLE = "single"


@dataclass
class EngineEvent:
    kind: str
    value: object = None


class MpvEngine:
    """Thin, testable wrapper around python-mpv.

    Events: state, position, duration, title, error, eof.
    Callbacks run on python-mpv's event thread; UI code must marshal to the
    main thread (Qt signal/slot does this automatically if the receiver is a
    QObject).
    """

    def __init__(
        self,
        on_event: Optional[Callable[[EngineEvent], None]] = None,
        *,
        volume: int = 70,
        audio_device: str = "auto",
        ao: str = "auto",
        vo: str = "null",
    ):
        self._on_event = on_event
        self._state = EngineState.IDLE
        self._lock = threading.RLock()
        self._alive = True
        self._queue: list[str] = []
        self._ranges: list[tuple[float, float]] = []
        self._mpv = mpv.MPV(
            vo=vo,
            ao=ao,
            idle="yes",
            keep_open="no",
            force_window="no",
            audio_display="no",
            gapless_audio="yes",
            volume=volume,
            audio_device=audio_device,
            **{"audio-client-name": "QianYu", "input-default-bindings": "no"},
        )
        self._register_observers()

    def set_event_callback(self, callback) -> None:
        self._on_event = callback

    # ------------------------------------------------------------------
    # properties
    # ------------------------------------------------------------------
    @property
    def state(self) -> EngineState:
        return self._state

    @property
    def position(self) -> float:
        return float(self._mpv.time_pos or 0.0)

    @property
    def duration(self) -> float:
        return float(self._mpv.duration or 0.0)

    @property
    def volume(self) -> int:
        return int(self._mpv.volume or 0)

    @volume.setter
    def volume(self, value: int) -> None:
        self._mpv.volume = max(0, min(100, int(value)))

    @property
    def title(self) -> str:
        return str(self._mpv.media_title or "")

    @property
    def stream_title(self) -> str:
        """ICY/stream metadata title, if libmpv exposes one."""
        try:
            metadata = self._mpv.metadata or {}
        except Exception:
            return ""
        if not isinstance(metadata, dict):
            return ""
        for key in ("icy-title", "StreamTitle", "stream_title", "title"):
            value = metadata.get(key)
            if value:
                return str(value).strip()
        return ""

    @property
    def path(self) -> str:
        return str(self._mpv.path or "")

    @property
    def audio_devices(self) -> list[dict]:
        return list(self._mpv.audio_device_list or [])

    @property
    def audio_device(self) -> str:
        return str(self._mpv.audio_device or "auto")

    @audio_device.setter
    def audio_device(self, name: str) -> None:
        self._mpv.audio_device = name

    @property
    def queue(self) -> list[str]:
        return list(self._queue)

    @property
    def queue_index(self) -> int:
        try:
            return int(self._mpv.playlist_pos if self._mpv.playlist_pos is not None else -1)
        except Exception:
            return -1

    # ------------------------------------------------------------------
    # commands
    # ------------------------------------------------------------------
    def set_queue(self, paths: Iterable[str], start_index: int = 0,
                  ranges: Optional[list[tuple[float, float]]] = None) -> None:
        """Replace mpv's playlist and start at start_index.

        Using mpv's own playlist (instead of calling play() per track) is what
        makes gapless transitions possible: the next file is already queued
        when the current one ends. `ranges` enables CUE-style sub-track ranges.
        """
        entries = [str(Path(p)) for p in paths]
        if not entries:
            self.stop()
            return
        start = max(0, min(int(start_index), len(entries) - 1))
        self._queue = entries
        self._ranges = list(ranges or [])
        self._set_state(EngineState.LOADING)
        try:
            self._mpv.command("playlist-clear")
            for index, entry in enumerate(entries):
                if self._ranges and index < len(self._ranges):
                    begin, end = self._ranges[index]
                    option = f"start={begin},end={end}"
                    self._mpv.command("loadfile", entry, "append", "0", option)
                else:
                    self._mpv.command("loadfile", entry, "append")
            self._mpv.command("playlist-play-index", start)
        except Exception as exc:
            self._fail(exc)

    def play_index(self, index: int) -> None:
        if not self._queue:
            return
        index = max(0, min(int(index), len(self._queue) - 1))
        self._set_state(EngineState.LOADING)
        try:
            self._mpv.command("playlist-play-index", index)
        except Exception as exc:
            self._fail(exc)

    def next(self) -> None:
        try:
            self._mpv.command("playlist-next")
        except Exception as exc:
            self._fail(exc)

    def previous(self) -> None:
        try:
            self._mpv.command("playlist-prev")
        except Exception as exc:
            self._fail(exc)

    def move_index(self, src: int, dst: int) -> None:
        if not (0 <= src < len(self._queue)) or not (0 <= dst < len(self._queue)):
            return
        try:
            self._mpv.command("playlist-move", int(src), int(dst))
            item = self._queue.pop(src)
            self._queue.insert(dst, item)
            if self._ranges and src < len(self._ranges):
                rng = self._ranges.pop(src)
                self._ranges.insert(min(dst, len(self._ranges)), rng)
        except Exception as exc:
            self._fail(exc)

    def remove_index(self, index: int) -> None:
        if not (0 <= index < len(self._queue)):
            return
        try:
            self._mpv.command("playlist-remove", int(index))
            self._queue.pop(index)
            if self._ranges and index < len(self._ranges):
                self._ranges.pop(index)
        except Exception as exc:
            self._fail(exc)

    def play(self, uri: str, start: float = 0.0, end: float | None = None) -> None:
        self._queue = [str(uri)]
        self._ranges = [(start, end)] if end is not None else []
        self._set_state(EngineState.LOADING)
        try:
            if start > 0 or end is not None:
                option = f"start={start}" + (f",end={end}" if end is not None else "")
                self._mpv.command("loadfile", uri, "replace", "0", option)
            else:
                self._mpv.play(uri)
        except Exception as exc:
            self._fail(exc)

    def pause(self) -> None:
        self._mpv.pause = True
        self._set_state(EngineState.PAUSED)

    def resume(self) -> None:
        self._mpv.pause = False
        self._set_state(EngineState.PLAYING)

    def toggle(self) -> None:
        # Use mpv's actual pause flag, not our cached state: state can still be
        # LOADING during the first few hundred milliseconds of a track.
        if bool(self._mpv.pause):
            self.resume()
        else:
            self.pause()

    def stop(self) -> None:
        self._mpv.command("stop")
        self._set_state(EngineState.IDLE)

    def clear_queue(self) -> None:
        self._queue = []
        self._ranges = []
        self.stop()

    def seek(self, seconds: float) -> None:
        self._mpv.command("seek", max(0.0, float(seconds)), "absolute")

    def set_eq(self, bands: Iterable[float], preamp_db: float = 0.0) -> None:
        self._mpv.af = build_eq_filter(bands, preamp_db)

    def clear_eq(self) -> None:
        self._mpv.af = ""

    def set_replaygain(self, mode: str = "track") -> None:
        self._mpv.replaygain = mode

    def set_audio_exclusive(self, enabled: bool) -> None:
        """WASAPI/CoreAudio exclusive mode (no-op on unsupported outputs)."""
        self._mpv.audio_exclusive = bool(enabled)

    def set_speed(self, speed: float) -> None:
        self._mpv.speed = max(0.25, min(4.0, float(speed)))

    def shutdown(self) -> None:
        # Property observers may still fire while libmpv tears down. Disable
        # them first, then terminate synchronously: python-mpv's terminate()
        # joins its event thread. Exiting while that thread is still alive can
        # crash during Python finalization (intermittent 0xC0000005).
        self._alive = False
        self._on_event = None
        try:
            self._mpv.terminate()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _register_observers(self) -> None:
        @self._mpv.property_observer("time-pos")
        def _time(_name, value):
            if not self._alive:
                return
            if value is not None:
                if self._state == EngineState.LOADING and not bool(self._mpv.pause):
                    self._set_state(EngineState.PLAYING)
                self._emit("position", float(value))

        @self._mpv.property_observer("duration")
        def _duration(_name, value):
            if not self._alive:
                return
            if value is not None:
                self._emit("duration", float(value))

        @self._mpv.property_observer("pause")
        def _pause(_name, value):
            if not self._alive:
                return
            if value:
                self._set_state(EngineState.PAUSED)
            elif self._state in (EngineState.PAUSED, EngineState.LOADING):
                self._set_state(EngineState.PLAYING)

        @self._mpv.property_observer("media-title")
        def _title(_name, value):
            if not self._alive:
                return
            if value:
                self._emit("title", str(value))

        @self._mpv.property_observer("playlist-pos")
        def _playlist_pos(_name, value):
            if not self._alive:
                return
            if value is not None:
                self._emit("index", int(value))

        @self._mpv.property_observer("path")
        def _path(_name, value):
            if not self._alive:
                return
            if value:
                self._emit("path", str(value))

        @self._mpv.property_observer("eof-reached")
        def _eof(_name, value):
            if not self._alive:
                return
            if value:
                self._emit("eof", None)
                try:
                    pos = int(self._mpv.playlist_pos if self._mpv.playlist_pos is not None else -1)
                except Exception:
                    pos = -1
                if pos < 0 or pos >= len(self._queue) - 1:
                    self._set_state(EngineState.IDLE)

    def _set_state(self, state: EngineState) -> None:
        with self._lock:
            if self._state == state:
                return
            self._state = state
        self._emit("state", state)

    def _fail(self, exc: Exception) -> None:
        self._set_state(EngineState.ERROR)
        self._emit("error", f"{type(exc).__name__}: {exc}")

    def _emit(self, kind: str, value) -> None:
        cb = self._on_event
        if cb is not None:
            try:
                cb(EngineEvent(kind, value))
            except Exception:
                # A broken listener must never kill the playback thread.
                pass

    # convenience for tests/headless waits
    def wait_until(self, predicate: Callable[[], bool], timeout: float = 10.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.05)
        return False
