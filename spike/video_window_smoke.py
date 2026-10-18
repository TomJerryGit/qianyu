# -*- coding: utf-8 -*-
"""Headless-ish smoke for the 1.0 video window (requires a real Windows Qt window)."""
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

SAMPLE = ROOT / "spike" / "fixtures" / "test_4k60_h264.mp4"
RESUME_SAMPLE = ROOT / "spike" / "fixtures" / "test_resume.mp4"
ASS = ROOT / "spike" / "fixtures" / "overlay.ass"


def main() -> None:
    app = QApplication([])
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-video-"))
    window = VideoWindow(config=Config(tmp / "config.json"), ao="null")
    window.show()
    app.processEvents()
    window.open_path(str(SAMPLE))
    deadline = time.time() + 12
    while time.time() < deadline:
        app.processEvents()
        if window._player is not None and (window._player.duration or 0) > 0:
            break
        time.sleep(0.1)
    player = window._player
    print("DURATION", round(player.duration, 2) if player else None)
    print("SIZE", player._get_property("width"), player._get_property("height"))
    print("HWDEC", player._get_property("hwdec-current"))
    print("TRACKS", len(player._get_property("track-list") or []))
    if ASS.exists():
        player.sub_add(str(ASS))
        time.sleep(0.5)
    print("SUBS", len([t for t in (player._get_property("track-list") or []) if t.get("type") == "sub"]))
    window._progress.setValue(500)
    window._end_seek()
    time.sleep(0.8)
    print("POSITION", round(player.time_pos or 0, 2))
    shot = window.screenshot()
    time.sleep(0.6)
    print("SHOT", bool(shot), Path(shot).exists() if shot else False)
    window._full_btn.click()
    app.processEvents()
    time.sleep(0.3)
    print("FULLSCREEN", window._fullscreen)
    window._full_btn.click()
    app.processEvents()
    window.grab().save(str(ROOT / "spike" / "out" / "video_window.png"))
    window._save_resume()
    window.close()
    app.processEvents()

    resume_pos = None
    if RESUME_SAMPLE.exists() and RESUME_SAMPLE.stat().st_size > 1_000_000:
        config = Config(tmp / "config.json")
        first = VideoWindow(config=config, ao="null")
        first.show()
        first.open_path(str(RESUME_SAMPLE))
        deadline = time.time() + 10
        while time.time() < deadline:
            app.processEvents()
            if first._player is not None and (first._player.duration or 0) > 8:
                break
            time.sleep(0.1)
        time.sleep(0.5)
        try:
            first._player.command("seek", 6.0, "absolute")
        except Exception as exc:
            print("RESUME_SEEK_ERR", type(exc).__name__)
        time.sleep(1.0)
        first._save_resume()
        first.close()
        app.processEvents()

        second = VideoWindow(config=config, ao="null")
        second.show()
        second.open_path(str(RESUME_SAMPLE))
        deadline = time.time() + 12
        while time.time() < deadline:
            app.processEvents()
            if second._player is not None and (second._player.time_pos or 0) > 5:
                resume_pos = second._player.time_pos
                break
            time.sleep(0.1)
        second.close()
        app.processEvents()
    print("RESUME_POSITION", round(resume_pos, 2) if resume_pos else None)
    print("CLOSED", player is not None)


if __name__ == "__main__":
    main()

