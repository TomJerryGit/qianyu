# -*- coding: utf-8 -*-
"""Run mpv-engine IME reproductions repeatedly."""
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(r"D:\qianyu")
PY = ROOT / "tools" / "venv311" / "Scripts" / "python.exe"
SCRIPT = ROOT / "spike" / "ime_mpv_repro.py"
OUT = ROOT / "spike" / "out" / "ime_mpv.json"
RUNS = 50


def main() -> int:
    env_base = dict(os.environ)
    env_base["QT_QPA_PLATFORM"] = "windows"
    env_base.pop("QT_IM_MODULE", None)
    report = {}
    for mode in ("engine", "window"):
        crashes = 0
        env = dict(env_base)
        env["QIANYU_MPV_MODE"] = mode
        for _ in range(RUNS):
            process = subprocess.Popen(
                [str(PY), str(SCRIPT)], env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            try:
                code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                code = -999
            if code == 3221225477:
                crashes += 1
        report[mode] = {"runs": RUNS, "crashes": crashes}
        print("MPV_COMPONENT", mode, report[mode], flush=True)
        OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
