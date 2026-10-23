# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Small secret store backed by Windows DPAPI.

Secrets are encrypted for the current Windows user with CryptProtectData and
stored as ``dpapi:<base64>`` in the config file. On non-Windows platforms a
plain prefix is used so development/tests remain portable; the production
build targets Windows.
"""
from __future__ import annotations

import base64
import ctypes
import sys
from ctypes import wintypes

PREFIX = "dpapi:"
PLAIN_PREFIX = "plain:"
ENTROPY = b"QianYu-credentials-v1"


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _protect_windows(text: str) -> str:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    input_blob, input_buffer = _blob(text.encode("utf-8"))
    entropy_blob, entropy_buffer = _blob(ENTROPY)
    output = _DataBlob()
    ok = crypt32.CryptProtectData(
        ctypes.byref(input_blob), "QianYu", ctypes.byref(entropy_blob),
        None, None, 0, ctypes.byref(output),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        encrypted = ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)
    return PREFIX + base64.b64encode(encrypted).decode("ascii")


def _unprotect_windows(value: str) -> str:
    raw = base64.b64decode(value[len(PREFIX):])
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    input_blob, input_buffer = _blob(raw)
    entropy_blob, entropy_buffer = _blob(ENTROPY)
    output = _DataBlob()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(input_blob), None, ctypes.byref(entropy_blob),
        None, None, 0, ctypes.byref(output),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        decrypted = ctypes.string_at(output.pbData, output.cbData)
    finally:
        kernel32.LocalFree(output.pbData)
    return decrypted.decode("utf-8")


def protect(value: str) -> str:
    value = str(value or "")
    if not value:
        return ""
    if sys.platform == "win32":
        return _protect_windows(value)
    return PLAIN_PREFIX + base64.b64encode(value.encode("utf-8")).decode("ascii")


def unprotect(value: str) -> str:
    value = str(value or "")
    if not value:
        return ""
    if value.startswith(PREFIX):
        return _unprotect_windows(value)
    if value.startswith(PLAIN_PREFIX):
        return base64.b64decode(value[len(PLAIN_PREFIX):]).decode("utf-8")
    return value


class SecretStore:
    """Read/write encrypted secrets in a Config-like object."""

    def __init__(self, config):
        self._config = config

    def get(self, key: str) -> str:
        return unprotect(self._config.get(key, "") or "")

    def set(self, key: str, value: str) -> None:
        value = str(value or "")
        self._config.set(key, protect(value) if value else "")

    def migrate(self, keys: list[str]) -> bool:
        """Encrypt legacy plaintext values once, in place."""
        changed = False
        for key in keys:
            value = self._config.get(key, "") or ""
            if value and not str(value).startswith((PREFIX, PLAIN_PREFIX)):
                self._config.set(key, protect(value))
                changed = True
        return changed
