# -*- coding: utf-8 -*-
"""Unit tests for the update skeleton (no network required)."""
from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.update import (  # noqa: E402
    canonical_manifest, download_update, fetch_manifest, is_newer, parse_manifest,
    sha256_file, verify_manifest,
)


class UpdateTests(unittest.TestCase):
    def test_version_compare(self):
        self.assertTrue(is_newer("0.9.0", "0.9.1"))
        self.assertFalse(is_newer("0.9.1", "0.9.1"))
        self.assertTrue(is_newer("0.9.9", "0.10.0"))

    def test_manifest_and_local_fetch(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.json"
            manifest.write_text(
                json.dumps({"version": "1.0.0", "url": "https://example.invalid/a.exe",
                            "sha256": "abc", "notes": "test"}, ensure_ascii=False),
                encoding="utf-8",
            )
            info = fetch_manifest(manifest.as_uri())
            self.assertEqual(info.version, "1.0.0")
            self.assertEqual(info.sha256, "abc")

    def test_hash_and_download_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "payload.bin"
            source.write_bytes(b"hello" * 1000)
            info = parse_manifest(
                json.dumps({
                    "version": "1.0.0",
                    "url": source.as_uri(),
                    "sha256": sha256_file(source),
                }).encode()
            )
            target = download_update(info, Path(tmp) / "downloaded.bin")
            self.assertEqual(sha256_file(target), sha256_file(source))

            bad = parse_manifest(
                json.dumps({"version": "1.0.0", "url": source.as_uri(), "sha256": "0" * 64}).encode()
            )
            with self.assertRaises(ValueError):
                download_update(bad, Path(tmp) / "bad.bin")

    def test_ed25519_manifest_signature(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private = Ed25519PrivateKey.generate()
        public = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        public_b64 = base64.b64encode(public).decode()
        payload = json.dumps({
            "version": "1.0.0", "url": "https://example.invalid/a.exe",
            "sha256": "a" * 64, "notes": "signed",
        }, sort_keys=True, separators=(",", ":")).encode()
        signature = private.sign(canonical_manifest(payload))
        signed = json.loads(payload)
        signed["signature"] = base64.b64encode(signature).decode()
        good = json.dumps(signed).encode()
        self.assertEqual(verify_manifest(good, public_b64).version, "1.0.0")

        tampered = dict(signed)
        tampered["notes"] = "tampered"
        with self.assertRaises(Exception):
            verify_manifest(json.dumps(tampered).encode(), public_b64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
