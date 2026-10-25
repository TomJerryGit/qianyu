# -*- coding: utf-8 -*-
"""Small deterministic performance gate for the library hot path."""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.library import Library  # noqa: E402

LIMITS = {
    "insert_10k_ms": 8000.0,
    "search_ms": 150.0,
    "tracks_query_ms": 500.0,
}
ROWS = 10_000


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="qy-perf-"))
    library = Library(tmp / "perf.db")
    rows = [
        (f"D:/perf/{index:05d}.flac", f"Track {index:05d}",
         f"Artist {index % 200}", f"Album {index % 1000}",
         180.0, index % 20, 0, "flac", 44100, 2, 900000, 0, time.time(), "")
        for index in range(ROWS)
    ]
    conn = library._connect()
    started = time.perf_counter()
    conn.executemany(
        """INSERT OR REPLACE INTO tracks(path,title,artist,album,duration,track_no,
           disc_no,codec,sample_rate,channels,bitrate,mtime,added_at,cover)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    insert_ms = (time.perf_counter() - started) * 1000
    conn.close()
    started = time.perf_counter()
    tracks = library.tracks()
    tracks_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    hits = library.search("Track 09999")
    search_ms = (time.perf_counter() - started) * 1000
    result = {
        "rows": len(tracks),
        "insert_10k_ms": round(insert_ms, 1),
        "tracks_query_ms": round(tracks_ms, 1),
        "search_ms": round(search_ms, 1),
        "search_hits": len(hits),
    }
    failures = []
    for key, limit in LIMITS.items():
        if result[key] > limit:
            failures.append(f"{key}={result[key]} > {limit}")
    result["limits"] = LIMITS
    result["ok"] = not failures
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failures:
        print("PERF_FAIL " + "; ".join(failures))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
