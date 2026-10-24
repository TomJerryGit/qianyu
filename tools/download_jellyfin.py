# -*- coding: utf-8 -*-
"""Resume the Jellyfin Windows ZIP download with range requests."""
from __future__ import annotations

import time
import urllib.request
from pathlib import Path

TARGET = Path(r"D:\qianyu\tools\jellyfin.zip")
URL = ("https://sgp1.mirror.jellyfin.org/files/server/windows/stable/v12.3/amd64/"
       "jellyfin_12.3-amd64.zip")
SHA256 = "64b81a7b01b4dfb4ad3380a367cdeaf59878d9070c0d5e0cf84025e58ed3e853"
TOTAL = 208873113


def main() -> int:
    for attempt in range(30):
        have = TARGET.stat().st_size if TARGET.exists() else 0
        if have >= TOTAL:
            break
        headers = {"User-Agent": "QianYu", "Range": f"bytes={have}-"}
        request = urllib.request.Request(URL, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                with TARGET.open("ab") as handle:
                    while True:
                        chunk = response.read(256 * 1024)
                        if not chunk:
                            break
                        handle.write(chunk)
        except Exception as exc:
            print(f"retry {attempt} at {have}: {type(exc).__name__}: {exc}", flush=True)
            time.sleep(2)
    have = TARGET.stat().st_size if TARGET.exists() else 0
    print(f"download size {have}/{TOTAL}", flush=True)
    if have < TOTAL:
        return 1
    import hashlib
    digest = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    print(f"sha256 {digest}", flush=True)
    return 0 if digest.lower() == SHA256 else 1


if __name__ == "__main__":
    raise SystemExit(main())
