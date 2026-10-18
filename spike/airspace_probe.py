# -*- coding: utf-8 -*-
"""Airspace probe: can a Qt widget overlay an mpv child window?

The video is embedded with --wid into a native QWidget. A red Qt label is
placed on top. If the native child paints above Qt, the label disappears in a
real screen capture even though QWidget.grab() still contains it.
"""
import ctypes
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageGrab

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mpv_loader  # noqa: F401,E402
import mpv  # noqa: E402

OUT = HERE / "out"
VIDEO = "av://lavfi:testsrc2=size=1280x720:rate=30:duration=10"


def main():
    from PyQt5.QtCore import QPoint, Qt
    from PyQt5.QtWidgets import QApplication, QLabel, QWidget

    app = QApplication.instance() or QApplication([])
    host = QWidget()
    host.setWindowTitle("airspace probe")
    host.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
    host.resize(1280, 720)
    host.move(80, 80)
    host.setAttribute(Qt.WA_NativeWindow, True)
    host.setStyleSheet("background:#101010;")
    overlay = QLabel("QT OVERLAY", host)
    overlay.setStyleSheet("background:rgb(255,0,0);color:white;font-size:22px;padding:8px;")
    overlay.move(30, 30)
    overlay.resize(300, 46)
    host.show()
    host.raise_()
    host.activateWindow()
    app.processEvents()
    time.sleep(0.8)
    hwnd = int(host.winId())
    user32 = ctypes.windll.user32
    user32.SetForegroundWindow(hwnd)
    user32.BringWindowToTop(hwnd)
    time.sleep(0.8)

    player = mpv.MPV(
        wid=str(hwnd), vo="gpu", ao="null", idle="yes", keep_open="yes",
        osc="no", length="10",
    )
    player.play(VIDEO)
    player.wait_until_playing(timeout=10)
    time.sleep(1.5)
    host.raise_()
    host.activateWindow()
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)

    top_left = host.mapToGlobal(QPoint(0, 0))
    box = (top_left.x(), top_left.y(), top_left.x() + host.width(), top_left.y() + host.height())
    screen = OUT / "airspace_screen.png"
    ImageGrab.grab(bbox=box).save(str(screen))
    qt = OUT / "airspace_qt_grab.png"
    host.grab().save(str(qt))

    region = np.asarray(Image.open(screen).convert("RGB").crop((30, 30, 330, 76)))
    red = ((region[:, :, 0] > 200) & (region[:, :, 1] < 60) & (region[:, :, 2] < 60)).mean()
    print("HWND", hwnd, "FOREGROUND", user32.GetForegroundWindow())
    print("SCREEN", screen, "RED_FRACTION", round(float(red), 4))
    print("QT_GRAB", qt)
    print("SUB_TEXT", player._get_property("sub-text"))
    player.terminate()
    host.close()
    app.processEvents()


if __name__ == "__main__":
    main()
