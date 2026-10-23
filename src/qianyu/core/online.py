# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Optional online lyrics lookup (LRCLIB)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

USER_AGENT = "QianYu/0.9 (local media player)"


def fetch_lyrics(title: str, artist: str = "", timeout: float = 6.0) -> str | None:
    title = title.strip()
    if not title:
        return None
    params = {"track_name": title}
    if artist.strip():
        params["artist_name"] = artist.strip()
    url = "https://lrclib.net/api/search?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            results = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(results, list):
        return None
    for item in results:
        synced = item.get("syncedLyrics")
        if synced:
            return str(synced)
        plain = item.get("plainLyrics")
        if plain:
            return "\n".join(f"[00:00.00]{line}" for line in str(plain).splitlines())
    return None
