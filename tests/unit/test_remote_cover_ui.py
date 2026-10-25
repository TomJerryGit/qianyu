# -*- coding: utf-8 -*-
"""Offscreen UI test for remote album cover rendering."""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.qt import QApplication, QPixmap  # noqa: E402
from qianyu.config import Config  # noqa: E402
from qianyu.ui.remote_album_dialog import RemoteAlbumDialog  # noqa: E402


class RemoteCoverUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_cover_pixmap_set(self):
        try:
            from PIL import Image
        except Exception:
            self.skipTest("Pillow missing")
        buffer = io.BytesIO()
        Image.new("RGB", (16, 16), (20, 120, 200)).save(buffer, "PNG")
        dialog = RemoteAlbumDialog(Config(Path(tempfile.mkdtemp()) / "config.json"))
        try:
            dialog._cover_album_id = "album-1"
            dialog._show_cover("album-1", buffer.getvalue())
            pixmap = dialog._cover.pixmap()
            self.assertIsNotNone(pixmap)
            self.assertFalse(pixmap.isNull())
            self.assertGreater(pixmap.width(), 0)
        finally:
            dialog.close()

    def test_cover_ignores_stale_album(self):
        try:
            from PIL import Image
        except Exception:
            self.skipTest("Pillow missing")
        buffer = io.BytesIO()
        Image.new("RGB", (8, 8), (200, 20, 20)).save(buffer, "PNG")
        dialog = RemoteAlbumDialog(Config(Path(tempfile.mkdtemp()) / "config.json"))
        try:
            dialog._cover_album_id = "new-album"
            dialog._cover.setText("封面")
            dialog._show_cover("old-album", buffer.getvalue())
            self.assertIsNone(dialog._cover.pixmap())
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
