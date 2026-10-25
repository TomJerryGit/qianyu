# -*- coding: utf-8 -*-
"""Release checksum verification tests."""
from __future__ import annotations

import contextlib
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from verify_release import parse_sums, sha256, verify_directory  # noqa: E402


class VerifyReleaseTests(unittest.TestCase):
    def test_checksum_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.exe").write_bytes(b"alpha")
            (root / "nested").mkdir()
            (root / "nested" / "b.json").write_bytes(b"beta")
            lines = [
                f"{hashlib.sha256(b'alpha').hexdigest()}  a.exe",
                f"{hashlib.sha256(b'beta').hexdigest()}  b.json",
            ]
            (root / "SHA256SUMS.txt").write_text("\n".join(lines), encoding="utf-8")
            self.assertEqual(sha256(root / "a.exe"), hashlib.sha256(b"alpha").hexdigest())
            self.assertEqual(len(parse_sums(root / "SHA256SUMS.txt")), 2)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(verify_directory(root), 0)
            self.assertIn("verified 2/2", output.getvalue())

    def test_bad_checksum_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SHA256SUMS.txt"
            path.write_text("not-a-valid-line", encoding="utf-8")
            with self.assertRaises(ValueError):
                parse_sums(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
