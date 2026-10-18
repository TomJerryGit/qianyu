# -*- coding: utf-8 -*-
"""20 fresh packaged starts with Windows platform; records 0xC0000005 crashes."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(r"D:\qianyu")
EXE = ROOT / "dist-pyside6" / "QianYu" / "QianYu.exe"
OUT = ROOT / "spike" / "out" / "cold_start_20.json"
LOG = ROOT / "spike" / "out" / "cold_start_20.log"


def main() -> int:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "windows"
    env["QIANYU_NO_SINGLE_INSTANCE"] = "1"
    if os.environ.get("QIANYU_FORCE_NO_TRAY") == "1":
        env["QIANYU_NO_TRAY"] = "1"
    else:
        env.pop("QIANYU_NO_TRAY", None)
    results = []
    with LOG.open("w", encoding="utf-8") as log:
        for index in range(1, 21):
            started = time.perf_counter()
            process = subprocess.Popen(
                [str(EXE), "--smoke"], env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                code = process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                code = -999
            elapsed = round((time.perf_counter() - started) * 1000)
            entry = {"run": index, "exit": code, "ms": elapsed}
            results.append(entry)
            log.write(json.dumps(entry) + "\n")
            log.flush()
            print(json.dumps(entry), flush=True)
    crashes = [entry for entry in results if entry["exit"] == 3221225477]
    report = {
        "total": len(results),
        "crashes_0xC0000005": len(crashes),
        "exit_codes": sorted({entry["exit"] for entry in results}),
        "min_ms": min(entry["ms"] for entry in results),
        "max_ms": max(entry["ms"] for entry in results),
        "avg_ms": round(sum(entry["ms"] for entry in results) / len(results)),
        "runs": results,
    }
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("COLD_START", json.dumps({k: report[k] for k in report if k != "runs"}), flush=True)
    return 0 if not crashes else 2


if __name__ == "__main__":
    raise SystemExit(main())
