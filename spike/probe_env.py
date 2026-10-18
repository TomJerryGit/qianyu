# -*- coding: utf-8 -*-
"""Probe libmpv capabilities before building the full spike harness."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mpv_loader  # noqa: F401
import mpv


def dump(label, value):
    print(f"{label}: {value!r}")


def main():
    player = mpv.MPV(
        vo="null",
        ao="null",
        idle="yes",
        **{"gapless-audio": "yes", "audio-display": "no"},
    )
    player.wait_until_playing(timeout=5) if False else None
    time.sleep(0.5)
    print("== mpv ==")
    for prop in ("mpv-version", "ffmpeg-version", "ao", "vo", "gpu-api",
                 "hwdec", "hwdec-current", "audio-device", "audio-device-list",
                 "gapless-audio", "audio-display", "video-sync"):
        try:
            dump(prop, getattr(player, prop.replace("-", "_")))
        except Exception as exc:
            print(f"{prop}: ERR {type(exc).__name__}: {exc}")

    print("== ao option ==")
    try:
        info = player.option_info("ao")
        print(json.dumps(info, ensure_ascii=False, default=str)[:2000])
    except Exception as exc:
        print("option_info(ao) failed:", exc)

    print("== render context ==")
    try:
        ctx = mpv.MpvRenderContext(player, "sw")
        dump("ctx", ctx)
    except Exception as exc:
        print("render ctx sw failed:", type(exc).__name__, exc)

    player.terminate()


if __name__ == "__main__":
    main()
