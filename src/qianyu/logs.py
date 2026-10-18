# -*- coding: utf-8 -*-
"""Rotating logs, crash dumps and startup breadcrumbs.

The windowed (console=False) build has no stderr, so startup failures must be
written to a file before anything else is imported.
"""
from __future__ import annotations

import faulthandler
import logging
import os
import sys
import tempfile
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR: Path | None = None
_CRASH_FILE = None


def _candidates() -> list[Path]:
    out = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        out.append(Path(local) / "QianYu" / "logs")
    out.append(Path.home() / ".qianyu_media" / "logs")
    out.append(Path(tempfile.gettempdir()) / "QianYu" / "logs")
    return out


def log_dir() -> Path:
    global _LOG_DIR
    if _LOG_DIR is not None:
        return _LOG_DIR
    for candidate in _candidates():
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write-test"
            probe.write_text("", encoding="utf-8")
            probe.unlink()
            _LOG_DIR = candidate
            return candidate
        except OSError:
            continue
    _LOG_DIR = Path(tempfile.mkdtemp(prefix="qianyu-logs-"))
    return _LOG_DIR


def bootstrap(message: str) -> None:
    """Append one line without importing anything else (frozen startup)."""
    try:
        path = log_dir() / "boot.log"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(message.rstrip() + "\n")
    except Exception:
        pass


def setup_logging(level: int = logging.INFO) -> Path:
    global _CRASH_FILE
    path = log_dir()
    logger = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        handler = RotatingFileHandler(
            path / "app.log", maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(handler)
        if sys.stderr is not None:
            stream = logging.StreamHandler()
            stream.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
            logger.addHandler(stream)
    logger.setLevel(level)
    try:
        crash = (path / "crash.log").open("a", encoding="utf-8")
        _CRASH_FILE = crash
        faulthandler.enable(file=crash, all_threads=True)
    except OSError:
        pass
    return path


def install_excepthook() -> None:
    original = sys.excepthook

    def _hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            with (log_dir() / "crash.log").open("a", encoding="utf-8") as fh:
                fh.write(text)
        except OSError:
            pass
        if threading.current_thread() is threading.main_thread():
            try:
                from .qt import QApplication, QMessageBox

                if QApplication.instance() is not None:
                    box = QMessageBox()
                    box.setIcon(QMessageBox.Critical)
                    box.setWindowTitle("浅语影音出错")
                    box.setText("程序遇到未处理的错误，详细信息已写入日志。")
                    box.setInformativeText(f"{exc_type.__name__}: {exc}")
                    box.setDetailedText(text)
                    box.exec()
                    return
            except Exception:
                pass
        original(exc_type, exc, tb)

    sys.excepthook = _hook
