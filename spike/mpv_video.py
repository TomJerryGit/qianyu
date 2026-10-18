# -*- coding: utf-8 -*-
"""libmpv video spike: 4K decode, ASS subtitles, wid embedding, render API.

Run:  QT_QPA_PLATFORM=windows python spike/mpv_video.py
Writes  spike/out/video_report.json  and PNG captures.
"""
from __future__ import annotations

import ctypes
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mpv_loader  # noqa: F401,E402
import mpv  # noqa: E402

FIX = HERE / "fixtures"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

IMAGE = str(FIX / "frame_4k.png")
ASS = str(FIX / "overlay.ass")
VIDEO = "av://lavfi:testsrc2=size=1280x720:rate=30:duration=10"


# --- extend python-mpv's render-param table with the software renderer ------
class MpvSWSize(ctypes.Structure):
    _fields_ = [("w", ctypes.c_int), ("h", ctypes.c_int)]


mpv.MpvRenderParam.TYPES["sw_size"] = (17, MpvSWSize)
mpv.MpvRenderParam.TYPES["sw_format"] = (18, str)
mpv.MpvRenderParam.TYPES["sw_stride"] = (19, int)
mpv.MpvRenderParam.TYPES["sw_pointer"] = (20, ctypes.c_void_p)

_orig_param_init = mpv.MpvRenderParam.__init__


def _param_init(self, name, value=None):
    if name == "sw_stride":
        self.type_id = 19
        self.value = ctypes.c_int(int(value))
        self.data = ctypes.cast(ctypes.pointer(self.value), ctypes.c_void_p)
        return
    _orig_param_init(self, name, value)


mpv.MpvRenderParam.__init__ = _param_init


def prop(player, name, default=None):
    try:
        return player._get_property(name)
    except Exception:
        return default


def make_player(**opts):
    base = dict(ao="null", idle="yes", keep_open="yes", osc="no", input_default_bindings="no")
    base.update(opts)
    return mpv.MPV(**base)


def load_and_wait(player, path: str, timeout: float = 10.0) -> bool:
    player.play(path)
    try:
        player.wait_until_playing(timeout=timeout)
        time.sleep(0.8)
        return True
    except Exception:
        return False


def test_decode() -> dict:
    """Decode a 3840x2160 PNG with vo=null; inspect video params and ASS tracks."""
    result = {"error": None}
    player = make_player(vo="null", **{"image-display-duration": "inf"})
    try:
        if not load_and_wait(player, IMAGE):
            result["error"] = "did not start playing"
        else:
            result["width"] = prop(player, "width")
            result["height"] = prop(player, "height")
            result["duration"] = prop(player, "duration")
            result["video_params"] = prop(player, "video-params")
            result["video_out_params"] = prop(player, "video-out-params")
            player.sub_add(ASS)
            time.sleep(0.5)
            result["track_list"] = prop(player, "track-list")
            result["status"] = "ok"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        player.terminate()
    return result


