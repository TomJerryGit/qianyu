# -*- coding: utf-8 -*-
"""Short soak: UI event loop + playback queue + memory sampling."""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psutil  # noqa: E402
from qianyu.qt import QApplication  # noqa: E402

from qianyu.config import Config  # noqa: E402
from qianyu.engine.mpv_engine import MpvEngine  # noqa: E402
from qianyu.library import Library  # noqa: E402
from qianyu.ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-soak-"))
    music = tmp / "music"
    music.mkdir()
    for name in ("single_tone.wav", "gapless_a.wav", "gapless_b.wav"):
        shutil.copy2(ROOT / "spike" / "fixtures" / name, music / name)
    library = Library(tmp / "library.db")
    library.scan(music)
    app = QApplication.instance() or QApplication([])
    config = Config(tmp / "config.json")
    engine = MpvEngine(ao="null", volume=0)
    window = MainWindow(config, engine=engine, data_dir=tmp)
    window.show()
    app.processEvents()
    window._play_library_row(0)
    process = psutil.Process()
    start = process.memory_info().rss / 1024 / 1024
    peak = start
    deadline = time.time() + 60
    while time.time() < deadline:
        app.processEvents()
        peak = max(peak, process.memory_info().rss / 1024 / 1024)
        time.sleep(0.1)
    end = process.memory_info().rss / 1024 / 1024
    print(f"SOAK start_mb={start:.1f} end_mb={end:.1f} peak_mb={peak:.1f} "
          f"state={engine.state} position={engine.position:.1f}")
    window.shutdown()
    engine.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
