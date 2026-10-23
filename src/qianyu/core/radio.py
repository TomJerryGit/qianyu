# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Public internet-radio discovery via the Radio Browser API.

Radio Browser is a community directory of publicly available radio streams.
No API key is required. Playback itself is handled by libmpv.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable

USER_AGENT = "QianYu/0.9 (local media player)"
API_ROOTS = (
    "https://de1.api.radio-browser.info/json",
    "https://de2.api.radio-browser.info/json",
    "https://nl1.api.radio-browser.info/json",
    "https://at1.api.radio-browser.info/json",
)
_CACHE: dict[tuple[str, str, int], list["RadioStation"]] = {}


@dataclass(frozen=True)
class RadioStation:
    name: str
    url: str
    country: str = ""
    tags: str = ""
    codec: str = ""
    bitrate: int = 0
    homepage: str = ""
    favicon: str = ""

    @property
    def display(self) -> str:
        details = " · ".join(part for part in (self.country, self.tags) if part)
        return f"{self.name} — {details}" if details else self.name

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "url": self.url,
            "country": self.country,
            "tags": self.tags,
            "codec": self.codec,
            "bitrate": self.bitrate,
            "homepage": self.homepage,
            "favicon": self.favicon,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RadioStation | None":
        if not isinstance(data, dict):
            return None
        url = _clean(data.get("url"))
        if not url.lower().startswith(("http://", "https://")):
            return None
        return cls(
            name=_clean(data.get("name")) or "Unknown station",
            url=url,
            country=_clean(data.get("country")),
            tags=_clean(data.get("tags")),
            codec=_clean(data.get("codec")),
            bitrate=int(data.get("bitrate") or 0),
            homepage=_clean(data.get("homepage")),
            favicon=_clean(data.get("favicon")),
        )


def _clean(value) -> str:
    return str(value or "").strip()


def parse_stations(payload: Iterable[dict]) -> list[RadioStation]:
    stations: list[RadioStation] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        url = _clean(item.get("url_resolved") or item.get("url"))
        if not url.lower().startswith(("http://", "https://")):
            continue
        if url in seen:
            continue
        seen.add(url)
        try:
            bitrate = int(item.get("bitrate") or 0)
        except (TypeError, ValueError):
            bitrate = 0
        stations.append(RadioStation(
            name=_clean(item.get("name")) or "Unknown station",
            url=url,
            country=_clean(item.get("country")),
            tags=_clean(item.get("tags")).replace(",", " · "),
            codec=_clean(item.get("codec")),
            bitrate=bitrate,
            homepage=_clean(item.get("homepage")),
            favicon=_clean(item.get("favicon")),
        ))
    return stations


def search_stations(keyword: str, country: str = "", limit: int = 50,
                    timeout: float = 8.0) -> list[RadioStation]:
    keyword = keyword.strip()
    if not keyword:
        return []
    key = (keyword.casefold(), country.strip().casefold(), int(limit))
    if key in _CACHE:
        return list(_CACHE[key])
    params = {
        "name": keyword,
        "limit": str(max(1, min(int(limit), 100))),
        "hidebroken": "true",
        "order": "clickcount",
        "reverse": "true",
    }
    if country.strip():
        params["countrycode"] = country.strip().upper()
    query = urllib.parse.urlencode(params)
    payload = None
    last_error: Exception | None = None
    for root in API_ROOTS:
        request = urllib.request.Request(f"{root}/stations/search?{query}",
                                         headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:
            last_error = exc
            continue
    if payload is None:
        raise RuntimeError(
            f"网络电台查询失败：{type(last_error).__name__}: {last_error}"
        ) from last_error
    if not isinstance(payload, list):
        raise RuntimeError("网络电台返回格式错误")
    stations = parse_stations(payload)
    _CACHE[key] = stations
    if len(_CACHE) > 32:
        _CACHE.pop(next(iter(_CACHE)))
    return list(stations)
