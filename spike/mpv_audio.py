# -*- coding: utf-8 -*-
"""libmpv audio spike: gapless, EQ, output-device switching.

Run:  python spike/mpv_audio.py
Writes  spike/out/audio_report.json  and the captured PCM WAVs.
"""
from __future__ import annotations

import json
import math
import sys
import time
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mpv_loader  # noqa: F401,E402
import mpv  # noqa: E402

FIX = HERE / "fixtures"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)


def new_player(**opts) -> "mpv.MPV":
    base = dict(vo="null", idle="yes", audio_display="no", volume=100)
    base.update(opts)
    return mpv.MPV(**base)


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Read PCM/float WAV, including WAVE_FORMAT_EXTENSIBLE (0xFFFE).

    mpv's PCM AO writes 16-bit stereo extensible WAVs; Python's stdlib wave
    module rejects that tag, so parse the RIFF chunks ourselves.
    """
    import struct

    blob = path.read_bytes()
    if blob[:4] != b"RIFF" or blob[8:12] != b"WAVE":
        raise ValueError(f"not a WAV: {path}")
    fmt = None
    data = None
    pos = 12
    while pos + 8 <= len(blob):
        cid = blob[pos:pos + 4]
        size = struct.unpack("<I", blob[pos + 4:pos + 8])[0]
        body = blob[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            tag, channels, rate, _byte_rate, _align, bits = struct.unpack("<HHIIHH", body[:16])
            if tag == 0xFFFE and len(body) >= 40:
                tag = struct.unpack("<H", body[24:26])[0]
            fmt = (tag, channels, rate, bits)
        elif cid == b"data":
            data = blob[pos + 8:pos + 8 + (size if size not in (0, 0xFFFFFFFF) else len(blob))]
        pos += 8 + size + (size & 1)

    if not fmt or data is None:
        raise ValueError(f"missing fmt/data chunk: {path}")
    tag, channels, rate, bits = fmt
    if tag == 1 and bits == 16:
        samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    elif tag == 1 and bits == 24:
        raw = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        val = raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16)
        val = np.where(val & 0x800000, val - 0x1000000, val).astype(np.float32) / 8388608.0
        samples = val
    elif tag == 1 and bits == 32:
        samples = np.frombuffer(data, dtype="<i4").astype(np.float32) / 2147483648.0
    elif tag == 3 and bits == 32:
        samples = np.frombuffer(data, dtype="<f4").astype(np.float32)
    elif tag == 3 and bits == 64:
        samples = np.frombuffer(data, dtype="<f8").astype(np.float32)
    else:
        raise ValueError(f"unsupported WAV format tag={tag} bits={bits}")
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, rate


def longest_silence(samples: np.ndarray, rate: int, threshold: float = 2e-3) -> float:
    quiet = np.abs(samples) < threshold
    if not quiet.any():
        return 0.0
    run = 0
    best = 0
    for q in quiet:
        run = run + 1 if q else 0
        best = max(best, run)
    return best / rate


def test_gapless() -> dict:
    capture = OUT / "gapless_capture.wav"
    if capture.exists():
        capture.unlink()
    player = new_player(ao="pcm", **{
        "ao-pcm-file": str(capture),
        "ao-pcm-waveheader": "yes",
        "gapless-audio": "yes",
    })
    result = {"capture": str(capture), "error": None}
    try:
        player.play(str(FIX / "gapless_a.wav"))
        player.playlist_append(str(FIX / "gapless_b.wav"))
        player.wait_until_playing(timeout=10)
        player.wait_for_playback(timeout=20)
        time.sleep(0.5)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        player.terminate()

    if not capture.exists():
        result["status"] = "no_capture"
        return result

    samples, rate = read_wav(capture)
    result.update(
        status="ok",
        sample_rate=rate,
        duration_s=round(len(samples) / rate, 3),
        longest_silence_ms=round(longest_silence(samples, rate) * 1000, 2),
    )
    # The splice sits at 2.0 s; measure the local envelope around it.
    start = int(1.95 * rate)
    end = int(2.05 * rate)
    local = samples[start:end]
    result["splice_peak"] = round(float(np.max(np.abs(local))) if len(local) else 0.0, 4)
    result["splice_rms"] = round(float(np.sqrt(np.mean(local ** 2))) if len(local) else 0.0, 4)
    return result


def fft_band_db(samples: np.ndarray, rate: int, lo: float, hi: float) -> float:
    mono = samples - samples.mean()
    n = 1 << int(math.log2(len(mono)))
    window = np.hanning(n)
    spec = np.fft.rfft(mono[:n] * window)
    freqs = np.fft.rfftfreq(n, 1 / rate)
    band = (freqs >= lo) & (freqs <= hi)
    power = np.mean(np.abs(spec[band]) ** 2) + 1e-20
    return 10 * math.log10(power)


def test_eq() -> dict:
    result = {"error": None}
    captures = {}
    for label, af in (("flat", ""), ("boost_1k", "equalizer=f=1000:t=q:w=1:g=12")):
        capture = OUT / f"eq_{label}.wav"
        if capture.exists():
            capture.unlink()
        player = new_player(ao="pcm", **{
            "ao-pcm-file": str(capture),
            "ao-pcm-waveheader": "yes",
        })
        try:
            if af:
                player.af = af
                time.sleep(0.2)
                result[f"{label}_af"] = player.af
            player.play(str(FIX / "noise.wav"))
            player.wait_until_playing(timeout=10)
            player.wait_for_playback(timeout=15)
            time.sleep(0.4)
        except Exception as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            player.terminate()
        if capture.exists():
            captures[label] = read_wav(capture)

    if "flat" not in captures or "boost_1k" not in captures:
        result["status"] = "no_capture"
        return result

    flat, rate = captures["flat"]
    boosted, _ = captures["boost_1k"]
    result.update(status="ok", sample_rate=rate)
    for band, (lo, hi) in {"1k": (900, 1100), "200": (150, 250)}.items():
        result[f"flat_{band}_db"] = round(fft_band_db(flat, rate, lo, hi), 2)
        result[f"boost_{band}_db"] = round(fft_band_db(boosted, rate, lo, hi), 2)
    result["delta_1k_db"] = round(result["boost_1k_db"] - result["flat_1k_db"], 2)
    result["delta_200_db"] = round(result["boost_200_db"] - result["flat_200_db"], 2)
    return result


def test_devices() -> dict:
    result = {"error": None, "devices": []}
    player = new_player(ao="wasapi", volume=0)
    try:
        time.sleep(0.5)
        result["devices"] = list(player.audio_device_list or [])
        result["initial_device"] = player.audio_device
        player.play(str(FIX / "single_tone.wav"))
        player.wait_until_playing(timeout=10)
        result["playing_device"] = player.audio_device
        result["audio_out_params"] = player.audio_out_params
        names = [d["name"] for d in result["devices"]]
        target = next((n for n in names if n.startswith("wasapi/")), None)
        if target:
            player.audio_device = target
            time.sleep(0.5)
            result["switched_to"] = player.audio_device
            result["switched_params"] = player.audio_out_params
        openal = "openal" if "openal" in names else None
        if openal:
            player.audio_device = openal
            time.sleep(0.5)
            result["switched_openal"] = player.audio_device
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        player.terminate()
    return result


def main() -> None:
    report = {
        "libmpv": mpv_loader.mpv.__version__,
        "gapless": test_gapless(),
        "eq": test_eq(),
        "devices": test_devices(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    (OUT / "audio_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
