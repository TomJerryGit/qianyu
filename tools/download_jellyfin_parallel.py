# -*- coding: utf-8 -*-
"""Parallel, resumable Jellyfin ZIP download."""
from __future__ import annotations

import hashlib
import json
import shutil
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

TARGET = Path(r"D:\qianyu\tools\jellyfin.zip")
PARTS = Path(r"D:\qianyu\tools\jellyfin.parts")
STATE = PARTS / "state.json"
URL = ("https://sgp1.mirror.jellyfin.org/files/server/windows/stable/v12.3/amd64/"
       "jellyfin_12.3-amd64.zip")
SHA256 = "64b81a7b01b4dfb4ad3380a367cdeaf59878d9070c0d5e0cf84025e58ed3e853"
TOTAL = 208873113
CHUNK = 8 * 1024 * 1024
COUNT = (TOTAL + CHUNK - 1) // CHUNK


def chunk_path(index: int) -> Path:
    return PARTS / f"{index:03d}.part"


def expected(index: int) -> int:
    return min(CHUNK, TOTAL - index * CHUNK)


def fetch(index: int) -> None:
    path = chunk_path(index)
    want = expected(index)
    if path.exists() and path.stat().st_size == want:
        return
    start = index * CHUNK
    end = start + want - 1
    for attempt in range(8):
        try:
            request = urllib.request.Request(
                URL, headers={"User-Agent": "QianYu", "Range": f"bytes={start}-{end}"}
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                data = response.read()
            if len(data) != want:
                raise IOError(f"chunk {index} got {len(data)} expected {want}")
            path.write_bytes(data)
            return
        except Exception as exc:
            print(f"retry {index}/{attempt}: {type(exc).__name__}: {exc}", flush=True)
            time.sleep(2)
    raise RuntimeError(f"chunk {index} failed")


def main() -> int:
    PARTS.mkdir(parents=True, exist_ok=True)
    done = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch, index): index for index in range(COUNT)}
        for future in as_completed(futures):
            future.result()
            done += 1
            if done % 4 == 0:
                print(f"chunks {done}/{COUNT}", flush=True)
    with TARGET.open("wb") as output:
        for index in range(COUNT):
            with chunk_path(index).open("rb") as part:
                shutil.copyfileobj(part, output, 1024 * 1024)
    digest = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    print(f"sha256 {digest}", flush=True)
    if digest.lower() != SHA256:
        print("HASH_MISMATCH", flush=True)
        return 1
    shutil.rmtree(PARTS, ignore_errors=True)
    print("DONE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
