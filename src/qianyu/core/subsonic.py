# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Subsonic-compatible remote library client.

Works with Navidrome, Airsonic, Gonic and other Subsonic API servers.
Jellyfin uses a different API and is not handled here.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass

USER_AGENT = "QianYu/0.9 (local media player)"
API_VERSION = "1.16.1"
CLIENT_NAME = "QianYu"


@dataclass(frozen=True)
class RemoteSong:
    id: str
    title: str
    artist: str = ""
    album: str = ""
    duration: float = 0.0
    cover_id: str = ""

    @property
    def display(self) -> str:
        details = " · ".join(part for part in (self.artist, self.album) if part)
        return f"{self.title} — {details}" if details else self.title


@dataclass(frozen=True)
class RemoteAlbum:
    id: str
    name: str
    artist: str = ""
    year: int = 0
    song_count: int = 0
    cover_id: str = ""

    @property
    def display(self) -> str:
        parts = [self.name]
        if self.artist:
            parts.append(self.artist)
        if self.year:
            parts.append(str(self.year))
        return " · ".join(parts)


def normalize_server(url: str) -> str:
    url = str(url or "").strip().rstrip("/")
    if not url:
        return ""
    if not url.lower().startswith(("http://", "https://")):
        return ""
    if url.lower().endswith("/rest"):
        url = url[:-5].rstrip("/")
    return url


class SubsonicError(RuntimeError):
    pass


class SubsonicClient:
    def __init__(self, server: str, username: str, password: str,
                 timeout: float = 10.0):
        self.server = normalize_server(server)
        self.username = str(username or "").strip()
        self.password = str(password or "")
        self.timeout = timeout
        self.salt = secrets.token_hex(8)

    @property
    def configured(self) -> bool:
        return bool(self.server and self.username and self.password)

    def _auth_params(self) -> dict[str, str]:
        token = hashlib.md5((self.password + self.salt).encode("utf-8")).hexdigest()
        return {
            "u": self.username,
            "t": token,
            "s": self.salt,
            "v": API_VERSION,
            "c": CLIENT_NAME,
            "f": "json",
        }

    def _url(self, method: str, **params) -> str:
        if not self.configured:
            raise SubsonicError("远程媒体库尚未配置")
        query = self._auth_params()
        query.update({key: str(value) for key, value in params.items() if value is not None})
        return f"{self.server}/rest/{method}.view?" + urllib.parse.urlencode(query)

    def _request(self, method: str, **params) -> dict:
        request = urllib.request.Request(self._url(method, **params),
                                         headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8", "replace"))
        except Exception as exc:
            raise SubsonicError(f"远程服务器请求失败：{type(exc).__name__}: {exc}") from exc
        body = payload.get("subsonic-response") if isinstance(payload, dict) else None
        if not isinstance(body, dict) or body.get("status") != "ok":
            message = body.get("error", {}).get("message") if isinstance(body, dict) else ""
            raise SubsonicError(f"远程服务器错误：{message or '未知错误'}")
        return body

    def ping(self) -> bool:
        self._request("ping")
        return True

    def search_songs(self, query: str, limit: int = 50) -> list[RemoteSong]:
        query = str(query or "").strip()
        if not query:
            return []
        body = self._request(
            "search3",
            query=query,
            songCount=max(1, min(int(limit), 100)),
            albumCount=0,
            artistCount=0,
        )
        result = body.get("searchResult3") or {}
        songs = result.get("song") or []
        if isinstance(songs, dict):
            songs = [songs]
        parsed: list[RemoteSong] = []
        for item in songs:
            if not isinstance(item, dict):
                continue
            song_id = str(item.get("id") or "").strip()
            if not song_id:
                continue
            try:
                duration = float(item.get("duration") or 0)
            except (TypeError, ValueError):
                duration = 0.0
            parsed.append(RemoteSong(
                id=song_id,
                title=str(item.get("title") or "Unknown").strip(),
                artist=str(item.get("artist") or "").strip(),
                album=str(item.get("album") or "").strip(),
                duration=duration,
                cover_id=str(item.get("coverArt") or "").strip(),
            ))
        return parsed

    def stream_url(self, song: RemoteSong) -> str:
        return self._url("stream", id=song.id)

    def albums(self, limit: int = 50, offset: int = 0,
               order: str = "alphabeticalByName") -> list[RemoteAlbum]:
        body = self._request(
            "getAlbumList2",
            type=order,
            size=max(1, min(int(limit), 100)),
            offset=max(0, int(offset)),
        )
        result = body.get("albumList2") or {}
        albums = result.get("album") or []
        if isinstance(albums, dict):
            albums = [albums]
        parsed: list[RemoteAlbum] = []
        for item in albums:
            if not isinstance(item, dict):
                continue
            album_id = str(item.get("id") or "").strip()
            if not album_id:
                continue
            try:
                year = int(item.get("year") or 0)
            except (TypeError, ValueError):
                year = 0
            try:
                song_count = int(item.get("songCount") or 0)
            except (TypeError, ValueError):
                song_count = 0
            parsed.append(RemoteAlbum(
                id=album_id,
                name=str(item.get("name") or "Unknown album").strip(),
                artist=str(item.get("artist") or "").strip(),
                year=year,
                song_count=song_count,
                cover_id=str(item.get("coverArt") or "").strip(),
            ))
        return parsed

    def album_songs(self, album_id: str) -> list[RemoteSong]:
        body = self._request("getAlbum", id=album_id)
        album = body.get("album") or {}
        songs = album.get("song") or []
        if isinstance(songs, dict):
            songs = [songs]
        parsed: list[RemoteSong] = []
        for item in songs:
            if not isinstance(item, dict):
                continue
            song_id = str(item.get("id") or "").strip()
            if not song_id:
                continue
            try:
                duration = float(item.get("duration") or 0)
            except (TypeError, ValueError):
                duration = 0.0
            parsed.append(RemoteSong(
                id=song_id,
                title=str(item.get("title") or "Unknown").strip(),
                artist=str(item.get("artist") or "").strip(),
                album=str(item.get("album") or album.get("name") or "").strip(),
                duration=duration,
                cover_id=str(item.get("coverArt") or "").strip(),
            ))
        return parsed

    def cover_url_for(self, cover_id: str) -> str:
        if not cover_id:
            return ""
        return self._url("getCoverArt", id=cover_id)

    def cover_url(self, song: RemoteSong) -> str:
        return self.cover_url_for(song.cover_id)
