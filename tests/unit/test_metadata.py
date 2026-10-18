# -*- coding: utf-8 -*-
"""Metadata lookup parsing test (no network)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.metadata import lookup_recording  # noqa: E402


class _Response:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


class MetadataTests(unittest.TestCase):
    def test_parse_recording(self):
        payload = {
            "recordings": [{
                "title": "Song", "score": 98,
                "artist-credit": [{"name": "Artist"}],
                "releases": [{"title": "Album", "date": "2020-01-01"}],
            }]
        }
        with patch("qianyu.core.metadata.urllib.request.urlopen", return_value=_Response(payload)):
            match = lookup_recording("Song", "Artist")
        self.assertEqual(match.title, "Song")
        self.assertEqual(match.artist, "Artist")
        self.assertEqual(match.album, "Album")
        self.assertEqual(match.year, "2020")
        self.assertEqual(match.score, 98)


if __name__ == "__main__":
    unittest.main(verbosity=2)
