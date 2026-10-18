# -*- coding: utf-8 -*-
"""MpvEngine + minimal Qt window reproduction for the IME crash."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"D:\qianyu") / "src"))

from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow

from qianyu.engine.mpv_engine import MpvEngine

mode = os.environ.get("QIANYU_MPV_MODE", "engine")
engine = MpvEngine(ao="null", volume=0)
if mode in ("window", "both"):
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setCentralWidget(QLineEdit("mpv test"))
    window.show()
    app.processEvents()
os._exit(0)
