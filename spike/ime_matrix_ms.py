# -*- coding: utf-8 -*-
"""Run 100 cold starts with whatever Windows IME is current.

Usage:
  1. Press Win+Space and select 微软拼音.
  2. python spike\ime_matrix_ms.py
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\qianyu")
PY = ROOT / "tools" / "venv311" / "Scripts" / "python.exe"
SCRIPT = ROOT / "run_dev.py"
OUT = ROOT / "spike" / "out" / "ime_matrix_current.json"
RUNS = 100


def current_ime() -> str:
    try:
        return subprocess.check_output(
            ["powershell.exe", "-NoProfile", "-Command",
             "(Get-WinDefaultInputMethodOverride).Description"],
            text=True, timeout=15,
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    ime = current_ime()
    print("CURRENT_IME", ime, flush=True)
    if "搜狗" in ime:
        print("Please switch to Microsoft Pinyin with Win+Space first.", flush=True)
        return 2

    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "windows"
    env["QIANYU_NO_SINGLE_INSTANCE"] = "1"
    env.pop("QT_IM_MODULE", None)
    env.pop("QIANYU_NO_TRAY", None)

    results = []
    for index in range(1, RUNS + 1):
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
        results.append({"run": index, "exit": code,
                        "ms": round((time.perf_counter() - started) * 1000)})
        if code == 3221225477:
            print(f"CRASH run={index}", flush=True)
    crashes = sum(1 for item in results if item["exit"] == 3221225477)
    report = {"ime": ime, "runs": RUNS, "crashes": crashes, "results": results}
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"RESULT ime={ime} crashes={crashes}/{RUNS}", flush=True)
    return 0 if not crashes else 1


if __name__ == "__main__":
    raise SystemExit(main())
