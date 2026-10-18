# -*- coding: utf-8 -*-
"""Smoke for video aspect/rotate/speed/frame-step/A-B (V08/V09/V16)."""
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

SAMPLE = ROOT / "spike" / "fixtures" / "test_resume.mp4"


def wait_for(app, predicate, timeout=12):
    deadline = time.time() + timeout
    while time.time() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.1)
    return False


def main() -> None:
    app = QApplication([])
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-controls-"))
    window = VideoWindow(config=Config(tmp / "config.json"), ao="null")
    window.show()
    window.open_path(str(SAMPLE))
    wait_for(app, lambda: window._player is not None and (window._player.duration or 0) > 8)
    player = window._player

    window._speed_combo.setCurrentIndex(4)
    time.sleep(0.4)
    print("SPEED", player.speed)

    window._set_aspect("16:9")
    time.sleep(0.3)
    print("ASPECT", player._get_property("video-aspect-override"))

    window._set_rotate(90)
    time.sleep(0.3)
    print("ROTATE", player._get_property("video-rotate"))
    window._set_rotate(0)

    window._set_deinterlace(True)
    time.sleep(0.3)
    print("DEINTERLACE", player._get_property("deinterlace"))
    window._set_deinterlace(False)

    player.pause = True
    player.command("seek", 5.0, "absolute")
    time.sleep(0.5)
    before = float(player.time_pos or 0)
    window._frame_step(True)
    time.sleep(0.3)
    after = float(player.time_pos or 0)
    print("FRAME_STEP", round(before, 3), "->", round(after, 3))

    window._set_ab_a()
    time.sleep(0.2)
    player.command("seek", 7.0, "absolute")
    time.sleep(0.3)
    window._set_ab_b()
    time.sleep(0.2)
    print("AB", player._get_property("ab-loop-a"), player._get_property("ab-loop-b"))
    window._clear_ab()
    time.sleep(0.2)
    print("AB_CLEAR", player._get_property("ab-loop-a"), player._get_property("ab-loop-b"))

    window._speed_combo.setCurrentIndex(2)
    window.close()
    app.processEvents()
    print("CLOSED", True)


if __name__ == "__main__":
    main()

