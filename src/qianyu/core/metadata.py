# -*- coding: utf-8 -*-
"""Optional MusicBrainz metadata lookup (no API key, one request per click)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

USER_AGENT = "QianYu/0.9 (https://example.invalid/qianyu; local media player)"


@dataclass
class MetadataMatch:
    title: str
    artist: str
    album: str
    year: str
    score: int = 0
    release_id: str = ""


def lookup_recording(title: str, artist: str = "", timeout: float = 6.0) -> MetadataMatch | None:
    title = title.strip()
    if not title:
        return None
    query = f'recording:"{title}"'
    if artist.strip():
        query += f' AND artist:"{artist.strip()}"'
    url = "https://musicbrainz.org/ws/2/recording/?" + urllib.parse.urlencode({
        "query": query, "fmt": "json", "limit": "1",
    })
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    recordings = payload.get("recordings") or []
    if not recordings:
        return None
    recording = recordings[0]
    artist_name = ""
    credits = recording.get("artist-credit") or []
    if credits:
        artist_name = str(credits[0].get("name", ""))
    releases = recording.get("releases") or []
    album = str(releases[0].get("title", "")) if releases else ""
    release_id = str(releases[0].get("id", "")) if releases else ""
    year = ""
    if releases:
        date = str(releases[0].get("date", ""))
        year = date[:4]
    return MetadataMatch(
        title=str(recording.get("title", title)),
        artist=artist_name,
        album=album,
        year=year,
        score=int(recording.get("score", 0) or 0),
        release_id=release_id,
    )


def fetch_cover(release_id: str, timeout: float = 8.0) -> bytes | None:
    if not release_id:
        return None
    url = f"https://coverartarchive.org/release/{release_id}/front-500"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except Exception:
        return None
