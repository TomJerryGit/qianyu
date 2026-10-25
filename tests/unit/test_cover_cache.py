# -*- coding: utf-8 -*-
"""Remote cover cache tests."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.cover_cache import fetch_cover  # noqa: E402


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size=-1):
        data = b"\xff\xd8\xffcover"
        return data if size < 0 else data[:size]


class CoverCacheTests(unittest.TestCase):
    def test_fetch_and_reuse(self):
        root = Path(tempfile.mkdtemp(prefix="qy-cover-"))
        url = "https://img.example/cover.jpg"
        with patch("qianyu.core.net.urllib.request.urlopen",
                   return_value=_Response()):
            path = fetch_cover(url, root)
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())
        with patch("qianyu.core.net.urllib.request.urlopen") as urlopen:
            again = fetch_cover(url, root)
        self.assertEqual(again, path)
        urlopen.assert_not_called()

    def test_invalid(self):
        self.assertIsNone(fetch_cover("file:///tmp/x", tempfile.mkdtemp()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
