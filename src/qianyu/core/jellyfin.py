# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Jellyfin remote library client."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

USER_AGENT = "QianYu/0.9 (local media player)"
DEVICE_ID = "qianyu-windows"
TICKS_PER_SECOND = 10_000_000


@dataclass(frozen=True)
class JellyfinItem:
    id: str
    title: str
    artist: str = ""
    album: str = ""
    duration: float = 0.0


@dataclass(frozen=True)
class JellyfinAlbum:
    id: str
    name: str
    artist: str = ""
    year: int = 0
    song_count: int = 0


def normalize_server(url: str) -> str:
    url = str(url or "").strip().rstrip("/")
    if not url.lower().startswith(("http://", "https://")):
        return ""
    return url


class JellyfinError(RuntimeError):
    pass


class JellyfinClient:
    def __init__(self, server: str, username: str = "", password: str = "",
                 token: str = "", user_id: str = "", timeout: float = 10.0):
        self.server = normalize_server(server)
        self.username = str(username or "").strip()
        self.password = str(password or "")
        self.token = str(token or "")
        self.user_id = str(user_id or "")
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.server)

    def _auth_header(self) -> str:
        return (
            f'MediaBrowser Client="QianYu", Device="Windows", '
            f'DeviceId="{DEVICE_ID}", Version="0.9.0"'
        )

    def _request(self, path: str, params: dict | None = None,
                 body: dict | None = None, auth: bool = True) -> dict:
        if not self.configured:
            raise JellyfinError("Jellyfin 服务器尚未配置")
        query = urllib.parse.urlencode(params or {})
        url = f"{self.server}{path}" + (f"?{query}" if query else "")
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "X-Emby-Authorization": self._auth_header(),
        }
        if auth and self.token:
            headers["X-Emby-Token"] = self.token
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers,
                                         method="POST" if body is not None else "GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8", "replace")
                return json.loads(raw) if raw.strip() else {}
        except Exception as exc:
            raise JellyfinError(f"Jellyfin 请求失败：{type(exc).__name__}: {exc}") from exc

    def login(self) -> bool:
        if not (self.server and self.username):
            raise JellyfinError("Jellyfin 用户名/服务器未配置")
        body = self._request(
            "/Users/AuthenticateByName",
            body={"Username": self.username, "Pw": self.password},
            auth=False,
        )
        token = str(body.get("AccessToken") or "").strip()
        user = body.get("User") or {}
        user_id = str(user.get("Id") or "").strip()
        if not token or not user_id:
            raise JellyfinError("Jellyfin 登录失败：未返回 token")
        self.token = token
        self.user_id = user_id
        return True

    def search_songs(self, query: str, limit: int = 50) -> list[JellyfinItem]:
        query = str(query or "").strip()
        if not query:
            return []
        if not self.token or not self.user_id:
            self.login()
        body = self._request(
            f"/Users/{self.user_id}/Items",
            params={
                "searchTerm": query,
                "IncludeItemTypes": "Audio",
                "Recursive": "true",
                "Fields": "Artists,Album,RunTimeTicks",
                "Limit": max(1, min(int(limit), 100)),
                "SortBy": "SortName",
                "SortOrder": "Ascending",
            },
        )
        return self._parse_items(body)

    def albums(self, limit: int = 50) -> list[JellyfinAlbum]:
        if not self.token or not self.user_id:
            self.login()
        body = self._request(
            f"/Users/{self.user_id}/Items",
            params={
                "IncludeItemTypes": "MusicAlbum",
                "Recursive": "true",
                "Fields": "AlbumArtist,ProductionYear,ChildCount",
                "Limit": max(1, min(int(limit), 100)),
                "SortBy": "SortName",
                "SortOrder": "Ascending",
            },
        )
        items = body.get("Items") or []
        result: list[JellyfinAlbum] = []
        if not isinstance(items, list):
            return result
        for item in items:
            if not isinstance(item, dict):
                continue
            album_id = str(item.get("Id") or "").strip()
            if not album_id:
                continue
            try:
                year = int(item.get("ProductionYear") or 0)
            except (TypeError, ValueError):
                year = 0
            try:
                count = int(item.get("ChildCount") or 0)
            except (TypeError, ValueError):
                count = 0
            result.append(JellyfinAlbum(
                id=album_id,
                name=str(item.get("Name") or "Unknown album").strip(),
                artist=str(item.get("AlbumArtist") or "").strip(),
                year=year,
                song_count=count,
            ))
        return result

    def album_songs(self, album_id: str) -> list[JellyfinItem]:
        if not self.token or not self.user_id:
            self.login()
        body = self._request(
            f"/Users/{self.user_id}/Items",
            params={
                "ParentId": album_id,
                "IncludeItemTypes": "Audio",
                "Recursive": "true",
                "Fields": "Artists,Album,RunTimeTicks",
                "SortBy": "ParentIndexNumber,IndexNumber,SortName",
                "SortOrder": "Ascending",
            },
        )
        return self._parse_items(body)

    def _parse_items(self, body: dict) -> list[JellyfinItem]:
        items = body.get("Items") or []
        if not isinstance(items, list):
            return []
        result: list[JellyfinItem] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("Id") or "").strip()
            if not item_id:
                continue
            artists = item.get("Artists") or []
            artist = ", ".join(str(value) for value in artists if value) if isinstance(artists, list) else ""
            try:
                duration = float(item.get("RunTimeTicks") or 0) / TICKS_PER_SECOND
            except (TypeError, ValueError):
                duration = 0.0
            result.append(JellyfinItem(
                id=item_id,
                title=str(item.get("Name") or "Unknown").strip(),
                artist=artist,
                album=str(item.get("Album") or "").strip(),
                duration=duration,
            ))
        return result

    def stream_url(self, item: JellyfinItem) -> str:
        query = urllib.parse.urlencode({
            "static": "true",
            "api_key": self.token,
        })
        return f"{self.server}/Audio/{urllib.parse.quote(item.id)}/stream?{query}"

    def cover_url(self, item: JellyfinItem) -> str:
        query = urllib.parse.urlencode({"api_key": self.token})
        return f"{self.server}/Items/{urllib.parse.quote(item.id)}/Images/Primary?{query}"
