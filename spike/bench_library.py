# -*- coding: utf-8 -*-
"""0.9 performance baseline: 10k-row library + 100-track queue.

Run:  QT_QPA_PLATFORM=offscreen python spike/bench_library.py
"""
from __future__ import annotations

import json
import math
import struct
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PyQt5.QtWidgets import QApplication, QTableView  # noqa: E402

from qianyu.library import Library  # noqa: E402
from qianyu.ui.track_model import TrackTableModel  # noqa: E402

OUT = ROOT / "spike" / "out"
OUT.mkdir(exist_ok=True)


def make_wav(path: Path, seconds: float = 0.2, rate: int = 24000) -> None:
    frames = int(rate * seconds)
    data = b"".join(
        struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(frames)
    )
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(data)


def bench_library(tmp: Path) -> dict:
    library = Library(tmp / "bench.db")
    conn = library._connect()
    rows = [
        (f"D:/fake/{i:05d}.flac", f"Track {i:05d}", f"Artist {i % 200}", f"Album {i % 1000}",
         180.0 + i % 30, i % 20, 0, "flac", 44100, 2, 900000, 0, time.time(), "")
        for i in range(10_000)
    ]
    t0 = time.perf_counter()
    conn.executemany(
        """INSERT OR REPLACE INTO tracks(path,title,artist,album,duration,track_no,disc_no,
           codec,sample_rate,channels,bitrate,mtime,added_at,cover)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    insert_ms = (time.perf_counter() - t0) * 1000
    conn.close()

    t0 = time.perf_counter()
    tracks = library.tracks()
    all_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    hits = library.search("Track 09999")
    search_ms = (time.perf_counter() - t0) * 1000

    app = QApplication.instance() or QApplication([])
    model = TrackTableModel(tracks)
    view = QTableView()
    view.setModel(model)
    view.resize(1000, 700)
    view.show()
    app.processEvents()
    t0 = time.perf_counter()
    model.set_tracks(tracks)
    app.processEvents()
    refresh_ms = (time.perf_counter() - t0) * 1000
    view.close()

    return {
        "rows": len(tracks),
        "insert_10k_ms": round(insert_ms, 1),
        "tracks_query_ms": round(all_ms, 1),
        "search_ms": round(search_ms, 1),
        "search_hits": len(hits),
        "model_refresh_ms": round(refresh_ms, 1),
    }


def bench_queue(tmp: Path) -> dict:
    try:
        from qianyu.engine.mpv_engine import MpvEngine
    except Exception as exc:
        return {"status": "skipped", "reason": f"{type(exc).__name__}: {exc}"}

    folder = tmp / "tracks"
    folder.mkdir()
    paths = []
    for i in range(100):
        path = folder / f"{i:03d}.wav"
        make_wav(path)
        paths.append(str(path))

    engine = MpvEngine(ao="null", volume=0)
    seen = set()
    last = [0.0]
    t0 = time.perf_counter()

    def on_event(event):
        if event.kind == "index":
            seen.add(int(event.value))
            last[0] = time.perf_counter() - t0

    engine._on_event = on_event
    try:
        engine.set_speed(4.0)
        engine.set_queue(paths, 0)
        ok = engine.wait_until(lambda: 99 in seen, timeout=30)
        elapsed = time.perf_counter() - t0
        return {
            "status": "ok" if ok else "timeout",
            "tracks": len(paths),
            "indices_seen": len(seen),
            "reached_99": 99 in seen,
            "elapsed_s": round(elapsed, 2),
            "last_index_at_s": round(last[0], 2),
        }
    finally:
        engine.shutdown()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory(prefix="qy-bench-") as tmp:
        tmp_path = Path(tmp)
        report = {
            "library": bench_library(tmp_path),
            "queue": bench_queue(tmp_path),
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    (OUT / "bench.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
