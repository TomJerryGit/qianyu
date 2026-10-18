# -*- coding: utf-8 -*-
"""Smoke for video queue / chapters / bookmarks (V13/V14/V15)."""
from __future__ import annotations

import shutil
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
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-queue-"))
    folder = tmp / "videos"
    folder.mkdir()
    first = folder / "01-first.mp4"
    second = folder / "02-second.mp4"
    shutil.copy2(SAMPLE, first)
    shutil.copy2(SAMPLE, second)

    window = VideoWindow(config=Config(tmp / "config.json"), ao="null")
    window.show()
    window.open_path(str(first))
    wait_for(app, lambda: window._player is not None and (window._player.duration or 0) > 1)
    print("QUEUE", len(window._queue), "INDEX", window._queue_index, "PATH", Path(window._last_path).name)

    window._next_video()
    wait_for(app, lambda: Path(window._last_path).name == second.name)
    print("NEXT", Path(window._last_path).name, "INDEX", window._queue_index)
    window._previous_video()
    wait_for(app, lambda: Path(window._last_path).name == first.name)
    print("PREV", Path(window._last_path).name, "INDEX", window._queue_index)

    window._set_chapters([
        {"time": 1.0, "title": "Intro"},
        {"time": 6.0, "title": "Main"},
    ])
    print("CHAPTERS", window._chapter_combo.count(), "VISIBLE", window._chapter_combo.isVisible())
    window._chapter_combo.setCurrentIndex(1)
    time.sleep(0.5)
    print("CHAPTER_POS", round(window._player.time_pos or 0, 1))

    window._bookmarks[window._last_path] = [{"pos": 4.0, "label": "mark"}]
    window._jump_bookmark(4.0)
    time.sleep(0.6)
    print("BOOKMARK_POS", round(window._player.time_pos or 0, 1))

    window.close()
    app.processEvents()
    print("CLOSED", True)


if __name__ == "__main__":
    main()

