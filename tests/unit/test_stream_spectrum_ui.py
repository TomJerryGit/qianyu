# -*- coding: utf-8 -*-
"""Progressive local/stream spectrum test (offscreen, no audio device)."""
from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.qt import QApplication  # noqa: E402
from qianyu.ui.now_playing import StreamSpectrumThread  # noqa: E402


class StreamSpectrumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_local_pcm_frames(self):
        fixture = ROOT / "spike" / "fixtures" / "single_tone.wav"
        if not fixture.exists():
            self.skipTest("fixture missing")
        try:
            import imageio_ffmpeg  # noqa: F401
        except Exception:
            self.skipTest("imageio-ffmpeg missing")
        levels = []
        thread = StreamSpectrumThread(str(fixture), live=False)
        thread.levels.connect(lambda values: levels.append(values))
        thread.start()
        deadline = time.time() + 12
        while time.time() < deadline and not levels:
            self.app.processEvents()
            time.sleep(0.05)
        thread.stop()
        thread.wait(5000)
        self.assertTrue(levels, "no spectrum levels produced")
        self.assertGreater(max(max(values) for values in levels if values), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
