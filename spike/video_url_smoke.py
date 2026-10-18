# -*- coding: utf-8 -*-
"""Verify the video URL path with a local HTTP server (no external network)."""
from __future__ import annotations

import functools
import sys
import tempfile
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from qianyu.qt import QApplication  # noqa: E402

from qianyu.config import Config  # noqa: E402
from qianyu.ui.video_window import VideoWindow  # noqa: E402

FIXTURES = ROOT / "spike" / "fixtures"


def main() -> None:
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(FIXTURES))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    app = QApplication([])
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-url-"))
    window = VideoWindow(config=Config(tmp / "config.json"), ao="null")
    window.show()
    url = f"http://127.0.0.1:{port}/test_resume.mp4"
    window.open_path(url)
    deadline = time.time() + 20
    while time.time() < deadline:
        app.processEvents()
        if window._player is not None and (window._player.duration or 0) > 8:
            break
        time.sleep(0.1)
    player = window._player
    print("URL", url)
    print("URL_DURATION", round(player.duration, 2) if player and player.duration else None)
    print("URL_SIZE", player._get_property("width") if player else None,
          player._get_property("height") if player else None)
    print("URL_QUEUE", len(window._queue))
    window.close()
    app.processEvents()
    server.shutdown()
    server.server_close()
    print("CLOSED", True)


if __name__ == "__main__":
    main()

