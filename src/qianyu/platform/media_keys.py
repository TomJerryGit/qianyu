# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Windows global multimedia keys (play/pause, next, previous, stop).

Uses RegisterHotKey + a Qt native event filter. No extra dependency. On
non-Windows or when another app owns the key, registration fails gracefully and
the app keeps working with its in-window shortcuts.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys
from typing import Callable

from ..qt import QAbstractNativeEventFilter, QObject

WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


class _HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, callbacks: dict[int, Callable[[], None]]):
        super().__init__()
        self._callbacks = callbacks

    def nativeEventFilter(self, event_type, message):
        if os.name == "nt" and event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    callback = self._callbacks.get(int(msg.wParam))
                    if callback is not None:
                        callback()
                        return True, 0
            except Exception:
                pass
        return False, 0


class MediaKeyManager(QObject):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._ids: list[int] = []
        self._filter: _HotkeyFilter | None = None
        self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def register(
        self,
        play_pause: Callable[[], None],
        next_track: Callable[[], None],
        previous: Callable[[], None],
        stop: Callable[[], None],
    ) -> bool:
        if os.name != "nt" or os.environ.get("QIANYU_NO_MEDIA_KEYS"):
            return False
        user32 = ctypes.windll.user32
        mapping = {
            VK_MEDIA_PLAY_PAUSE: play_pause,
            VK_MEDIA_NEXT_TRACK: next_track,
            VK_MEDIA_PREV_TRACK: previous,
            VK_MEDIA_STOP: stop,
        }
        base = 0xA100
        for offset, (vk, callback) in enumerate(mapping.items()):
            hotkey_id = base + offset
            if not user32.RegisterHotKey(None, hotkey_id, MOD_NOREPEAT, vk):
                self.unregister()
                return False
            self._ids.append(hotkey_id)
            self._callbacks[hotkey_id] = callback
        self._filter = _HotkeyFilter(self._callbacks)
        self._app.installNativeEventFilter(self._filter)
        self._available = True
        return True

    def unregister(self) -> None:
        if os.name == "nt":
            user32 = ctypes.windll.user32
            for hotkey_id in self._ids:
                try:
                    user32.UnregisterHotKey(None, hotkey_id)
                except Exception:
                    pass
        self._ids.clear()
        self._callbacks.clear()
        if self._filter is not None:
            try:
                self._app.removeNativeEventFilter(self._filter)
            except Exception:
                pass
            self._filter = None
        self._available = False
