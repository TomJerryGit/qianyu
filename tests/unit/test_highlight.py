# -*- coding: utf-8 -*-
"""Search highlighting helpers."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.ui.highlight import match_spans, query_tokens  # noqa: E402


class HighlightTests(unittest.TestCase):
    def test_spans(self):
        spans = match_spans("Jay Chou - 稻香", ["jay", "稻香"])
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0], (0, 3))
        self.assertEqual(spans[1], (11, 13))

    def test_overlap_merge(self):
        spans = match_spans("abcabc", ["abc", "bc"])
        self.assertEqual(spans, [(0, 6)])

    def test_tokens(self):
        self.assertEqual(query_tokens("周杰伦 稻香"), ["周杰伦", "稻香"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
