# -*- coding: utf-8 -*-
"""Real remote HLS smoke (1080p and 4K variants). Requires network."""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from qianyu.qt import QApplication  # noqa: E402

from qianyu.config import Config  # noqa: E402
from qianyu.ui.video_window import VideoWindow  # noqa: E402

URLS = [
    ("1080p", "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"),
    ("4K", "http://sample.vodobox.net/skate_phantom_flex_4k/4k/skate_phantom_flex_4k_8288_2160p.m3u8"),
]


def main() -> None:
    app = QApplication([])
    for label, url in URLS:
        tmp = Path(tempfile.mkdtemp(prefix="qianyu-hls-"))
        window = VideoWindow(config=Config(tmp / "config.json"), ao="null")
        window.show()
        window.open_path(url)
        deadline = time.time() + 30
        while time.time() < deadline:
            app.processEvents()
            player = window._player
            if player is not None and ((player.width or 0) > 0 or (player.duration or 0) > 0):
                break
            time.sleep(0.2)
        player = window._player
        print(label, "DURATION", round(player.duration, 2) if player and player.duration else None)
        print(label, "SIZE", player._get_property("width") if player else None,
              player._get_property("height") if player else None)
        print(label, "CODEC", player._get_property("video-codec") if player else None)
        print(label, "HWDEC", player._get_property("hwdec-current") if player else None)
        window.close()
        app.processEvents()
    print("CLOSED", True)


if __name__ == "__main__":
    main()

