# -*- coding: utf-8 -*-
"""Library tests: scan, tags, covers, search, incremental skip."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.library import Library  # noqa: E402

FIX = ROOT / "spike" / "fixtures"


@unittest.skipUnless((FIX / "single_tone.wav").exists(), "spike fixtures missing")
class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="qy-library-"))
        self.music = self.tmp / "music"
        self.music.mkdir()
        for name in ("single_tone.wav", "gapless_a.wav"):
            shutil.copy2(FIX / name, self.music / name)
        from PIL import Image

        Image.new("RGB", (32, 32), (10, 20, 30)).save(self.music / "cover.jpg")
        self.library = Library(self.tmp / "data" / "library.db")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_scan_and_cover(self):
        result = self.library.scan(self.music)
        self.assertEqual(result.added, 2)
        self.assertEqual(result.errors, 0)
        tracks = self.library.tracks()
        self.assertEqual(len(tracks), 2)
        self.assertTrue(all(t.cover.endswith("cover.jpg") for t in tracks))
        self.assertAlmostEqual(max(t.duration for t in tracks), 3.0, delta=0.2)

    def test_favorite_and_play_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "music"
            folder.mkdir()
            shutil.copy2(FIX / "single_tone.wav", folder / "tone.wav")
            library = Library(Path(tmp) / "lib.db")
            library.scan(folder)
            track = library.tracks()[0]
            library.set_favorite(track.path, True)
            library.mark_played(track.path)
            updated = library.get(track.path)
            self.assertTrue(updated.favorite)
            self.assertEqual(updated.play_count, 1)
            self.assertGreater(updated.last_played, 0)

    def test_incremental_and_search(self):
        self.library.scan(self.music)
        again = self.library.scan(self.music)
        self.assertEqual(again.added, 0)
        self.assertEqual(again.skipped, 2)
        self.assertEqual(len(self.library.search("single")), 1)

    def test_remove_missing(self):
        self.library.scan(self.music)
        (self.music / "gapless_a.wav").unlink()
        self.assertEqual(self.library.remove_missing(), 1)
        self.assertEqual(self.library.count(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
