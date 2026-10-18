# -*- coding: utf-8 -*-
"""Generate HDR10-tagged HEVC Main10 fixtures with imageio-ffmpeg/libx265.

The *content* is synthetic (testsrc2); the HDR10 metadata, 10-bit Main10
profile, BT.2020/PQ signaling and master-display/CLL values are real.
"""
from __future__ import annotations

from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
OUT = HERE / "fixtures"


def encode(name: str, width: int, height: int, rate: int = 60, duration: int = 3) -> None:
    target = OUT / name
    vf = ("format=yuv420p10le,"
          "setparams=color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc")
    x265 = (
        "hdr-opt=1:repeat-headers=1:colorprim=bt2020:transfer=smpte2084:"
        "colormatrix=bt2020nc:"
        "master-display=G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(10000000,1):"
        "max-cll=1000,400"
    )
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"testsrc2=size={width}x{height}:rate={rate}:duration={duration}",
        "-vf", vf, "-c:v", "libx265", "-preset", "ultrafast",
        "-x265-params", x265, "-an", "-y", str(target),
    ]
    print("encoding", target)
    import subprocess

    subprocess.run(command, check=True)
    print("wrote", target, target.stat().st_size)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    encode("test_4k60_hevc_hdr.mp4", 3840, 2160)
    encode("test_1080p60_hevc_hdr.mp4", 1920, 1080)
