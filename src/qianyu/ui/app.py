# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Application entry point for the 0.9 music player."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from ..qt import Qt
from ..qt import QLocalServer, QLocalSocket
from ..qt import QApplication

from ..config import Config
from ..logs import bootstrap, install_excepthook, setup_logging
from .main_window import MainWindow

SERVER_NAME = "qianyu-0.9-" + os.environ.get("USERNAME", "user").lower()


def _load_theme(name: str) -> str:
    path = Path(__file__).resolve().parent / "theme" / f"{name}.qss"
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _already_running() -> bool:
    if os.environ.get("QIANYU_NO_SINGLE_INSTANCE"):
        return False
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(300):
        socket.write(b"show")
        socket.flush()
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv
    bootstrap("app: enter")
    setup_logging()
    install_excepthook()
    if "--register-associations" in args:
        from ..platform.windows import register

        register()
        return 0
    if "--unregister-associations" in args:
        from ..platform.windows import unregister

        unregister()
        return 0
    for attribute in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
        value = getattr(Qt, attribute, None)
        if value is not None:
            QApplication.setAttribute(value, True)
    app = QApplication(args)
    app.setApplicationName("浅语影音")
    app.setOrganizationName("QianYuMedia")
    icon_path = Path(__file__).resolve().parent / "theme" / "app.ico"
    if icon_path.exists():
        from ..qt import QIcon

        app.setWindowIcon(QIcon(str(icon_path)))
    bootstrap("app: QApplication created")

    if _already_running():
        bootstrap("app: another instance, exit")
        return 0

    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    server.listen(SERVER_NAME)
    bootstrap(f"app: server listen={server.isListening()}")

    config = Config()
    if not os.environ.get("QIANYU_NO_QSS"):
        app.setStyleSheet(_load_theme(str(config.get("theme", "dark"))))
    window = MainWindow(config)
    bootstrap("app: window created")
    window.show()
    bootstrap("app: window shown")

    def _on_new_connection() -> None:
        connection = server.nextPendingConnection()
        if connection is not None:
            window._show_window()
            connection.disconnectFromServer()

    server.newConnection.connect(_on_new_connection)
    app.aboutToQuit.connect(window.shutdown)

    # Optional file argument: qianyu "D:\Music\song.flac"
    candidates = [arg for arg in (argv if argv is not None else sys.argv)[1:] if not arg.startswith("-")]
    if candidates and Path(candidates[0]).is_file():
        window.open_path(candidates[0])

    if "--smoke" in (argv if argv is not None else sys.argv):
        # Initialization smoke: prove imports, Qt platform, libmpv, theme and
        # window construction work. Let the Qt loop turn once: calling
        # os._exit immediately after show() races Windows IME initialization
        # and produces intermittent 0xC0000005 in the smoke process.
        from ..qt import QTimer

        QTimer.singleShot(2500, lambda: os._exit(0))
        app.exec()
    bootstrap("app: exec")
    code = app.exec()
    bootstrap(f"app: exec returned {code}")
    return code
