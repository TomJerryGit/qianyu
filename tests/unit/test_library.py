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

from qianyu.library import Library, fuzzy_score, search_score  # noqa: E402
from qianyu.core.models import Track  # noqa: E402
from qianyu.core.pinyin import variants as pinyin_variants  # noqa: E402

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

    def test_fuzzy_score(self):
        track = Track(path="x.wav", title="Single Tone", artist="Test Artist",
                      album="Demo")
        self.assertGreater(fuzzy_score("singel", track), 0.5)
        self.assertEqual(fuzzy_score("single", track), 1.0)
        self.assertLess(fuzzy_score("zzzzzz", track), 0.5)

    def test_pinyin_and_ranking(self):
        full, initials = pinyin_variants("周杰伦")
        self.assertIn("zhoujielun", full)
        self.assertIn("zjl", initials)
        basic = Track(path="a.wav", title="稻香", artist="周杰伦")
        favorite = Track(path="b.wav", title="稻香", artist="周杰伦",
                         favorite=True, play_count=3)
        self.assertGreater(search_score("稻香", favorite),
                           search_score("稻香", basic))

    def test_pinyin_database_search(self):
        from contextlib import closing
        track = Track(path=str(self.music / "pinyin.wav"), title="稻香",
                      artist="周杰伦", album="魔杰座")
        with closing(self.library._connect()) as conn:
            Library._upsert(conn, track, 1.0)
            conn.commit()
        self.assertEqual(len(self.library.search("zjl")), 1)
        self.assertEqual(len(self.library.search("zhoujielun")), 1)
        self.assertEqual(len(self.library.search("daoxiang")), 1)

    def test_remove_missing(self):
        self.library.scan(self.music)
        (self.music / "gapless_a.wav").unlink()
        self.assertEqual(self.library.remove_missing(), 1)
        self.assertEqual(self.library.count(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
