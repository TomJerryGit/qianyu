# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Optional ListenBrainz scrobbling.

Only local music tracks are submitted. Streams, podcasts and radio are excluded.
The feature is disabled by default and requires a user token.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from dataclasses import dataclass

from .models import Track
from .secure_store import SecretStore

LISTENBRAINZ_URL = "https://api.listenbrainz.org/1/submit-listens"
USER_AGENT = "QianYu/0.9 (local media player)"
MIN_DURATION = 30.0
MAX_THRESHOLD = 240.0


def should_scrobble(duration: float, position: float) -> bool:
    if duration < MIN_DURATION or position <= 0:
        return False
    threshold = min(MAX_THRESHOLD, duration * 0.5)
    return position >= threshold


def build_listen_payload(track: Track, listened_at: int | None = None) -> dict | None:
    title = str(track.title or "").strip()
    artist = str(track.artist or "").strip()
    if not title or not artist:
        return None
    metadata = {
        "artist_name": artist,
        "track_name": title,
        "additional_info": {
            "media_player": "QianYu",
            "submission_client": "QianYu",
        },
    }
    if track.album:
        metadata["release_name"] = str(track.album)
    if track.duration:
        metadata["additional_info"]["duration_ms"] = int(track.duration * 1000)
    return {
        "listen_type": "single",
        "payload": [{
            "listened_at": int(listened_at or time.time()),
            "track_metadata": metadata,
        }],
    }


def submit_listen(payload: dict, token: str, timeout: float = 8.0) -> bool:
    token = str(token or "").strip()
    if not token or not isinstance(payload, dict):
        return False
    request = urllib.request.Request(
        LISTENBRAINZ_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= int(response.status) < 300
    except Exception:
        return False


def is_scrobbleable_track(track: Track | None) -> bool:
    if track is None:
        return False
    path = str(track.path or "")
    if not path or path.lower().startswith(("http://", "https://")):
        return False
    if str(track.album or "") == "播客":
        return False
    return bool(str(track.title or "").strip() and str(track.artist or "").strip())


@dataclass
class _ListenState:
    path: str
    started_at: float


class ListenBrainzScrobbler:
    def __init__(self, config):
        self._config = config
        self._secrets = SecretStore(config)
        self._token = self._secrets.get("listenbrainz_token")
        self._state: _ListenState | None = None
        self._submitted = False
        self._lock = threading.Lock()

    def reload(self) -> None:
        self._token = self._secrets.get("listenbrainz_token")
        self.stop()

    def track_started(self, track: Track | None) -> None:
        with self._lock:
            self._submitted = False
            self._state = _ListenState(str(track.path), time.time()) if track is not None else None

    def stop(self) -> None:
        with self._lock:
            self._state = None
            self._submitted = False

    def tick(self, track: Track | None, position: float, duration: float) -> None:
        if track is None or not bool(self._config.get("listenbrainz_enabled", False)):
            return
        token = self._token
        if not token or not is_scrobbleable_track(track):
            return
        if not should_scrobble(float(duration or 0), float(position or 0)):
            return
        with self._lock:
            if self._submitted:
                return
            if self._state is None or self._state.path != str(track.path):
                self._state = _ListenState(str(track.path), time.time())
            self._submitted = True
        payload = build_listen_payload(track)
        if payload is None:
            return
        threading.Thread(
            target=submit_listen,
            args=(payload, token),
            name="qianyu-listenbrainz",
            daemon=True,
        ).start()
