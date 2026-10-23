# -*- coding: utf-8 -*-
"""Credential storage tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.secure_store import (  # noqa: E402
    PREFIX, PLAIN_PREFIX, SecretStore, protect, unprotect,
)


class _Config:
    def __init__(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


class SecureStoreTests(unittest.TestCase):
    def test_round_trip(self):
        value = protect("token-value")
        self.assertTrue(value.startswith((PREFIX, PLAIN_PREFIX)))
        self.assertEqual(unprotect(value), "token-value")
        if sys.platform == "win32":
            self.assertTrue(value.startswith(PREFIX))
            self.assertNotIn("token-value", value)

    def test_store_and_migrate(self):
        config = _Config()
        store = SecretStore(config)
        store.set("listenbrainz_token", "abc")
        self.assertEqual(store.get("listenbrainz_token"), "abc")
        self.assertNotEqual(config.get("listenbrainz_token"), "abc")

        config.data["subsonic_password"] = "legacy-password"
        self.assertTrue(store.migrate(["subsonic_password"]))
        self.assertEqual(store.get("subsonic_password"), "legacy-password")
        self.assertFalse(store.migrate(["subsonic_password"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
