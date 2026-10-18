# -*- coding: utf-8 -*-
"""IME cold-start crash matrix (source build)."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(r"D:\qianyu")
PY = ROOT / "tools" / "venv311" / "Scripts" / "python.exe"
SCRIPT = ROOT / "run_dev.py"
OUT = ROOT / "spike" / "out" / "ime_matrix.json"


def run_condition(name: str, extra: dict[str, str], count: int = 50) -> dict:
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "windows"
    env["QIANYU_NO_SINGLE_INSTANCE"] = "1"
    env.pop("QT_IM_MODULE", None)
    env.pop("QIANYU_NO_TRAY", None)
    env.update(extra)
    results = []
    for index in range(1, count + 1):
        started = time.perf_counter()
        process = subprocess.Popen(
            [str(PY), str(SCRIPT), "--smoke"], env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            code = process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            code = -999
        elapsed = round((time.perf_counter() - started) * 1000)
        results.append({"run": index, "exit": code, "ms": elapsed})
        if code == 3221225477:
            print(f"{name}: CRASH run={index} ms={elapsed}", flush=True)
    crashes = sum(1 for item in results if item["exit"] == 3221225477)
    summary = {
        "name": name,
        "env": extra,
        "runs": count,
        "crashes": crashes,
        "avg_ms": round(sum(item["ms"] for item in results) / count),
        "results": results,
    }
    print(f"RESULT {name}: {crashes}/{count} crashes avg={summary['avg_ms']}ms", flush=True)
    return summary


def main() -> int:
    conditions = [
        ("default", {}),
        ("qt_im_module", {"QT_IM_MODULE": "qt"}),
        ("windows_explicit", {"QT_IM_MODULE": "windows"}),
        ("no_tray", {"QIANYU_NO_TRAY": "1"}),
        ("offscreen_control", {"QT_QPA_PLATFORM": "offscreen"}),
    ]
    report = {"conditions": []}
    for name, extra in conditions:
        count = 30 if name == "offscreen_control" else 50
        report["conditions"].append(run_condition(name, extra, count))
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("MATRIX_DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
