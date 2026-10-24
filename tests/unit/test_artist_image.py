# -*- coding: utf-8 -*-
"""Artist image cache tests with a mocked Deezer API."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.artist_image import cache_path, fetch_artist_image  # noqa: E402


class _Response:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


class ArtistImageTests(unittest.TestCase):
    def test_fetch_and_cache(self):
        root = Path(tempfile.mkdtemp(prefix="qy-artist-"))
        search = json.dumps({
            "data": [{"picture_xl": "https://img.example/artist.jpg"}]
        }).encode()
        image = b"\xff\xd8\xff" + b"x" * 100

        def fake_urlopen(request, timeout=0):
            return _Response(search if "search/artist" in request.full_url else image)

        with patch("qianyu.core.artist_image.urllib.request.urlopen", side_effect=fake_urlopen):
            path = fetch_artist_image("Coldplay", root)
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_bytes(), image)
        with patch("qianyu.core.artist_image.urllib.request.urlopen") as urlopen:
            again = fetch_artist_image("Coldplay", root)
        self.assertEqual(again, path)
        urlopen.assert_not_called()

    def test_bad_artist(self):
        self.assertIsNone(fetch_artist_image("", tempfile.mkdtemp()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
