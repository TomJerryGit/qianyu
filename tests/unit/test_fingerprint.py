# -*- coding: utf-8 -*-
"""Fingerprint helper tests (no fpcalc required)."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.fingerprint import audio_fingerprint, envelope_similarity, similarity  # noqa: E402


class FingerprintTests(unittest.TestCase):
    def test_similarity(self):
        self.assertEqual(similarity((1, 2, 3, 4), (1, 2, 3, 4)), 1.0)
        self.assertEqual(similarity((1, 2, 3, 4), (1, 2, 0, 0)), 0.5)
        self.assertEqual(similarity((), (1,)), 0.0)
        self.assertGreater(envelope_similarity(
            (200,) * 10, (192,) * 10
        ), 0.9)
        self.assertGreater(envelope_similarity(
            (10, 20, 30, 40, 50), (11, 21, 29, 41, 49)
        ), 0.9)

    def test_fpcalc_json(self):
        completed = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"duration": 12.0, "fingerprint": [1, 2, 3]}'
        )
        with patch("qianyu.core.fingerprint.find_fpcalc", return_value="fpcalc"), \
                patch("subprocess.run", return_value=completed):
            self.assertEqual(audio_fingerprint("x.flac"), (1, 2, 3))


if __name__ == "__main__":
    unittest.main(verbosity=2)
