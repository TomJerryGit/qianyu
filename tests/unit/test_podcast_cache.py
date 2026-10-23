# -*- coding: utf-8 -*-
"""Podcast cache tests using a local HTTP server."""
from __future__ import annotations

import http.server
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.podcast_cache import PodcastCache  # noqa: E402

PAYLOAD = b"qianyu-podcast-bytes" * 4096


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(PAYLOAD)))
        self.end_headers()
        self.wfile.write(PAYLOAD)

    def log_message(self, *args):
        pass


class PodcastCacheTests(unittest.TestCase):
    def setUp(self):
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/episode.mp3"
        self.root = Path(tempfile.mkdtemp(prefix="qy-podcast-cache-"))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_download_and_remove(self):
        cache = PodcastCache(self.root)
        path = cache.download(self.url, title="Episode")
        self.assertTrue(path.is_file())
        self.assertEqual(path.read_bytes(), PAYLOAD)
        self.assertTrue(cache.is_downloaded(self.url))
        self.assertEqual(cache.total_bytes(), len(PAYLOAD))
        self.assertTrue(cache.remove(self.url))
        self.assertFalse(cache.is_downloaded(self.url))

    def test_prune_oldest(self):
        cache = PodcastCache(self.root, limit_mb=64)
        first = cache.download(self.url, title="First")
        self.assertTrue(first.is_file())
        # Simulate an over-limit cache with two registered files.
        second = self.root / "second.mp3"
        second.write_bytes(b"x" * (2 * 1024 * 1024))
        cache._index["http://example.com/second"] = {
            "file": second.name, "title": "Second", "size": second.stat().st_size,
            "downloaded_at": 9999999999,
        }
        cache._index[self.url]["downloaded_at"] = 1
        cache.limit_bytes = 1024 * 1024
        cache.prune()
        self.assertFalse(cache.is_downloaded(self.url))


if __name__ == "__main__":
    unittest.main(verbosity=2)
