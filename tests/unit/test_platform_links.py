# -*- coding: utf-8 -*-
"""Platform deep-link tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.platform_links import platform_names, search_url  # noqa: E402


class PlatformLinkTests(unittest.TestCase):
    def test_urls(self):
        self.assertEqual(
            search_url("Spotify", "周杰伦"),
            "https://open.spotify.com/search/%E5%91%A8%E6%9D%B0%E4%BC%A6",
        )
        self.assertIn("%E5%91%A8%E6%9D%B0%E4%BC%A6", search_url("Deezer", "周杰伦"))
        self.assertIn("YouTube", " ".join(platform_names()))

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            search_url("unknown", "x")
        with self.assertRaises(ValueError):
            search_url("Spotify", "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
