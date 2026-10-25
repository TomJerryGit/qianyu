# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Small network input guards shared by online features.

The application intentionally allows private/LAN hosts (local Jellyfin and
Navidrome servers).  It only rejects non-HTTP schemes, embedded credentials and
obviously malformed URLs; callers must still bound response sizes and timeouts.
"""
from __future__ import annotations

import urllib.parse
import urllib.request

DEFAULT_MAX_BYTES = 8 * 1024 * 1024
USER_AGENT = "QianYu/0.9 (local media player)"


class UnsafeUrl(ValueError):
    pass


def safe_http_url(url: str) -> str:
    """Return a normalized http(s) URL or raise UnsafeUrl."""
    text = str(url or "").strip()
    if not text:
        raise UnsafeUrl("URL 为空")
    if any(ord(char) < 32 or char == " " for char in text):
        raise UnsafeUrl("URL 含控制字符")
    parsed = urllib.parse.urlsplit(text)
    if parsed.scheme.lower() not in ("http", "https"):
        raise UnsafeUrl("只允许 http/https URL")
    if not parsed.hostname:
        raise UnsafeUrl("URL 缺少主机名")
    if parsed.username or parsed.password:
        raise UnsafeUrl("URL 不得包含用户名/密码")
    return text


def read_limited(response, max_bytes: int = DEFAULT_MAX_BYTES) -> bytes:
    """Read at most max_bytes; return empty bytes when the limit is exceeded."""
    limit = max(1, int(max_bytes))
    data = response.read(limit + 1)
    if len(data) > limit:
        return b""
    return data


def fetch_limited(url: str, timeout: float = 8.0,
                  max_bytes: int = DEFAULT_MAX_BYTES,
                  headers: dict | None = None) -> bytes:
    """Fetch an http(s) resource with a hard response-size limit."""
    target = safe_http_url(url)
    request = urllib.request.Request(
        target,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return read_limited(response, max_bytes)
