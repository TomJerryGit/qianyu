# -*- coding: utf-8 -*-
"""Generate deterministic media fixtures for the libmpv spike.

No external encoder is required: WAV is written with the stdlib, the 4K frame
is a PNG (decoded by FFmpeg through mpv's image demuxer), and the subtitle is
plain ASS.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "fixtures"
OUT.mkdir(exist_ok=True)

RATE = 48000
CHANNELS = 2


def write_wav(path: Path, samples: np.ndarray, rate: int = RATE) -> None:
    """samples: float32 [-1, 1], shape (n,) or (n, channels)."""
    samples = np.asarray(samples, dtype=np.float32)
    if samples.ndim == 1:
        samples = np.repeat(samples[:, None], CHANNELS, axis=1)
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(pcm.shape[1])
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(pcm.tobytes())


def make_gapless_pair() -> None:
    """Two halves of one continuous 440 Hz tone.

    If playback inserts a gap, the captured PCM shows a silent run at the
    splice; a true gapless transition keeps the sine continuous.
    """
    n = RATE * 2
    t = np.arange(n) / RATE
    # End/start at phase 0 so the concatenation is continuous.
    tone = 0.35 * np.sin(2 * math.pi * 440.0 * t)
    write_wav(OUT / "gapless_a.wav", tone)
    write_wav(OUT / "gapless_b.wav", tone)
    write_wav(OUT / "single_tone.wav", 0.35 * np.sin(2 * math.pi * 440.0 * np.arange(RATE * 3) / RATE))


def make_eq_probe() -> None:
    """5 s of white noise for a before/after FFT comparison."""
    rng = np.random.default_rng(20261017)
    noise = 0.15 * rng.standard_normal(RATE * 5)
    write_wav(OUT / "noise.wav", noise)


def make_4k_png() -> None:
    w, h = 3840, 2160
    x = np.linspace(0, 1, w, dtype=np.float32)
    y = np.linspace(0, 1, h, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)
    rgb = np.stack(
        [
            (xx * 255).astype(np.uint8),
            (yy * 255).astype(np.uint8),
            (((xx + yy) / 2) * 255).astype(np.uint8),
        ],
        axis=-1,
    )
    img = Image.fromarray(rgb, "RGB")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 180)
    except OSError:
        font = ImageFont.load_default()
    draw.rectangle([120, 120, 3720, 540], fill=(0, 0, 0))
    draw.text((180, 180), "4K 3840x2160  SPIKE", fill=(255, 255, 255), font=font)
    draw.text((180, 1900), "ASS subtitle overlay test", fill=(255, 255, 255), font=font)
    img.save(OUT / "frame_4k.png", optimize=True)


def make_ass() -> None:
    (OUT / "overlay.ass").write_text(
        """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3,2,2,60,60,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:10.00,Default,,0,0,0,,{\\fad(200,200)}ASS subtitle: 中文 / English / 日本語
Dialogue: 0,0:00:02.00,0:00:08.00,Default,,0,0,0,,{\\an8}Top line with {\\c&H00FFFF&}color{\\c} and shadow
""",
        encoding="utf-8-sig",
    )


def main() -> None:
    make_gapless_pair()
    make_eq_probe()
    make_4k_png()
    make_ass()
    for p in sorted(OUT.iterdir()):
        print(f"{p.name:20s} {p.stat().st_size:>12,} bytes")


if __name__ == "__main__":
    main()
