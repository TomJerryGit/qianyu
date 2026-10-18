# -*- coding: utf-8 -*-
"""Smoke for subtitle style / color / audio delay (V18/V19/V20)."""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from qianyu.qt import QApplication  # noqa: E402

from qianyu.config import Config  # noqa: E402
from qianyu.ui.video_style_dialog import SubtitleStyleDialog  # noqa: E402
from qianyu.ui.video_window import VideoWindow  # noqa: E402

SAMPLE = ROOT / "spike" / "fixtures" / "test_resume.mp4"


def main() -> None:
    app = QApplication([])
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-style-"))
    window = VideoWindow(config=Config(tmp / "config.json"), ao="null")
    window.show()
    window.open_path(str(SAMPLE))
    deadline = time.time() + 12
    while time.time() < deadline:
        app.processEvents()
        if window._player is not None and (window._player.duration or 0) > 8:
            break
        time.sleep(0.1)
    player = window._player

    window._subtitle_style.update({
        "font": "Microsoft YaHei", "size": 42, "color": "#FFCC00",
        "border": 3.0, "delay": 0.5, "position": "top", "bold": True, "italic": False,
        "codepage": "gbk",
    })
    window._apply_subtitle_style()
    time.sleep(0.4)
    print("SUB_SIZE", player._get_property("sub-font-size"))
    print("SUB_COLOR", player._get_property("sub-color"))
    print("SUB_DELAY", player._get_property("sub-delay"))
    print("SUB_ALIGN", player._get_property("sub-align-y"))
    print("SUB_CODEPAGE", player._get_property("sub-codepage"))

    window._hdr.update({"tone_mapping": "spline", "target_peak": "500",
                        "compute_peak": False, "target_hint": False})
    window._apply_hdr()
    time.sleep(0.3)
    print("HDR", player._get_property("tone-mapping"), player._get_property("target-peak"),
          player._get_property("hdr-compute-peak"), player._get_property("target-colorspace-hint"))

    window._color.update({"brightness": 10, "contrast": 20, "saturation": -5, "gamma": 5})
    window._apply_color()
    time.sleep(0.4)
    print("COLOR", player._get_property("brightness"), player._get_property("contrast"),
          player._get_property("saturation"), player._get_property("gamma"))

    window._audio_delay = 0.25
    window._apply_audio_delay()
    time.sleep(0.3)
    print("AUDIO_DELAY", player._get_property("audio-delay"))

    dialog = SubtitleStyleDialog(window._subtitle_style, window)
    print("DIALOG_SIZE", dialog.values()["size"], dialog.values()["position"])
    dialog.reject()

    window.close()
    app.processEvents()
    print("CLOSED", True)


if __name__ == "__main__":
    main()

