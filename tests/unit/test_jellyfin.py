# -*- coding: utf-8 -*-
"""Jellyfin client tests."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.jellyfin import (  # noqa: E402
    JellyfinClient, JellyfinError, JellyfinItem, normalize_server,
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


class JellyfinTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_server("https://jf.example.com/"), "https://jf.example.com")
        self.assertEqual(normalize_server("ftp://jf.example.com"), "")

    def test_login_search_stream(self):
        login = {"AccessToken": "tok", "User": {"Id": "user1"}}
        search = {"Items": [{"Id": "song1", "Name": "Song", "Artists": ["Artist"],
                             "Album": "Album", "RunTimeTicks": 1800000000}]}
        client = JellyfinClient("https://jf.example.com", "user", "pass")

        def fake_urlopen(request, timeout=0):
            if "AuthenticateByName" in request.full_url:
                return _Response(login)
            return _Response(search)

        with patch("qianyu.core.jellyfin.urllib.request.urlopen", side_effect=fake_urlopen):
            self.assertTrue(client.login())
            songs = client.search_songs("Song")
        self.assertEqual(client.token, "tok")
        self.assertEqual(len(songs), 1)
        self.assertEqual(songs[0].duration, 180)
        self.assertIn("/Audio/song1/stream", client.stream_url(songs[0]))
        self.assertIn("api_key=tok", client.stream_url(songs[0]))

    def test_error(self):
        client = JellyfinClient("https://jf.example.com", "user", "pass")
        with patch("qianyu.core.jellyfin.urllib.request.urlopen",
                   side_effect=RuntimeError("boom")):
            with self.assertRaises(JellyfinError):
                client.login()

    def test_albums(self):
        albums = {"Items": [{"Id": "a1", "Name": "Album", "AlbumArtist": "Artist",
                             "ProductionYear": 2024, "ChildCount": 2}]}
        songs = {"Items": [{"Id": "s1", "Name": "Song", "Artists": ["Artist"],
                            "Album": "Album", "RunTimeTicks": 600000000}]}
        client = JellyfinClient("https://jf.example.com", "user", "pass",
                                token="tok", user_id="user1")
        with patch("qianyu.core.jellyfin.urllib.request.urlopen",
                   side_effect=[_Response(albums), _Response(songs)]):
            albums_result = client.albums()
            songs_result = client.album_songs("a1")
        self.assertEqual(len(albums_result), 1)
        self.assertEqual(albums_result[0].name, "Album")
        self.assertEqual(len(songs_result), 1)
        self.assertEqual(songs_result[0].duration, 60)

    def test_authorization_includes_token(self):
        seen = []

        def fake_urlopen(request, timeout=0):
            seen.append(request)
            return _Response({"Items": []})

        client = JellyfinClient("https://jf.example.com", "user", "pass",
                                token="tok", user_id="user1")
        with patch("qianyu.core.jellyfin.urllib.request.urlopen", side_effect=fake_urlopen):
            client.albums()
        auth = seen[0].get_header("Authorization")
        self.assertIn('Client="QianYu"', auth)
        self.assertIn('Token="tok"', auth)


if __name__ == "__main__":
    unittest.main(verbosity=2)
