# -*- coding: utf-8 -*-
"""Isolate memory growth: playback-only vs UI-churn-only."""
from __future__ import annotations

import os
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

MODE = os.environ.get("QIANYU_ISOLATE_MODE", "play")
SECONDS = int(os.environ.get("QIANYU_ISOLATE_SECONDS", "300"))
OUT = ROOT / "spike" / "out" / f"isolate_{MODE}.json"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-isolate-"))
    music = tmp / "music"
    music.mkdir()
    for name in ("single_tone.wav", "gapless_a.wav", "gapless_b.wav"):
        shutil.copy2(ROOT / "spike" / "fixtures" / name, music / name)
    library = Library(tmp / "library.db")
    library.scan(music)
    app = QApplication.instance() or QApplication([])
    window = MainWindow(Config(tmp / "config.json"),
                        engine=MpvEngine(ao="null", volume=0), data_dir=tmp)
    window.show()
    app.processEvents()
    process = psutil.Process()
    start = process.memory_info().rss / 1024 / 1024
    samples = []
    if MODE == "play":
        window._play_library_row(0)
    started = time.time()
    while time.time() - started < SECONDS:
        if MODE == "play":
            pass
        else:
            window._search.setText("a" if int(time.time() - started) % 4 < 2 else "")
            window._search_timer.stop()
            window._refresh_library()
            window._refresh_playlist()
            window._grid_toggle.setChecked(False)
        app.processEvents()
        time.sleep(0.25)
        if int(time.time() - started) % 60 == 0:
            rss = process.memory_info().rss / 1024 / 1024
            samples.append(round(rss, 1))
    end = process.memory_info().rss / 1024 / 1024
    print(f"ISOLATE mode={MODE} start={start:.1f} end={end:.1f} delta={end-start:.1f} samples={samples}")
    OUT.write_text(str({"mode": MODE, "start": start, "end": end, "delta": end - start, "samples": samples}), encoding="utf-8")
    window.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
