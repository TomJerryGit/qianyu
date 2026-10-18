# -*- coding: utf-8 -*-
"""Smoke for fullscreen top-level gesture overlay (V12 workaround)."""
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

SAMPLE = ROOT / "spike" / "fixtures" / "test_resume.mp4"


def main() -> None:
    app = QApplication([])
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-gesture-"))
    window = VideoWindow(config=Config(tmp / "config.json"), ao="null")
    window.show()
    window.open_path(str(SAMPLE))
    deadline = time.time() + 12
    while time.time() < deadline:
        app.processEvents()
        if window._player is not None and (window._player.duration or 0) > 8:
            break
        time.sleep(0.1)

    window._full_btn.click()
    app.processEvents()
    time.sleep(0.5)
    overlay = window._gesture_overlay
    print("FULLSCREEN", window._fullscreen, "OVERLAY", overlay is not None)

    if overlay is not None:
        before = float(window._player.time_pos or 0)
        QTest.mouseClick(overlay, Qt.LeftButton, pos=QPoint(400, 300))
        time.sleep(0.4)
        print("TAP_PAUSE", bool(window._player.pause))

        QTest.mousePress(overlay, Qt.LeftButton, pos=QPoint(200, 300))
        QTest.mouseRelease(overlay, Qt.LeftButton, pos=QPoint(420, 300))
        time.sleep(0.8)
        print("SWIPE_POS", round(before, 2), "->", round(float(window._player.time_pos or 0), 2))

        QTest.mouseDClick(overlay, Qt.LeftButton, pos=QPoint(600, 300))
        app.processEvents()
        time.sleep(0.4)
        print("DBLCLICK_FULLSCREEN", window._fullscreen)

    window.close()
    app.processEvents()
    print("CLOSED", True)


if __name__ == "__main__":
    main()