def test_wid() -> dict:
    """Embed mpv into a real Qt widget and check whether Qt overlays survive."""
    result = {"error": None}
    try:
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication, QLabel, QWidget
    except Exception as exc:
        return {"error": f"PyQt5 unavailable: {exc}", "status": "skipped"}

    app = QApplication.instance() or QApplication(sys.argv)
    host = QWidget()
    host.setWindowTitle("wid spike")
    host.resize(1280, 720)
    host.setAttribute(Qt.WA_NativeWindow, True)
    host.setStyleSheet("background:#101010;")
    overlay = QLabel("QT OVERLAY — should be above video", host)
    overlay.setStyleSheet("background:white;color:black;font-size:20px;padding:8px;")
    overlay.move(30, 30)
    overlay.resize(460, 46)
    host.show()
    app.processEvents()
    time.sleep(0.5)
    hwnd = int(host.winId())
    result["hwnd"] = hwnd

    player = make_player(wid=str(hwnd), vo="gpu", hwdec="auto-safe", length="10")
    try:
        if not load_and_wait(player, VIDEO):
            result["error"] = "did not start playing"
        else:
            player.sub_add(ASS)
            time.sleep(1.0)
            result["current_vo"] = prop(player, "current-vo")
            result["video_out_params"] = prop(player, "video-out-params")
            result["hwdec_current"] = prop(player, "hwdec-current")
            result["osd_dimensions"] = prop(player, "osd-dimensions")
            result["sub_text"] = prop(player, "sub-text")
            result["sub_visibility"] = prop(player, "sub-visibility")
            app.processEvents()
            time.sleep(1.0)
            app.processEvents()
            shot = OUT / "wid_window.png"
            result["qt_grab_saved"] = bool(host.grab().save(str(shot)))
            result["qt_grab"] = str(shot)
            try:
                from PIL import ImageGrab
                from PyQt5.QtCore import QPoint

                top_left = host.mapToGlobal(QPoint(0, 0))
                box = (top_left.x(), top_left.y(), top_left.x() + host.width(), top_left.y() + host.height())
                screen_path = OUT / "wid_screen.png"
                ImageGrab.grab(bbox=box).save(str(screen_path))
                result["screen_capture"] = str(screen_path)
                result["airspace_check"] = "see airspace_probe2.py (PrintWindow vs QWidget.grab)"
            except Exception as exc:
                result["screen_capture_error"] = f"{type(exc).__name__}: {exc}"
            result["status"] = "ok"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        player.terminate()
        host.close()
        app.processEvents()
    return result


def sw_capture(ctx, width: int, height: int, path: Path) -> bool:
    deadline = time.time() + 10
    while time.time() < deadline:
        if ctx.update():
            break
        time.sleep(0.05)
    buf = ctypes.create_string_buffer(width * height * 4)
    ctx.render(
        sw_size={"w": width, "h": height},
        sw_format="rgb0",
        sw_stride=width * 4,
        sw_pointer=ctypes.cast(buf, ctypes.c_void_p),
    )
    ctx.report_swap()
    frame = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4)[:, :, :3]
    Image.fromarray(frame, "RGB").save(path)
    return True


def test_render_api() -> dict:
    """Render into a Python-owned buffer via the libmpv software render API."""
    result = {"error": None}
    player = make_player(vo="libmpv", length="10")
    ctx = None
    try:
        # vo=libmpv waits for a render context, so create it before loadfile.
        ctx = mpv.MpvRenderContext(player, "sw")
        if not load_and_wait(player, VIDEO):
            result["error"] = "did not start playing"
        else:
            player.pause = True
            player.sub_add(ASS)
            time.sleep(1.0)
            result["sub_text"] = prop(player, "sub-text")
            result["video_params"] = prop(player, "video-params")
            result["sw_640"] = sw_capture(ctx, 640, 360, OUT / "sw_640.png")
            result["sw_640_ass"] = sw_capture(ctx, 640, 360, OUT / "sw_640_ass.png")
            result["sw_1280"] = sw_capture(ctx, 1280, 720, OUT / "sw_1280.png")
            result["status"] = "ok"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if ctx is not None:
            ctx.free()
        player.terminate()
    return result


def test_hdr_options() -> dict:
    """Verify the HDR/tone-mapping option surface; no HDR sample is available."""
    result = {"error": None}
    player = make_player(vo="null")
    try:
        result["tone_mapping_choices"] = [
            "auto", "clip", "mobius", "reinhard", "hable", "gamma", "linear",
            "spline", "bt.2390", "bt.2446a", "st2094-40", "st2094-10",
        ]
        result["target_colorspace_hint"] = prop(player, "target-colorspace-hint")
        player.tone_mapping = "bt.2390"
        player.target_colorspace_hint = "yes"
        result["applied_tone_mapping"] = prop(player, "tone-mapping")
        result["applied_target_hint"] = prop(player, "target-colorspace-hint")
        load_and_wait(player, IMAGE)
        result["sdr_video_params"] = prop(player, "video-params")
        result["status"] = "options_verified_no_hdr_sample"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        player.terminate()
    return result


def main() -> None:
    report = {
        "decode": test_decode(),
        "wid": test_wid(),
        "render_api": test_render_api(),
        "hdr": test_hdr_options(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    (OUT / "video_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
