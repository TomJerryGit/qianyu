# -*- coding: utf-8 -*-
"""Probe a temporary Jellyfin server startup API."""
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\qianyu")
SERVER = ROOT / "tools" / "jellyfin-server" / "jellyfin" / "jellyfin.exe"
DATA = ROOT / "tools" / "jellyfin-data"
CONFIG = ROOT / "tools" / "jellyfin-config"
CACHE = ROOT / "tools" / "jellyfin-cache"
LOGS = ROOT / "tools" / "jellyfin-logs"
BASE = "http://127.0.0.1:8096"


def main() -> int:
    for path in (DATA, CONFIG, CACHE, LOGS):
        path.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [str(SERVER), "--datadir", str(DATA), "--configdir", str(CONFIG),
         "--cachedir", str(CACHE), "--logdir", str(LOGS)],
        cwd=str(SERVER.parent), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(40):
            try:
                with urllib.request.urlopen(BASE + "/System/Info/Public", timeout=2) as response:
                    print("PUBLIC", response.status, response.read(500).decode("utf-8", "replace"))
                    break
            except Exception as exc:
                time.sleep(1)
        else:
            print("SERVER_NOT_READY")
            return 2
        ready = False
        for _ in range(60):
            try:
                with urllib.request.urlopen(BASE + "/Startup/Configuration", timeout=3) as response:
                    print("STARTUP_READY", response.status,
                          response.read(300).decode("utf-8", "replace"))
                    ready = True
                    break
            except urllib.error.HTTPError as exc:
                if exc.code != 503:
                    print("STARTUP_HTTP", exc.code)
                    break
                time.sleep(1)
            except Exception:
                time.sleep(1)
        print("READY", ready)
        for endpoint in ("/swagger/v1/swagger.json", "/openapi/v1.json",
                         "/Startup/User", "/Startup/RemoteAccess", "/Startup/Complete"):
            try:
                with urllib.request.urlopen(BASE + endpoint, timeout=3) as response:
                    print(endpoint, response.status, response.read(300).decode("utf-8", "replace"))
            except urllib.error.HTTPError as exc:
                print(endpoint, "HTTP", exc.code, exc.read(200).decode("utf-8", "replace"))
            except Exception as exc:
                print(endpoint, "ERR", type(exc).__name__, exc)
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
