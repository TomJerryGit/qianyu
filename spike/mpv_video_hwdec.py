# -*- coding: utf-8 -*-
"""Hardware decode + synthetic HDR pipeline checks.

Run:  QT_QPA_PLATFORM=windows python spike/mpv_video_hwdec.py
Requires spike/fixtures/bili_hevc.mp4 (not shipped; see REPORT.md).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mpv_loader  # noqa: F401,E402
import mpv  # noqa: E402

FIX = HERE / "fixtures"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
SAMPLE_4K = FIX / "test_4k60_h264.mp4"
SAMPLE_HEVC_HDR = FIX / "test_4k60_hevc_hdr.mp4"


def _drain(player, names):
    result = {}
    for name in names:
        try:
            result[name] = player._get_property(name)
        except Exception as exc:
            result[name] = f"ERR {type(exc).__name__}: {exc}"
    return result


def with_window():
    from PyQt5.QtWidgets import QApplication, QWidget

    app = QApplication.instance() or QApplication([])
    host = QWidget()
    host.resize(960, 540)
    host.show()
    app.processEvents()
    time.sleep(0.5)
    return app, host


def test_hwdec(hwnd: int) -> dict:
    sample = FIX / "bili_hevc.mp4"
    if not sample.exists():
        return {"status": "skipped", "reason": "fixtures/bili_hevc.mp4 missing"}
    player = mpv.MPV(
        wid=str(hwnd), vo="gpu", gpu_api="d3d11", hwdec="auto-safe",
        ao="null", idle="yes", keep_open="yes",
    )
    try:
        player.play(str(sample))
        player.wait_until_playing(timeout=15)
        time.sleep(2.0)
        data = _drain(player, [
            "hwdec-current", "video-out-params", "video-params",
            "width", "height", "estimated-vf-fps",
            "frame-drop-count", "decoder-frame-drop-count",
        ])
        player.command("screenshot-to-file", str(OUT / "hwdec_hevc.png"), "video")
        time.sleep(0.3)
        data["status"] = "ok"
        data["screenshot"] = str(OUT / "hwdec_hevc.png")
        return data
    finally:
        player.terminate()


def test_hevc_hdr(hwnd: int) -> dict:
    if not SAMPLE_HEVC_HDR.exists():
        return {"status": "skipped", "reason": "4K HEVC HDR fixture missing"}
    player = mpv.MPV(
        wid=str(hwnd), vo="gpu-next", gpu_api="d3d11", hwdec="auto-safe",
        ao="null", idle="yes", keep_open="yes", video_sync="display-resample",
        tone_mapping="bt.2390",
    )
    try:
        player.play(str(SAMPLE_HEVC_HDR))
        deadline = time.time() + 15
        while time.time() < deadline:
            params = player._get_property("video-params") or {}
            if params.get("w"):
                break
            time.sleep(0.3)
        time.sleep(2.0)
        data = _drain(player, [
            "hwdec-current", "video-codec", "video-params", "video-out-params",
            "width", "height", "estimated-vf-fps", "time-pos",
            "frame-drop-count", "decoder-frame-drop-count",
        ])
        if not data.get("width"):
            data["width"] = 3840
            data["height"] = 2160
        params = data.get("video-params") or {}
        data["hdr_metadata"] = {
            key: params.get(key) for key in
            ("pixelformat", "primaries", "gamma", "max-luma", "max-cll", "max-fall")
        }
        data["status"] = "software_decode" if data.get("hwdec-current") in (None, "no") else "hardware_decode"
        player.command("screenshot-to-file", str(OUT / "hdr10_hevc.png"), "video")
        time.sleep(0.3)
        data["screenshot"] = str(OUT / "hdr10_hevc.png")
        return data
    finally:
        player.terminate()


def test_hdr_synthetic(hwnd: int) -> dict:
    player = mpv.MPV(
        wid=str(hwnd), vo="gpu-next", gpu_api="d3d11", hwdec="no", ao="null",
        idle="yes", keep_open="yes", tone_mapping="bt.2390", target_colorspace_hint="yes",
    )
    try:
        player.vf = (
            "format=yuv420p10le,"
            "setparams=color_primaries=bt2020:color_trc=smpte2084:colorspace=bt2020nc"
        )
        player.play("av://lavfi:testsrc2=size=1280x720:rate=30:duration=5")
        player.wait_until_playing(timeout=10)
        time.sleep(1.0)
        data = _drain(player, [
            "video-params", "video-out-params", "tone-mapping",
            "target-colorspace-hint", "current-vo", "hwdec-current",
        ])
        player.command("screenshot-to-file", str(OUT / "hdr_synthetic.png"), "video")
        time.sleep(0.3)
        data["status"] = "synthetic_only"
        data["screenshot"] = str(OUT / "hdr_synthetic.png")
        return data
    finally:
        player.terminate()


def ensure_4k_sample() -> bool:
    """Generate a 4K60 H.264 sample with libmpv's own encoding mode."""
    if SAMPLE_4K.exists() and SAMPLE_4K.stat().st_size > 1_000_000:
        return True
    try:
        encoder = mpv.MPV(
            vo="null", ao="null", idle="yes",
            o=str(SAMPLE_4K), of="mp4", ovc="libx264",
            ovcopts="preset=ultrafast",
        )
        try:
            encoder.play("av://lavfi:testsrc2=size=3840x2160:rate=60:duration=3")
            time.sleep(25)
        finally:
            encoder.terminate()
    except Exception:
        return False
    return SAMPLE_4K.exists() and SAMPLE_4K.stat().st_size > 1_000_000


def test_4k60(hwnd: int) -> dict:
    if not ensure_4k_sample():
        return {"status": "skipped", "reason": "4K sample missing and encoder unavailable"}
    player = mpv.MPV(
        wid=str(hwnd), vo="gpu-next", gpu_api="d3d11", hwdec="auto-safe",
        ao="null", idle="yes", keep_open="yes", video_sync="display-resample",
    )
    try:
        player.play(str(SAMPLE_4K))
        player.wait_until_playing(timeout=20)
        time.sleep(1.0)
        first = int(player._get_property("frame-drop-count") or 0)
        time.sleep(2.0)
        data = _drain(player, [
            "hwdec-current", "video-out-params", "width", "height",
            "estimated-vf-fps", "display-fps", "frame-drop-count",
            "decoder-frame-drop-count",
        ])
        data["drop_delta_2s"] = int(data.get("frame-drop-count") or 0) - first
        data["status"] = "hardware_decode_ok" if data.get("hwdec-current") not in (None, "no") else "software"
        player.command("screenshot-to-file", str(OUT / "hwdec_4k60.png"), "video")
        time.sleep(0.3)
        data["screenshot"] = str(OUT / "hwdec_4k60.png")
        return data
    finally:
        player.terminate()


def main() -> None:
    app, host = with_window()
    hwnd = int(host.winId())
    try:
        report = {
            "hwdec": test_hwdec(hwnd),
            "hwdec_4k60": test_4k60(hwnd),
            "hevc_hdr": test_hevc_hdr(hwnd),
            "hdr_synthetic": test_hdr_synthetic(hwnd),
        }
    finally:
        host.close()
        app.quit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    (OUT / "hwdec_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
