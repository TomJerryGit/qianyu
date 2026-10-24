# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Artist photo lookup through the public Deezer search API.

The image is only displayed/cached locally for the current artist; it is not
redistributed. Artwork rights remain with the original rights holders.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "QianYu/0.9 (local media player)"
DEEZER_SEARCH = "https://api.deezer.com/search/artist"


def cache_path(cache_dir: str | Path, artist: str) -> Path:
    key = hashlib.sha1(str(artist).strip().casefold().encode("utf-8")).hexdigest()[:24]
    return Path(cache_dir) / f"artist_{key}.jpg"


def fetch_artist_image(artist: str, cache_dir: str | Path,
                       timeout: float = 8.0) -> Path | None:
    artist = str(artist or "").strip()
    if not artist:
        return None
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = cache_path(root, artist)
    if path.is_file() and path.stat().st_size > 0:
        return path
    query = urllib.parse.urlencode({"q": artist, "limit": 1})
    request = urllib.request.Request(f"{DEEZER_SEARCH}?{query}",
                                     headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list) or not data:
            return None
        picture = data[0].get("picture_xl") or data[0].get("picture_big")
        if not picture:
            return None
        image_request = urllib.request.Request(str(picture),
                                               headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(image_request, timeout=timeout) as response:
            image = response.read()
        if not image:
            return None
        temp = path.with_suffix(".part")
        temp.write_bytes(image)
        temp.replace(path)
        return path
    except Exception:
        return None
