# -*- coding: utf-8 -*-
"""Tag write guard and duplicate detection tests."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.tagging import write_tags  # noqa: E402
from qianyu.library import Library  # noqa: E402

FIX = ROOT / "spike" / "fixtures"


class TaggingTests(unittest.TestCase):
    def test_wav_tag_write_is_rejected_and_db_update_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "music"
            folder.mkdir()
            source = folder / "tone.wav"
            shutil.copy2(FIX / "single_tone.wav", source)
            with self.assertRaises(ValueError):
                write_tags(str(source), {"title": "New Title", "artist": "New Artist"})

            library = Library(Path(tmp) / "lib.db")
            library.scan(folder)
            track = library.tracks()[0]
            library.update_metadata(track.path, {"title": "DB Title", "artist": "DB Artist"})
            updated = library.get(track.path)
            self.assertEqual(updated.title, "DB Title")
            self.assertEqual(updated.artist, "DB Artist")
            self.assertEqual(library.search("DB Artist")[0].path, track.path)

    def test_duplicate_detection_and_remove(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "music"
            folder.mkdir()
            for name in ("a.wav", "b.wav"):
                shutil.copy2(FIX / "single_tone.wav", folder / name)
            library = Library(Path(tmp) / "lib.db")
            library.scan(folder)
            tracks = library.tracks()
            for track in tracks:
                library.update_metadata(track.path, {"title": "Same", "artist": "Same"})
            groups = library.find_duplicates()
            self.assertEqual(len(groups), 1)
            self.assertEqual(len(groups[0]), 2)
            removed = library.remove_paths([groups[0][1].path])
            self.assertEqual(removed, 1)
            self.assertEqual(len(library.search("Same")), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
