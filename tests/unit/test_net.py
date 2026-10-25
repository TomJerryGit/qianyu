# -*- coding: utf-8 -*-
"""Network guard tests."""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.net import UnsafeUrl, read_limited, safe_http_url  # noqa: E402


class NetGuardTests(unittest.TestCase):
    def test_safe_urls(self):
        self.assertEqual(safe_http_url("https://example.com/a.jpg"),
                         "https://example.com/a.jpg")
        self.assertEqual(safe_http_url("http://127.0.0.1:8096/Items/1/Images"),
                         "http://127.0.0.1:8096/Items/1/Images")

    def test_rejects(self):
        for value in ("file:///C:/Windows/win.ini", "ftp://x/y",
                      "javascript:alert(1)", "https://user:pass@example.com/x",
                      "https:///missing-host", ""):
            with self.assertRaises(UnsafeUrl, msg=value):
                safe_http_url(value)

    def test_read_limited(self):
        self.assertEqual(read_limited(io.BytesIO(b"abc"), 3), b"abc")
        self.assertEqual(read_limited(io.BytesIO(b"abcd"), 3), b"")


if __name__ == "__main__":
    unittest.main(verbosity=2)
