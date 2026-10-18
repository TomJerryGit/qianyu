# -*- coding: utf-8 -*-
"""8-hour soak: UI + queue + search + grid + CUE, RSS sampling."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import faulthandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import psutil  # noqa: E402
from qianyu.qt import QApplication  # noqa: E402

from qianyu.config import Config  # noqa: E402
from qianyu.engine.mpv_engine import MpvEngine  # noqa: E402
from qianyu.library import Library  # noqa: E402
from qianyu.ui.main_window import MainWindow  # noqa: E402

DURATION = int(os.environ.get("QIANYU_SOAK_SECONDS", 8 * 3600))
LOG = ROOT / "spike" / "out" / os.environ.get("QIANYU_SOAK_LOG", "soak_8h.log")
RESULT = ROOT / "spike" / "out" / os.environ.get("QIANYU_SOAK_RESULT", "soak_8h.json")


def log(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}"
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def main() -> int:
    faulthandler.dump_traceback_later(30, repeat=True)
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-soak8-"))
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
    window._play_library_row(0)
    process = psutil.Process()
    start = process.memory_info().rss / 1024 / 1024
    started = time.time()
    log(f"START pid={process.pid} rss={start:.1f}MB duration={DURATION}s")
    cycle = 0
    next_sample = started + 300
    while time.time() - started < DURATION:
        cycle += 1
        if cycle <= 10 or cycle % 100 == 0:
            log(f"CYCLE {cycle} begin")
        window._play_library_row(cycle % max(1, len(window._tracks)))
        if cycle <= 10:
            log(f"CYCLE {cycle} playing")
        app.processEvents()
        window._search.setText("a" if cycle % 2 else "")
        window._search_timer.stop()
        window._refresh_library()
        if cycle <= 10:
            log(f"CYCLE {cycle} refreshed")
        window._grid_toggle.setChecked(cycle % 10 == 0)
        app.processEvents()
        window._grid_toggle.setChecked(False)
        app.processEvents()
        time.sleep(2)
        if cycle <= 10:
            log(f"CYCLE {cycle} done")
        if time.time() >= next_sample:
            rss = process.memory_info().rss / 1024 / 1024
            log(f"SAMPLE cycle={cycle} rss={rss:.1f}MB uptime={int(time.time()-started)}s")
            next_sample += 300
    end = process.memory_info().rss / 1024 / 1024
    log(f"END rss={end:.1f}MB delta={end-start:.1f}MB cycles={cycle}")
    RESULT.write_text(json.dumps({
        "start_mb": round(start, 1), "end_mb": round(end, 1),
        "delta_mb": round(end - start, 1), "cycles": cycle,
        "duration_s": int(time.time() - started),
    }, indent=2), encoding="utf-8")
    window.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
