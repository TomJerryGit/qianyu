# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Podcast discovery (iTunes Search API) and RSS episode parsing."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Iterable

USER_AGENT = "QianYu/0.9 (local media player)"
ITUNES_SEARCH = "https://itunes.apple.com/search"


@dataclass(frozen=True)
class Podcast:
    name: str
    feed_url: str
    artist: str = ""
    genre: str = ""
    artwork: str = ""
    description: str = ""
    episode_count: int = 0

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "feed_url": self.feed_url,
            "artist": self.artist,
            "genre": self.genre,
            "artwork": self.artwork,
            "description": self.description,
            "episode_count": self.episode_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Podcast | None":
        if not isinstance(data, dict):
            return None
        feed = _text(data.get("feed_url"))
        if not feed.lower().startswith(("http://", "https://")):
            return None
        return cls(
            name=_text(data.get("name")) or "Unknown podcast",
            feed_url=feed,
            artist=_text(data.get("artist")),
            genre=_text(data.get("genre")),
            artwork=_text(data.get("artwork")),
            description=_text(data.get("description")),
            episode_count=_int(data.get("episode_count")),
        )


@dataclass(frozen=True)
class Episode:
    title: str
    url: str
    podcast_name: str = ""
    published: str = ""
    duration: float = 0.0
    description: str = ""
    artwork: str = ""


def _text(value) -> str:
    return str(value or "").strip()


def _int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_duration(value) -> float:
    value = _text(value)
    if not value:
        return 0.0
    if ":" not in value:
        try:
            return float(value)
        except ValueError:
            return 0.0
    total = 0.0
    for part in value.split(":"):
        try:
            total = total * 60 + float(part)
        except ValueError:
            return 0.0
    return total


def parse_podcast_search(payload: Iterable[dict]) -> list[Podcast]:
    podcasts: list[Podcast] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        feed = _text(item.get("feedUrl"))
        if not feed.lower().startswith(("http://", "https://")) or feed in seen:
            continue
        seen.add(feed)
        podcasts.append(Podcast(
            name=_text(item.get("collectionName")) or _text(item.get("trackName")) or "Unknown podcast",
            feed_url=feed,
            artist=_text(item.get("artistName")),
            genre=_text(item.get("primaryGenreName")),
            artwork=_text(item.get("artworkUrl600") or item.get("artworkUrl100")),
            description=_text(item.get("description")),
            episode_count=_int(item.get("trackCount")),
        ))
    return podcasts


def search_podcasts(term: str, limit: int = 25, timeout: float = 8.0) -> list[Podcast]:
    term = term.strip()
    if not term:
        return []
    params = {
        "media": "podcast",
        "entity": "podcast",
        "term": term,
        "limit": str(max(1, min(int(limit), 50))),
        "country": "CN",
    }
    url = ITUNES_SEARCH + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"播客查询失败：{type(exc).__name__}: {exc}") from exc
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        raise RuntimeError("播客搜索返回格式错误")
    return parse_podcast_search(results)


def _find_text(node: ET.Element, names: tuple[str, ...], default: str = "") -> str:
    for child in node:
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag in names and (child.text or "").strip():
            return child.text.strip()
    return default


def _find_attr(node: ET.Element, name: str, attr: str) -> str:
    for child in node.iter():
        tag = child.tag.rsplit("}", 1)[-1].lower()
        if tag == name:
            value = child.attrib.get(attr)
            if value:
                return value
    return ""


def parse_feed(xml_text: str, playlist_limit: int = 100) -> tuple[str, list[Episode]]:
    """Return (podcast title, newest-first episodes) from an RSS document."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise RuntimeError(f"播客 RSS 解析失败：{exc}") from exc
    channel = root.find("channel")
    if channel is None:
        raise RuntimeError("播客 RSS 缺少 channel")
    podcast_name = _find_text(channel, ("title",), "Unknown podcast")
    artwork = _find_attr(channel, "image", "href") or _find_text(channel, ("url",))
    episodes: list[Episode] = []
    for item in channel.findall("item"):
        title = _find_text(item, ("title",), "Untitled episode")
        enclosure = item.find("enclosure")
        url = enclosure.attrib.get("url", "") if enclosure is not None else ""
        if not url:
            for child in item.iter():
                tag = child.tag.rsplit("}", 1)[-1].lower()
                if tag in ("content", "enclosure") and child.attrib.get("url"):
                    url = child.attrib["url"]
                    break
        if not url.lower().startswith(("http://", "https://")):
            continue
        duration = parse_duration(_find_text(item, ("duration",)))
        published = _find_text(item, ("pubdate",), "")
        try:
            published = parsedate_to_datetime(published).strftime("%Y-%m-%d")
        except (TypeError, ValueError):
            pass
        episodes.append(Episode(
            title=title,
            url=url,
            podcast_name=podcast_name,
            published=published,
            duration=duration,
            description=_find_text(item, ("description", "summary")),
            artwork=_find_attr(item, "image", "href") or artwork,
        ))
        if len(episodes) >= max(1, playlist_limit):
            break
    return podcast_name, episodes


def fetch_episodes(feed_url: str, limit: int = 100, timeout: float = 10.0) -> list[Episode]:
    feed_url = feed_url.strip()
    if not feed_url.lower().startswith(("http://", "https://")):
        raise RuntimeError("播客 feed 地址无效")
    request = urllib.request.Request(feed_url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read(8 * 1024 * 1024).decode("utf-8", "replace")
    except Exception as exc:
        raise RuntimeError(f"播客 RSS 下载失败：{type(exc).__name__}: {exc}") from exc
    return parse_feed(text, limit)[1]
