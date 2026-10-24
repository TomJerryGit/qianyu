# -*- coding: utf-8 -*-
"""Curated radio preset tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.radio_presets import preset_stations  # noqa: E402


class RadioPresetTests(unittest.TestCase):
    def test_presets_valid(self):
        stations = preset_stations()
        self.assertGreaterEqual(len(stations), 6)
        urls = {station.url for station in stations}
        self.assertEqual(len(urls), len(stations))
        for station in stations:
            self.assertTrue(station.name)
            self.assertTrue(station.url.startswith("https://"), station.url)


if __name__ == "__main__":
    unittest.main(verbosity=2)
