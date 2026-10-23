# -*- coding: utf-8 -*-
"""Subsonic-compatible remote library tests."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.subsonic import (  # noqa: E402
    RemoteSong, SubsonicClient, SubsonicError, normalize_server,
)


class _Response:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


class SubsonicTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_server("https://music.example.com/rest/"),
                         "https://music.example.com")
        self.assertEqual(normalize_server("http://host:4533"), "http://host:4533")
        self.assertEqual(normalize_server("ftp://host"), "")

    def test_search_and_stream(self):
        payload = {"subsonic-response": {
            "status": "ok",
            "searchResult3": {"song": [
                {"id": "42", "title": "Song", "artist": "Artist",
                 "album": "Album", "duration": 180, "coverArt": "c1"},
                {"id": "", "title": "bad"},
            ]},
        }}
        client = SubsonicClient("https://music.example.com", "user", "pass")
        client.salt = "abc"
        with patch("qianyu.core.subsonic.urllib.request.urlopen",
                   return_value=_Response(payload)):
            songs = client.search_songs("Song")
        self.assertEqual(len(songs), 1)
        self.assertEqual(songs[0].id, "42")
        self.assertEqual(songs[0].duration, 180)
        stream = client.stream_url(songs[0])
        self.assertIn("/rest/stream.view", stream)
        self.assertIn("id=42", stream)
        self.assertIn("u=user", stream)
        self.assertIn("s=abc", stream)
        self.assertNotIn("pass", stream)

    def test_error(self):
        payload = {"subsonic-response": {
            "status": "failed", "error": {"message": "Wrong credentials"},
        }}
        client = SubsonicClient("https://music.example.com", "user", "pass")
        with patch("qianyu.core.subsonic.urllib.request.urlopen",
                   return_value=_Response(payload)):
            with self.assertRaises(SubsonicError):
                client.ping()


if __name__ == "__main__":
    unittest.main(verbosity=2)
