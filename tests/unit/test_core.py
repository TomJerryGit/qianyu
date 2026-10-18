# -*- coding: utf-8 -*-
"""Unit tests for the 0.9 core (stdlib unittest; pytest can also collect)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.lyrics import LrcLine, find_lrc, line_index_at, parse_lrc  # noqa: E402
from qianyu.core.models import Playlist  # noqa: E402
from qianyu.core.playlist import PlaylistStore  # noqa: E402
from qianyu.eq import build_eq_filter  # noqa: E402


class LyricsTests(unittest.TestCase):
    def test_basic_and_multi_timestamp(self):
        lines = parse_lrc("[00:01.00]one\n[00:02.50][00:03.50]two\n[ar:x]\n")
        self.assertEqual([(l.time_ms, l.text) for l in lines], [(1000, "one"), (2500, "two"), (3500, "two")])

    def test_offset_and_fraction(self):
        lines = parse_lrc("[offset:-500]\n[00:01.5]a\n[00:02.050]b\n")
        self.assertEqual([l.time_ms for l in lines], [1000, 1550])

    def test_index_at(self):
        lines = [LrcLine(1000, "a"), LrcLine(2000, "b")]
        self.assertEqual(line_index_at(lines, 0), -1)
        self.assertEqual(line_index_at(lines, 1500), 0)
        self.assertEqual(line_index_at(lines, 2000), 1)

    def test_find_lrc(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "song.mp3"
            audio.write_bytes(b"")
            self.assertIsNone(find_lrc(audio))
            (Path(tmp) / "song.lrc").write_text("[00:00.00]x", encoding="utf-8")
            self.assertEqual(find_lrc(audio).name, "song.lrc")


class PlaylistTests(unittest.TestCase):
    def test_add_dedupe_and_next(self):
        p = Playlist()
        with tempfile.TemporaryDirectory() as tmp:
            a, b = str(Path(tmp) / "a.mp3"), str(Path(tmp) / "b.mp3")
            Path(a).write_bytes(b"")
            Path(b).write_bytes(b"")
            self.assertTrue(p.add(a, "A"))
            self.assertFalse(p.add(a, "A2"))
            self.assertTrue(p.add(b, "B"))
            self.assertEqual(p.select(0).title, "A")
            self.assertEqual(p.next().title, "B")
            self.assertEqual(p.next().title, "A")
            p.loop_mode = "single"
            self.assertEqual(p.next().title, "A")

    def test_move_remove(self):
        p = Playlist()
        for name in ("a", "b", "c"):
            p.items.append(__import__("qianyu.core.models", fromlist=["PlaylistItem"]).PlaylistItem(name, name))
        self.assertTrue(p.move(0, 2))
        self.assertEqual([i.title for i in p.items], ["b", "c", "a"])
        self.assertTrue(p.remove(0))
        self.assertEqual([i.title for i in p.items], ["c", "a"])

    def test_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "list.json"
            store = PlaylistStore(path)
            store.playlist.add(str(Path(tmp) / "x.mp3"), "X")
            store.save()
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["items"][0]["title"], "X")
            again = PlaylistStore(path)
            self.assertEqual(len(again.playlist.items), 1)


class EqTests(unittest.TestCase):
    def test_chain(self):
        chain = build_eq_filter([0] * 10, preamp_db=-3)
        self.assertIn("volume=-3.00dB", chain)
        self.assertEqual(chain.count("equalizer="), 10)
        self.assertIn("f=1000", chain)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            build_eq_filter([0] * 9)
        with self.assertRaises(ValueError):
            build_eq_filter([0] * 9 + [float("nan")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
