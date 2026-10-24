# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Cache remote cover images locally."""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

USER_AGENT = "QianYu/0.9 (local media player)"


def fetch_cover(url: str, cache_dir: str | Path, timeout: float = 6.0) -> Path | None:
    url = str(url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return None
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:24]
    path = root / f"cover_{key}.jpg"
    if path.is_file() and path.stat().st_size > 0:
        return path
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
        if not data:
            return None
        temp = path.with_suffix(".part")
        temp.write_bytes(data)
        temp.replace(path)
        return path
    except Exception:
        return None
