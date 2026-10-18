# -*- coding: utf-8 -*-
"""Smoke for windowed top-level gesture overlay (optional V12 mode)."""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from qianyu.qt import QApplication, QPoint, Qt  # noqa: E402

if QApplication.__module__.startswith("PySide6"):
    from PySide6.QtTest import QTest  # noqa: E402
else:
    from PyQt5.QtTest import QTest  # noqa: E402

from qianyu.config import Config  # noqa: E402
from qianyu.ui.video_window import VideoWindow  # noqa: E402


def main() -> None:
    app = QApplication([])
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-win-gesture-"))
    config = Config(tmp / "config.json")
    config.set("video_gesture_windowed", True)
    window = VideoWindow(config=config, ao="null")
    window.show()
    window.raise_()
    window.activateWindow()
    window.open_path(str(ROOT / "spike" / "fixtures" / "test_resume.mp4"))
    deadline = time.time() + 12
    while time.time() < deadline:
        app.processEvents()
        if window._player is not None and (window._player.duration or 0) > 8:
            break
        time.sleep(0.1)
    window.raise_()
    window.activateWindow()
    for _ in range(10):
        app.processEvents()
        time.sleep(0.1)
    overlay = window._gesture_overlay
    print("WINDOW_ACTIVE", window.isActiveWindow())
    print("WINDOWED_OVERLAY", overlay is not None and overlay.isVisible())
    if overlay is not None:
        before = float(window._player.time_pos or 0)
        QTest.mouseClick(overlay, Qt.LeftButton, pos=QPoint(200, 120))
        time.sleep(0.3)
        print("TAP_PAUSE", bool(window._player.pause))
        QTest.mousePress(overlay, Qt.LeftButton, pos=QPoint(100, 120))
        QTest.mouseRelease(overlay, Qt.LeftButton, pos=QPoint(320, 120))
        time.sleep(0.8)
        print("SWIPE_POS", round(before, 2), "->", round(float(window._player.time_pos or 0), 2))
    window.close()
    app.processEvents()
    print("CLOSED", True)


if __name__ == "__main__":
    main()
