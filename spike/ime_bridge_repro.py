# -*- coding: utf-8 -*-
"""MpvEngine + Qt signal bridge reproduction."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"D:\qianyu") / "src"))

from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow

from qianyu.engine.mpv_engine import MpvEngine
from qianyu.ui.main_window import EngineBridge

app = QApplication(sys.argv)
bridge = EngineBridge()
bridge.event.connect(lambda event: None)
engine = MpvEngine(on_event=lambda event: bridge.event.emit(event), ao="null", volume=0)
window = QMainWindow()
window.setCentralWidget(QLineEdit("bridge test"))
window.show()
app.processEvents()
os._exit(0)
