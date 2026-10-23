# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Settings dialog (theme, tray, media keys, output device, library folders)."""
from __future__ import annotations

from pathlib import Path

from ..qt import Qt
from ..qt import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QSpinBox, QVBoxLayout,
)

from ..config import Config


class SettingsDialog(QDialog):
    def __init__(self, config: Config, engine, parent=None):
        super().__init__(parent)
        self._config = config
        self._engine = engine
        self.setWindowTitle("设置")
        self.setMinimumWidth(520)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("主题"))
        self._theme = QComboBox()
        self._theme.addItem("深色", "dark")
        self._theme.addItem("浅色", "light")
        index = self._theme.findData(str(self._config.get("theme", "dark")))
        self._theme.setCurrentIndex(max(0, index))
        layout.addWidget(self._theme)

        self._close_to_tray = QCheckBox("关闭窗口时最小化到托盘")
        self._close_to_tray.setChecked(bool(self._config.get("close_to_tray", True)))
        layout.addWidget(self._close_to_tray)

        self._media_keys = QCheckBox("启用全局媒体键（播放/暂停、上一首、下一首、停止）")
        self._media_keys.setChecked(bool(self._config.get("global_media_keys", True)))
        layout.addWidget(self._media_keys)

        layout.addWidget(QLabel("输出设备"))
        self._device = QComboBox()
        current = self._engine.audio_device
        self._device.addItem("自动", "auto")
        for device in self._engine.audio_devices:
            name = str(device.get("name", ""))
            if name and name != "auto":
                self._device.addItem(str(device.get("description", name)), name)
        index = self._device.findData(current)
        self._device.setCurrentIndex(max(0, index))
        layout.addWidget(self._device)

        layout.addWidget(QLabel("ReplayGain"))
        self._replaygain = QComboBox()
        self._replaygain.addItem("关闭", "no")
        self._replaygain.addItem("按曲目", "track")
        self._replaygain.addItem("按专辑", "album")
        rg_index = self._replaygain.findData(str(self._config.get("replaygain", "no")))
        self._replaygain.setCurrentIndex(max(0, rg_index))
        layout.addWidget(self._replaygain)

        self._exclusive = QCheckBox("WASAPI 独占模式（可能独占音频设备）")
        self._exclusive.setChecked(bool(self._config.get("audio_exclusive", False)))
        layout.addWidget(self._exclusive)

        layout.addWidget(QLabel("播客缓存上限（MB）"))
        self._podcast_cache_limit = QSpinBox()
        self._podcast_cache_limit.setRange(128, 102400)
        self._podcast_cache_limit.setValue(int(self._config.get("podcast_cache_limit_mb", 2048)))
        layout.addWidget(self._podcast_cache_limit)

        self._listenbrainz = QCheckBox("启用 ListenBrainz Scrobbling（仅本地音乐，默认关闭）")
        self._listenbrainz.setChecked(bool(self._config.get("listenbrainz_enabled", False)))
        layout.addWidget(self._listenbrainz)
        layout.addWidget(QLabel("ListenBrainz 用户 token"))
        self._listenbrainz_token = QLineEdit(str(self._config.get("listenbrainz_token", "")))
        self._listenbrainz_token.setEchoMode(QLineEdit.Password)
        self._listenbrainz_token.setPlaceholderText("在 listenbrainz.org/settings 获取")
        layout.addWidget(self._listenbrainz_token)
        note = QLabel("token 只保存在本机配置文件；播放达到 50% 或 4 分钟后提交一次。")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addWidget(QLabel("远程媒体库（Navidrome / Subsonic）服务器地址"))
        self._subsonic_url = QLineEdit(str(self._config.get("subsonic_url", "")))
        self._subsonic_url.setPlaceholderText("https://music.example.com")
        layout.addWidget(self._subsonic_url)
        layout.addWidget(QLabel("远程媒体库用户名"))
        self._subsonic_user = QLineEdit(str(self._config.get("subsonic_user", "")))
        layout.addWidget(self._subsonic_user)
        layout.addWidget(QLabel("远程媒体库密码（仅保存在本机）"))
        self._subsonic_password = QLineEdit(str(self._config.get("subsonic_password", "")))
        self._subsonic_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self._subsonic_password)
        remote_note = QLabel("仅支持 Subsonic API（Navidrome/Airsonic/Gonic 等）；Jellyfin 需独立适配。")
        remote_note.setWordWrap(True)
        layout.addWidget(remote_note)

        layout.addWidget(QLabel("更新源（manifest.json URL，可留空）"))
        self._update_url = QLineEdit(str(self._config.get("update_url", "")))
        self._update_url.setPlaceholderText("https://example.com/qianyu/manifest.json")
        layout.addWidget(self._update_url)

        layout.addWidget(QLabel("更新公钥（Ed25519，base64，可留空）"))
        self._update_key = QLineEdit(str(self._config.get("update_public_key", "")))
        self._update_key.setPlaceholderText("base64 public key")
        layout.addWidget(self._update_key)

        layout.addWidget(QLabel("音乐文件夹"))
        self._folders = QListWidget()
        for folder in self._config.get("library_folders", []) or []:
            self._folders.addItem(str(folder))
        layout.addWidget(self._folders)
        folder_buttons = QHBoxLayout()
        add = QPushButton("添加…")
        add.clicked.connect(self._add_folder)
        remove = QPushButton("移除")
        remove.clicked.connect(self._remove_folder)
        folder_buttons.addWidget(add)
        folder_buttons.addWidget(remove)
        folder_buttons.addStretch(1)
        layout.addLayout(folder_buttons)

        layout.addStretch(1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("保存")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择音乐文件夹")
        if folder and not self._folders.findItems(folder, Qt.MatchExactly):
            self._folders.addItem(folder)

    def _remove_folder(self) -> None:
        row = self._folders.currentRow()
        if row >= 0:
            self._folders.takeItem(row)

    def accept(self) -> None:
        self._config.set("theme", self._theme.currentData())
        self._config.set("close_to_tray", self._close_to_tray.isChecked())
        self._config.set("global_media_keys", self._media_keys.isChecked())
        self._config.set("library_folders", [self._folders.item(i).text() for i in range(self._folders.count())])
        self._config.set("update_url", self._update_url.text().strip())
        self._config.set("update_public_key", self._update_key.text().strip())
        self._config.set("podcast_cache_limit_mb", self._podcast_cache_limit.value())
        self._config.set("listenbrainz_enabled", self._listenbrainz.isChecked())
        self._config.set("listenbrainz_token", self._listenbrainz_token.text().strip())
        self._config.set("subsonic_url", self._subsonic_url.text().strip())
        self._config.set("subsonic_user", self._subsonic_user.text().strip())
        self._config.set("subsonic_password", self._subsonic_password.text())
        try:
            self._engine.set_replaygain(str(self._replaygain.currentData()))
            self._config.set("replaygain", str(self._replaygain.currentData()))
            self._engine.set_audio_exclusive(self._exclusive.isChecked())
            self._config.set("audio_exclusive", self._exclusive.isChecked())
        except Exception:
            pass
        device = self._device.currentData()
        if device:
            try:
                self._engine.audio_device = device
            except Exception:
                pass
        super().accept()
