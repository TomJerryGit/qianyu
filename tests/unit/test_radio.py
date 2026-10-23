# -*- coding: utf-8 -*-
"""Radio Browser parsing tests."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.radio import parse_stations, search_stations  # noqa: E402


class _Response:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._payload


class RadioTests(unittest.TestCase):
    def test_parse_dedupe_and_filter(self):
        stations = parse_stations([
            {"name": "Jazz One", "url_resolved": "https://radio.example/one",
             "country": "US", "tags": "jazz,chill", "bitrate": 128},
            {"name": "Duplicate", "url_resolved": "https://radio.example/one"},
            {"name": "Broken", "url_resolved": "not-a-url"},
        ])
        self.assertEqual(len(stations), 1)
        self.assertEqual(stations[0].name, "Jazz One")
        self.assertIn("jazz", stations[0].tags)
        self.assertEqual(stations[0].bitrate, 128)

    def test_search_request(self):
        payload = [{"name": "Test", "url_resolved": "http://radio.example/live"}]
        with patch("qianyu.core.radio.urllib.request.urlopen", return_value=_Response(payload)):
            result = search_stations("unique-test-query", limit=5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].url, "http://radio.example/live")


if __name__ == "__main__":
    unittest.main(verbosity=2)
