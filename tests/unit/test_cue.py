# -*- coding: utf-8 -*-
"""CUE parser test."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.cue import parse_cue  # noqa: E402
from qianyu.library import Library  # noqa: E402


class CueTests(unittest.TestCase):
    def test_parse_single_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            shutil.copy2(ROOT / "spike" / "fixtures" / "single_tone.wav", folder / "album.wav")
            cue = folder / "album.cue"
            cue.write_text(
                'PERFORMER "Artist"\nTITLE "Album"\n'
                'FILE "album.wav" WAVE\n'
                '  TRACK 01 AUDIO\n    TITLE "One"\n    INDEX 01 00:00:00\n'
                '  TRACK 02 AUDIO\n    TITLE "Two"\n    INDEX 01 00:01:00\n',
                encoding="utf-8",
            )
            sheet = parse_cue(cue)
            self.assertEqual(sheet.title, "Album")
            self.assertEqual(sheet.performer, "Artist")
            self.assertEqual(len(sheet.tracks), 2)
            self.assertEqual(sheet.tracks[0].title, "One")
            self.assertEqual(sheet.tracks[0].start, 0.0)
            self.assertAlmostEqual(sheet.tracks[1].start, 1.0)
            self.assertGreater(sheet.tracks[1].end, 2.0)
            self.assertEqual(sheet.tracks[0].path, str((folder / "album.wav").resolve()))

    def test_multi_file_cue_and_library_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for name in ("one.wav", "two.wav"):
                shutil.copy2(ROOT / "spike" / "fixtures" / "single_tone.wav", folder / name)
            cue = folder / "multi.cue"
            cue.write_text(
                'PERFORMER "Artist"\nTITLE "Multi"\n'
                'FILE "one.wav" WAVE\n  TRACK 01 AUDIO\n    TITLE "One"\n    INDEX 01 00:00:00\n'
                'FILE "two.wav" WAVE\n  TRACK 02 AUDIO\n    TITLE "Two"\n    INDEX 01 00:00:00\n',
                encoding="utf-8",
            )
            sheet = parse_cue(cue)
            self.assertEqual(len(sheet.tracks), 2)
            self.assertNotEqual(sheet.tracks[0].path, sheet.tracks[1].path)
            self.assertGreater(sheet.tracks[0].end, 2.0)
            self.assertGreater(sheet.tracks[1].end, 2.0)

            library = Library(folder / "lib.db")
            result = library.scan(folder)
            tracks = library.tracks()
            self.assertEqual(len(tracks), 2)
            self.assertEqual({t.album for t in tracks}, {"Multi"})
            self.assertTrue(all(t.cue_path for t in tracks))
            self.assertEqual(len(library.search("One")), 1)
            self.assertEqual(library.remove_missing(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
