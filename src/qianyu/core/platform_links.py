# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Legal platform search links.

QianYu does not scrape or stream these catalogs. It only opens the official
platform search page in the user's browser.
"""
from __future__ import annotations

import urllib.parse

PLATFORM_LINKS = {
    "Spotify": "https://open.spotify.com/search/{query}",
    "Apple Music": "https://music.apple.com/us/search?term={query}",
    "YouTube Music": "https://music.youtube.com/search?q={query}",
    "网易云音乐": "https://music.163.com/#/search/m/?s={query}",
    "QQ 音乐": "https://y.qq.com/portal/search.html#page=1&t=song&w={query}",
    "Bandcamp": "https://bandcamp.com/search?q={query}",
    "Internet Archive": "https://archive.org/search?query={query}",
    "Jamendo": "https://www.jamendo.com/search/tracks?q={query}",
    "Deezer": "https://www.deezer.com/search/{query}",
}


def platform_names() -> list[str]:
    return list(PLATFORM_LINKS)


def search_url(platform: str, query: str) -> str:
    template = PLATFORM_LINKS.get(str(platform))
    if template is None:
        raise ValueError(f"未知平台：{platform}")
    query = str(query or "").strip()
    if not query:
        raise ValueError("搜索关键词为空")
    return template.format(query=urllib.parse.quote(query, safe=""))
