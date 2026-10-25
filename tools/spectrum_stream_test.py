# -*- coding: utf-8 -*-
"""Offscreen acceptance for progressive FFmpeg spectrum (local + HTTP)."""
from __future__ import annotations

import http.server
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, r"D:\qianyu\src")

from qianyu.qt import QApplication
from qianyu.core.models import Track
from qianyu.ui.now_playing import NowPlayingPage

WAV = Path(r"D:\qianyu\spike\fixtures\single_tone.wav")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WAV.parent), **kwargs)

    def log_message(self, *args):
        pass


def wait(app, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        app.processEvents()
        time.sleep(0.05)


def run_case(app, path, label):
    page = NowPlayingPage()
    track = Track(path=path, title=label, artist="Test", album="Demo")
    page.set_track(track)
    wait(app, 5.0)
    source = page._spectrum_source.text()
    levels = page._spectrum._live_levels or page._spectrum._levels
    values = list(levels) if levels is not None else []
    print(label, "SOURCE:", source, "LEVELS:", round(max(values), 3) if values else 0)
    page.close()
    wait(app, 0.5)


def main():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/{WAV.name}"
    app = QApplication([])
    try:
        run_case(app, str(WAV), "LOCAL")
        run_case(app, url, "STREAM")
        run_case(app, str(WAV), "LOCAL2")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
