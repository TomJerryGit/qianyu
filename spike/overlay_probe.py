# -*- coding: utf-8 -*-
"""Probe: can a separate top-level translucent Qt window sit above mpv's wid?"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtGui import QColor, QPainter  # noqa: E402
from PyQt5.QtWidgets import QApplication, QWidget  # noqa: E402

from qianyu.config import Config  # noqa: E402
from qianyu.ui.video_window import VideoWindow  # noqa: E402


class Overlay(QWidget):
    def __init__(self, target):
        super().__init__(target)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setGeometry(target.frameGeometry())
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 0, 0, 90))
        painter.setPen(Qt.white)
        painter.drawText(20, 30, "QT TOP-LEVEL OVERLAY")


def main():
    app = QApplication([])
    window = VideoWindow(config=Config(Path.home() / ".qianyu_overlay_test.json"), ao="null")
    window.setGeometry(120, 120, 960, 600)
    window.show()
    window.open_path(str(ROOT / "spike" / "fixtures" / "test_resume.mp4"))
    for _ in range(30):
        app.processEvents()
        time.sleep(0.1)
    overlay = Overlay(window)
    overlay.show()
    for _ in range(20):
        app.processEvents()
        time.sleep(0.1)
    time.sleep(1)
    screen = app.primaryScreen()
    screen.grabWindow(0).save(str(ROOT / "spike" / "out" / "overlay_probe.png"))
    print("OVERLAY_VISIBLE", overlay.isVisible(), overlay.geometry().getRect())
    window.close()
    overlay.close()
    app.quit()


if __name__ == "__main__":
    main()
