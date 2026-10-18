# -*- coding: utf-8 -*-
"""Local production acceptance: startup, 10k library, UI paths, screenshots."""
from __future__ import annotations

import json
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
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-accept-"))
    process = psutil.Process()
    memory_start = process.memory_info().rss / 1024 / 1024

    library = Library(tmp / "library.db")
    conn = library._connect()
    rows = [
        (f"D:/fake/{i:05d}.flac", f"Track {i:05d}", f"Artist {i % 200}",
         f"Album {i % 1000}", 180.0 + i % 30, i % 20, 0, "flac",
         44100, 2, 900000, 0, time.time(), "")
        for i in range(10_000)
    ]
    conn.executemany(
        """INSERT OR REPLACE INTO tracks(path,title,artist,album,duration,track_no,disc_no,
           codec,sample_rate,channels,bitrate,mtime,added_at,cover)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    conn.close()

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet((ROOT / "src" / "qianyu" / "ui" / "theme" / "dark.qss").read_text(encoding="utf-8"))
    config = Config(tmp / "config.json")

    t0 = time.perf_counter()
    engine = MpvEngine(ao="null", volume=0)
    window = MainWindow(config, engine=engine, data_dir=tmp)
    init_ms = (time.perf_counter() - t0) * 1000
    memory_window = process.memory_info().rss / 1024 / 1024

    t0 = time.perf_counter()
    window._refresh_library()
    refresh_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    hits = library.search("Track 09999")
    search_ms = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    window.show()
    app.processEvents()
    show_ms = (time.perf_counter() - t0) * 1000
    time.sleep(0.2)
    app.processEvents()
    window.grab().save(str(ROOT / "spike" / "out" / "acceptance_10k.png"))

    window._grid_toggle.setChecked(True)
    app.processEvents()
    grid_count = window._album_view._grid.count()
    window._grid_toggle.setChecked(False)
    window._queue_toggle.setChecked(True)
    queue_hidden = not window._playlist_view.isVisible()
    window._queue_toggle.setChecked(False)

    memory_end = process.memory_info().rss / 1024 / 1024
    report = {
        "library_tracks": len(window._tracks),
        "startup_mainwindow_ms": round(init_ms, 1),
        "show_ms": round(show_ms, 1),
        "refresh_10k_ms": round(refresh_ms, 1),
        "search_ms": round(search_ms, 1),
        "search_hits": len(hits),
        "grid_groups": grid_count,
        "queue_hidden": queue_hidden,
        "memory_start_mb": round(memory_start, 1),
        "memory_window_mb": round(memory_window, 1),
        "memory_end_mb": round(memory_end, 1),
        "screenshot": "spike/out/acceptance_10k.png",
    }
    print("ACCEPTANCE", json.dumps(report, ensure_ascii=False))
    (ROOT / "spike" / "out" / "acceptance.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    window.shutdown()
    engine.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
