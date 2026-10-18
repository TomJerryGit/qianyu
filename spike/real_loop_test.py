# -*- coding: utf-8 -*-
"""Run the real Qt event loop briefly, then shut down normally."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"D:\qianyu")
sys.path.insert(0, str(ROOT / "src"))

from qianyu.qt import QApplication, QTimer
from qianyu.config import Config
from qianyu.engine.mpv_engine import MpvEngine
from qianyu.ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])
tmp = Path(tempfile.mkdtemp(prefix="qy-loop-"))
engine = MpvEngine(ao="null", volume=0)
window = MainWindow(Config(tmp / "config.json"), engine=engine, data_dir=tmp)
window.show()
QTimer.singleShot(2500, app.quit)
code = app.exec()
window.shutdown()
engine.shutdown()
sys.exit(code)
