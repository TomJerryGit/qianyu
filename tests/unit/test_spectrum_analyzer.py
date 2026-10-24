# -*- coding: utf-8 -*-
"""Real spectrum analyzer tests (PCM path)."""
from __future__ import annotations

import array
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.spectrum_analyzer import analyze_pcm  # noqa: E402
from qianyu.core.spectrum_analyzer import BANDS  # noqa: E402


class SpectrumAnalyzerTests(unittest.TestCase):
    def test_sine_peak(self):
        sample_rate = 8000
        samples = array.array(
            "h",
            (int(10000 * math.sin(2 * math.pi * 440 * i / sample_rate))
             for i in range(sample_rate)),
        )
        frames = analyze_pcm(samples.tobytes())
        self.assertGreater(len(frames), 0)
        levels = frames[5][1]
        self.assertEqual(len(levels), BANDS)
        peak = max(range(len(levels)), key=lambda index: levels[index])
        self.assertTrue(8 <= peak <= 16, peak)
        self.assertGreater(levels[peak], 0.2)

    def test_silence(self):
        frames = analyze_pcm(b"\x00\x00" * 4096)
        self.assertGreater(len(frames), 0)
        self.assertTrue(all(level < 0.2 for level in frames[0][1]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
