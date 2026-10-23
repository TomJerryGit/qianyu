# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Per-user Windows file association for audio files.

This does not hijack the default handler: it registers a ProgID and puts it in
each extension's OpenWithProgids + the Default Apps capability list. The user
still chooses "浅语影音" as the default in Windows Settings.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROGID = "QianYu.Audio"
APP_NAME = "浅语影音"
AUDIO_EXTENSIONS = (
    ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".opus",
    ".ape", ".wma", ".aiff", ".aif", ".wv",
)
ROOT = Path(__file__).resolve().parents[3]


def command_line() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" "%1"'
    python = Path(sys.executable)
    launcher = python.with_name("pythonw.exe")
    if not launcher.exists():
        launcher = python
    runner = ROOT / "run_dev.py"
    return f'"{launcher}" "{runner}" "%1"'


def _winreg():
    import winreg

    return winreg


def is_registered() -> bool:
    if os.name != "nt":
        return False
    winreg = _winreg()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROGID}\shell\open\command"):
            return True
    except OSError:
        return False


def register() -> None:
    """Register for the current user. Raises OSError on failure."""
    if os.name != "nt":
        raise OSError("file association is only implemented on Windows")
    winreg = _winreg()
    command = command_line()
    icon = f'"{sys.executable}",0'

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROGID}") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, f"{APP_NAME} 音频文件")
        winreg.SetValueEx(key, "FriendlyTypeName", 0, winreg.REG_SZ, f"{APP_NAME} 音频文件")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROGID}\DefaultIcon") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, icon)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROGID}\shell\open\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)

    capabilities = r"Software\QianYu\Capabilities"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, capabilities) as key:
        winreg.SetValueEx(key, "ApplicationName", 0, winreg.REG_SZ, APP_NAME)
        winreg.SetValueEx(key, "ApplicationDescription", 0, winreg.REG_SZ, "浅语影音 · 本地音乐播放器")
        winreg.SetValueEx(key, "ApplicationIcon", 0, winreg.REG_SZ, icon)
        with winreg.CreateKey(key, "FileAssociations") as assoc:
            for extension in AUDIO_EXTENSIONS:
                winreg.SetValueEx(assoc, extension, 0, winreg.REG_SZ, PROGID)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications") as key:
        winreg.SetValueEx(key, "QianYu", 0, winreg.REG_SZ, capabilities)

    for extension in AUDIO_EXTENSIONS:
        with winreg.CreateKey(
            winreg.HKEY_CURRENT_USER, rf"Software\Classes\{extension}\OpenWithProgids"
        ) as key:
            winreg.SetValueEx(key, PROGID, 0, winreg.REG_NONE, b"")


def unregister() -> None:
    if os.name != "nt":
        return
    winreg = _winreg()
    for path in (rf"Software\Classes\{PROGID}", r"Software\QianYu\Capabilities"):
        try:
            _delete_tree(winreg.HKEY_CURRENT_USER, path)
        except OSError:
            pass
    for extension in AUDIO_EXTENSIONS:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Classes\{extension}\OpenWithProgids",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, PROGID)
        except OSError:
            pass
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications", 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, "QianYu")
    except OSError:
        pass


def _delete_tree(root, path: str) -> None:
    winreg = _winreg()
    with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as key:
        while True:
            try:
                child = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_tree(root, path + "\\" + child)
    winreg.DeleteKey(root, path)
