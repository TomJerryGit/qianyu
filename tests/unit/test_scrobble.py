# -*- coding: utf-8 -*-
"""ListenBrainz payload and threshold tests."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.models import Track  # noqa: E402
from qianyu.core.scrobble import (  # noqa: E402
    ListenBrainzScrobbler, build_listen_payload, is_scrobbleable_track,
    should_scrobble, submit_listen,
)


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ScrobbleTests(unittest.TestCase):
    def test_threshold(self):
        self.assertTrue(should_scrobble(100, 50))
        self.assertFalse(should_scrobble(100, 49))
        self.assertTrue(should_scrobble(1000, 240))
        self.assertFalse(should_scrobble(20, 20))

    def test_payload(self):
        track = Track(path=r"C:\Music\a.flac", title="Song", artist="Artist",
                      album="Album", duration=180)
        payload = build_listen_payload(track, listened_at=123)
        self.assertEqual(payload["listen_type"], "single")
        listen = payload["payload"][0]
        self.assertEqual(listen["listened_at"], 123)
        self.assertEqual(listen["track_metadata"]["track_name"], "Song")
        self.assertEqual(listen["track_metadata"]["artist_name"], "Artist")
        self.assertEqual(listen["track_metadata"]["release_name"], "Album")
        self.assertEqual(listen["track_metadata"]["additional_info"]["duration_ms"], 180000)

    def test_scrobbleable(self):
        local = Track(path=r"C:\Music\a.flac", title="Song", artist="Artist")
        stream = Track(path="https://example.com/a.mp3", title="Song", artist="Artist",
                       album="播客")
        self.assertTrue(is_scrobbleable_track(local))
        self.assertFalse(is_scrobbleable_track(stream))
        self.assertFalse(is_scrobbleable_track(None))

    def test_submit_request(self):
        payload = build_listen_payload(
            Track(path=r"C:\Music\a.flac", title="Song", artist="Artist"), listened_at=1
        )
        captured = {}

        def fake_urlopen(request, timeout=0):
            captured["headers"] = request.headers
            captured["body"] = json.loads(request.data.decode())
            return _Response()

        with patch("qianyu.core.scrobble.urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertTrue(submit_listen(payload, "token"))
        self.assertEqual(captured["headers"]["Authorization"], "Token token")
        self.assertEqual(captured["body"]["payload"][0]["track_metadata"]["track_name"], "Song")

    def test_controller_submits_once(self):
        class Config:
            values = {"listenbrainz_enabled": True, "listenbrainz_token": "token"}

            def get(self, key, default=None):
                return self.values.get(key, default)

        track = Track(path=r"C:\Music\a.flac", title="Song", artist="Artist", duration=100)
        scrobbler = ListenBrainzScrobbler(Config())
        scrobbler.track_started(track)

        class ImmediateThread:
            def __init__(self, target, args=(), **_kwargs):
                target(*args)

            def start(self):
                pass

        with patch("qianyu.core.scrobble.threading.Thread", ImmediateThread), \
                patch("qianyu.core.scrobble.submit_listen", return_value=True) as submit:
            scrobbler.tick(track, 50, 100)
            scrobbler.tick(track, 60, 100)
        self.assertEqual(submit.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
