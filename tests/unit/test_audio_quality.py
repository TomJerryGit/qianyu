# -*- coding: utf-8 -*-
"""Audio-quality golden tests: gapless splice and EQ frequency response.

These use mpv's PCM output (ao=pcm) and the real libmpv build, so they are
skipped when the DLL or fixtures are unavailable.
"""
from __future__ import annotations

import math
import struct
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
FIX = ROOT / "spike" / "fixtures"

try:
    from qianyu.engine import _loader  # noqa: F401
    import mpv

    ENGINE_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    mpv = None
    ENGINE_AVAILABLE = False
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    blob = path.read_bytes()
    assert blob[:4] == b"RIFF"
    fmt = data = None
    pos = 12
    while pos + 8 <= len(blob):
        cid = blob[pos:pos + 4]
        size = struct.unpack("<I", blob[pos + 4:pos + 8])[0]
        body = blob[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            tag, channels, rate, _br, _ba, bits = struct.unpack("<HHIIHH", body[:16])
            if tag == 0xFFFE and len(body) >= 40:
                tag = struct.unpack("<H", body[24:26])[0]
            fmt = (tag, channels, rate, bits)
        elif cid == b"data":
            data = blob[pos + 8:pos + 8 + (size if size not in (0, 0xFFFFFFFF) else len(blob))]
        pos += 8 + size + (size & 1)
    tag, channels, rate, bits = fmt
    if tag == 1 and bits == 16:
        samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    elif tag == 3 and bits == 32:
        samples = np.frombuffer(data, dtype="<f4").astype(np.float32)
    else:
        raise ValueError(f"unsupported wav {tag}/{bits}")
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, rate


def longest_silence(samples: np.ndarray, rate: int, threshold: float = 2e-3) -> float:
    quiet = np.abs(samples) < threshold
    best = run = 0
    for value in quiet:
        run = run + 1 if value else 0
        best = max(best, run)
    return best / rate


def band_db(samples: np.ndarray, rate: int, lo: float, hi: float) -> float:
    mono = samples - samples.mean()
    n = 1 << int(math.log2(len(mono)))
    spec = np.fft.rfft(mono[:n] * np.hanning(n))
    freqs = np.fft.rfftfreq(n, 1 / rate)
    band = (freqs >= lo) & (freqs <= hi)
    return 10 * math.log10(float(np.mean(np.abs(spec[band]) ** 2)) + 1e-20)


@unittest.skipUnless(ENGINE_AVAILABLE, f"libmpv unavailable: {IMPORT_ERROR}")
@unittest.skipUnless((FIX / "gapless_a.wav").exists(), "spike fixtures missing")
class AudioQualityTests(unittest.TestCase):
    def _capture(self, paths, af: str = "") -> np.ndarray:
        with tempfile.TemporaryDirectory(prefix="qy-audio-") as tmp:
            out = Path(tmp) / "capture.wav"
            player = mpv.MPV(
                vo="null", ao="pcm", idle="yes",
                **{
                    "ao-pcm-file": str(out),
                    "ao-pcm-waveheader": "yes",
                    "gapless-audio": "yes",
                },
            )
            try:
                if af:
                    player.af = af
                player.play(str(paths[0]))
                for extra in paths[1:]:
                    player.playlist_append(str(extra))
                player.wait_until_playing(timeout=10)
                player.wait_for_playback(timeout=25)
                time.sleep(0.3)
            finally:
                player.terminate()
            return read_wav(out)

    def test_gapless_no_inserted_silence(self):
        samples, rate = self._capture([FIX / "gapless_a.wav", FIX / "gapless_b.wav"])
        self.assertAlmostEqual(len(samples) / rate, 4.0, delta=0.05)
        self.assertLess(longest_silence(samples, rate), 0.01)
        splice = samples[int(1.95 * rate):int(2.05 * rate)]
        self.assertGreater(float(np.sqrt(np.mean(splice ** 2))), 0.2)

    def test_eq_boost_is_frequency_selective(self):
        flat, rate = self._capture([FIX / "noise.wav"])
        boosted, _ = self._capture([FIX / "noise.wav"], "equalizer=f=1000:t=q:w=1:g=12")
        delta_1k = band_db(boosted, rate, 900, 1100) - band_db(flat, rate, 900, 1100)
        delta_200 = band_db(boosted, rate, 150, 250) - band_db(flat, rate, 150, 250)
        self.assertGreater(delta_1k, 8.0)
        self.assertLess(abs(delta_200), 2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
