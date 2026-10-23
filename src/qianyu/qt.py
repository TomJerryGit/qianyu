# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Qt binding shim.

Default auto-detects: PySide6 if installed (Python 3.11+ LGPL build), otherwise
PyQt5. Force one with QIANYU_QT=PySide6 or QIANYU_QT=PyQt5.
"""
from __future__ import annotations

import os
import sys

QT_API = os.environ.get("QIANYU_QT", "").strip().lower()
if not QT_API:
    # PySide6 6.8+ requires Python >=3.9. On 3.8 keep the known-good PyQt5
    # default even if an old PySide6 wheel happens to be installed.
    if sys.version_info >= (3, 9):
        try:
            import PySide6  # noqa: F401

            QT_API = "pyside6"
        except ImportError:
            QT_API = "pyqt5"
    else:
        QT_API = "pyqt5"

if QT_API in ("pyside6", "pyside"):
    from PySide6.QtCore import *  # noqa: F401,F403
    from PySide6.QtGui import *  # noqa: F401,F403
    from PySide6.QtWidgets import *  # noqa: F401,F403
    from PySide6.QtNetwork import QLocalServer, QLocalSocket  # noqa: F401
    from PySide6.QtCore import Signal as pyqtSignal  # noqa: F401
    from PySide6.QtCore import Slot as pyqtSlot  # noqa: F401
else:
    from PyQt5.QtCore import *  # noqa: F401,F403
    from PyQt5.QtGui import *  # noqa: F401,F403
    from PyQt5.QtWidgets import *  # noqa: F401,F403
    from PyQt5.QtNetwork import QLocalServer, QLocalSocket  # noqa: F401
    from PyQt5.QtCore import pyqtSignal, pyqtSlot  # noqa: F401


try:
    DIALOG_ACCEPTED = QDialog.DialogCode.Accepted  # type: ignore[name-defined]
except Exception:  # pragma: no cover - older binding
    DIALOG_ACCEPTED = QDialog.Accepted  # type: ignore[name-defined]


def exec_app(app):
    """QApplication.exec() across PyQt5/PySide6."""
    return app.exec() if hasattr(app, "exec") else app.exec_()


def exec_modal(widget):
    """QDialog/QMenu.exec() across PyQt5/PySide6."""
    return widget.exec() if hasattr(widget, "exec") else widget.exec_()
