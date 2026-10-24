# -*- coding: utf-8 -*-
"""WASAPI loopback helper tests (no device capture)."""
from __future__ import annotations

import array
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.wasapi_loopback import convert_float32_to_i16  # noqa: E402


class WasapiHelperTests(unittest.TestCase):
    def test_float32_downmix(self):
        floats = array.array("f", [0.5, 0.5, -0.5, -0.5, 0.0, 0.0])
        pcm = convert_float32_to_i16(floats.tobytes(), channels=2, factor=1)
        samples = array.array("h")
        samples.frombytes(pcm)
        self.assertEqual(len(samples), 3)
        self.assertGreater(samples[0], 16000)
        self.assertLess(samples[1], -16000)
        self.assertEqual(samples[2], 0)

    def test_factor(self):
        floats = array.array("f", [1.0, -1.0, 0.5, 0.5, 0.0, 0.0])
        pcm = convert_float32_to_i16(floats.tobytes(), channels=2, factor=2)
        self.assertEqual(len(pcm), 2 * 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
