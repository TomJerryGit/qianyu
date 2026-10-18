# -*- coding: utf-8 -*-
"""Airspace probe v2: capture the window directly instead of relying on focus."""
import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mpv_loader  # noqa: F401,E402
import mpv  # noqa: E402

OUT = HERE / "out"
VIDEO = "av://lavfi:testsrc2=size=1280x720:rate=30:duration=10"

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, ctypes.c_uint]


def print_window(hwnd: int, path: Path) -> bool:
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return False
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    old = gdi32.SelectObject(mem, bmp)
    ok = user32.PrintWindow(hwnd, mem, 2)  # PW_RENDERFULLCONTENT
    class BIH(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD),
        ]
    bi = BIH()
    bi.biSize = ctypes.sizeof(BIH)
    bi.biWidth = w
    bi.biHeight = -h
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.SelectObject(mem, old)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    frame = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)[:, :, 2::-1]
    Image.fromarray(frame.copy(), "RGB").save(path)
    return bool(ok)


def main():
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QLabel, QWidget

    app = QApplication.instance() or QApplication([])
    host = QWidget()
    host.setWindowTitle("airspace probe")
    host.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
    host.resize(1280, 720)
    host.setAttribute(Qt.WA_NativeWindow, True)
    host.setStyleSheet("background:#101010;")
    overlay = QLabel("QT OVERLAY", host)
    overlay.setStyleSheet("background:rgb(255,0,0);color:white;font-size:22px;padding:8px;")
    overlay.move(30, 30)
    overlay.resize(300, 46)
    host.show()
    app.processEvents()
    time.sleep(0.8)
    hwnd = int(host.winId())

    player = mpv.MPV(wid=str(hwnd), vo="gpu", ao="null", idle="yes", keep_open="yes", osc="no", length="10")
    player.play(VIDEO)
    player.wait_until_playing(timeout=10)
    time.sleep(1.5)
    # HWND_TOPMOST = -1; SWP_SHOWWINDOW = 0x40
    user32.SetWindowPos(hwnd, -1, 80, 80, 1280, 720, 0x0040)
    time.sleep(1.0)

    print_path = OUT / "airspace_printwindow.png"
    ok = print_window(hwnd, print_path)
    print("PRINTWINDOW", ok, print_path)

    shot = app.primaryScreen().grabWindow(hwnd)
    shot.save(str(OUT / "airspace_qscreen.png"))
    print("QSCREEN", OUT / "airspace_qscreen.png", shot.width(), shot.height())

    qt = OUT / "airspace_qt_grab.png"
    host.grab().save(str(qt))
    print("QT_GRAB", qt)

    region = np.asarray(Image.open(print_path).convert("RGB").crop((30, 30, 330, 76)))
    red = ((region[:, :, 0] > 200) & (region[:, :, 1] < 60) & (region[:, :, 2] < 60)).mean()
    print("RED_FRACTION", round(float(red), 4))

    player.terminate()
    host.close()
    app.processEvents()


if __name__ == "__main__":
    main()
