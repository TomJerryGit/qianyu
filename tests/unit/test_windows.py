# -*- coding: utf-8 -*-
"""Windows integration helpers that are safe to test without touching the registry."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.platform.windows import AUDIO_EXTENSIONS, PROGID, command_line  # noqa: E402


class WindowsIntegrationTests(unittest.TestCase):
    def test_command_contains_placeholder(self):
        command = command_line()
        self.assertIn("%1", command)
        if not getattr(sys, "frozen", False):
            self.assertIn("run_dev.py", command)

    def test_extensions(self):
        self.assertIn(".mp3", AUDIO_EXTENSIONS)
        self.assertIn(".flac", AUDIO_EXTENSIONS)
        self.assertEqual(PROGID, "QianYu.Audio")


if __name__ == "__main__":
    unittest.main(verbosity=2)
