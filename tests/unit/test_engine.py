# -*- coding: utf-8 -*-
"""Smoke test for the production engine wrapper (headless, ao=null)."""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    from qianyu.engine.mpv_engine import EngineState, MpvEngine  # noqa: E402
    ENGINE_AVAILABLE = True
    IMPORT_ERROR = None
except Exception as exc:  # libmpv or python-mpv missing
    EngineState = MpvEngine = None  # type: ignore[assignment]
    ENGINE_AVAILABLE = False
    IMPORT_ERROR = exc

FIXTURE = ROOT / "spike" / "fixtures" / "single_tone.wav"


@unittest.skipUnless(ENGINE_AVAILABLE, f"libmpv unavailable: {IMPORT_ERROR}")
class EngineTests(unittest.TestCase):
    @unittest.skipUnless(FIXTURE.exists(), "spike fixture missing")
    def test_play_and_seek(self):
        events = []
        engine = MpvEngine(on_event=events.append, ao="null", volume=0)
        try:
            engine.play(str(FIXTURE))
            self.assertTrue(engine.wait_until(lambda: engine.position > 0.2, timeout=10))
            self.assertAlmostEqual(engine.duration, 3.0, delta=0.2)
            engine.seek(1.5)
            self.assertTrue(engine.wait_until(lambda: engine.position >= 1.4, timeout=5))
            engine.set_eq([0] * 10)
            self.assertIn(engine.state, (EngineState.PLAYING, EngineState.PAUSED))
        finally:
            engine.shutdown()

    @unittest.skipUnless(FIXTURE.exists(), "spike fixture missing")
    def test_devices_and_pause(self):
        engine = MpvEngine(ao="null", volume=0)
        try:
            self.assertTrue(isinstance(engine.audio_devices, list))
            engine.play(str(FIXTURE))
            engine.wait_until(lambda: engine.position > 0.1, timeout=10)
            engine.toggle()
            self.assertTrue(engine.wait_until(lambda: engine.state == EngineState.PAUSED, timeout=3))
            engine.toggle()
        finally:
            engine.shutdown()

    @unittest.skipUnless((FIXTURE.parent / "gapless_a.wav").exists(), "spike fixtures missing")
    def test_queue_advances_without_reload(self):
        a = FIXTURE.parent / "gapless_a.wav"
        b = FIXTURE.parent / "gapless_b.wav"
        engine = MpvEngine(ao="null", volume=0)
        try:
            engine.set_queue([str(a), str(b)], 0)
            self.assertTrue(engine.wait_until(lambda: engine.queue_index == 0, timeout=10))
            self.assertTrue(engine.wait_until(lambda: engine.queue_index == 1, timeout=10))
            self.assertTrue(engine.wait_until(lambda: engine.duration > 1.5, timeout=5))
        finally:
            engine.shutdown()

    def test_audio_options(self):
        engine = MpvEngine(ao="null", volume=0)
        try:
            engine.set_replaygain("track")
            self.assertEqual(str(engine._mpv.replaygain), "track")
            engine.set_replaygain("album")
            self.assertEqual(str(engine._mpv.replaygain), "album")
            engine.set_audio_exclusive(True)
            self.assertTrue(bool(engine._mpv.audio_exclusive))
            engine.set_audio_exclusive(False)
            self.assertFalse(bool(engine._mpv.audio_exclusive))
        finally:
            engine.shutdown()

    @unittest.skipUnless((FIXTURE.parent / "test_resume.mp4").exists(), "resume fixture missing")
    def test_cue_ranges_advance(self):
        path = str(FIXTURE.parent / "test_resume.mp4")
        engine = MpvEngine(ao="null", volume=0)
        try:
            engine.set_queue([path, path], 0, ranges=[(0.0, 2.0), (4.0, 6.0)])
            self.assertTrue(engine.wait_until(lambda: engine.queue_index == 1, timeout=15))
            self.assertTrue(engine.wait_until(
                lambda: engine.position >= 4.0, timeout=10
            ))
        finally:
            engine.shutdown()


if __name__ == "__main__":
    unittest.main(verbosity=2)
