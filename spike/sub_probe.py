# -*- coding: utf-8 -*-
"""Focused probe: does libmpv render ASS subtitles in wid and render API modes?"""
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
IMAGE = str(FIX / "frame_4k.png")
ASS = str(FIX / "overlay.ass")


class MpvSWSize(ctypes.Structure):
    _fields_ = [("w", ctypes.c_int), ("h", ctypes.c_int)]


mpv.MpvRenderParam.TYPES["sw_size"] = (17, MpvSWSize)
mpv.MpvRenderParam.TYPES["sw_format"] = (18, str)
mpv.MpvRenderParam.TYPES["sw_stride"] = (19, int)
mpv.MpvRenderParam.TYPES["sw_pointer"] = (20, ctypes.c_void_p)
_orig = mpv.MpvRenderParam.__init__


def _init(self, name, value=None):
    if name == "sw_stride":
        self.type_id = 19
        self.value = ctypes.c_int(int(value))
        self.data = ctypes.cast(ctypes.pointer(self.value), ctypes.c_void_p)
        return
    _orig(self, name, value)


mpv.MpvRenderParam.__init__ = _init


def prop(p, n, d=None):
    try:
        return p._get_property(n)
    except Exception:
        return d


def wid_test():
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QWidget

    app = QApplication.instance() or QApplication([])
    host = QWidget()
    host.resize(960, 540)
    host.setAttribute(Qt.WA_NativeWindow, True)
    host.show()
    app.processEvents()
    time.sleep(0.5)
    out = {"hwnd": int(host.winId())}
    p = mpv.MPV(wid=str(out["hwnd"]), vo="gpu", ao="null", idle="yes", keep_open="yes", osc="no")
    try:
        p.play(IMAGE)
        p.wait_until_playing(timeout=10)
        time.sleep(0.5)
        p.sub_add(ASS)
        time.sleep(1.0)
        out["track_list"] = prop(p, "track-list")
        out["sub_text"] = prop(p, "sub-text")
        out["sub_visibility"] = prop(p, "sub-visibility")
        shot = OUT / "wid_ass.png"
        p.command("screenshot-to-file", str(shot), "subtitles")
        time.sleep(0.5)
        out["shot_exists"] = shot.exists()
        out["shot"] = str(shot)
        from PIL import ImageGrab
        from PyQt5.QtCore import QPoint

        tl = host.mapToGlobal(QPoint(0, 0))
        ImageGrab.grab(bbox=(tl.x(), tl.y(), tl.x() + host.width(), tl.y() + host.height())).save(
            str(OUT / "wid_ass_screen.png")
        )
        out["screen"] = str(OUT / "wid_ass_screen.png")
    finally:
        p.terminate()
        host.close()
        app.processEvents()
    return out


def render_test():
    out = {}
    p = mpv.MPV(vo="libmpv", ao="null", idle="yes", keep_open="yes")
    ctx = mpv.MpvRenderContext(p, "sw")
    try:
        p.play(IMAGE)
        p.wait_until_playing(timeout=10)
        time.sleep(0.5)
        p.pause = True
        p.sub_add(ASS)
        time.sleep(1.5)
        out["track_list"] = prop(p, "track-list")
        out["sub_text"] = prop(p, "sub-text")
        out["sub_visibility"] = prop(p, "sub-visibility")
        out["osd_level"] = prop(p, "osd-level")
        for i in range(3):
            deadline = time.time() + 5
            while time.time() < deadline:
                if ctx.update():
                    break
                time.sleep(0.05)
            w, h = 640, 360
            buf = ctypes.create_string_buffer(w * h * 4)
            ctx.render(
                sw_size={"w": w, "h": h},
                sw_format="rgb0",
                sw_stride=w * 4,
                sw_pointer=ctypes.cast(buf, ctypes.c_void_p),
            )
            ctx.report_swap()
            frame = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)[:, :, :3]
            Image.fromarray(frame, "RGB").save(str(OUT / f"render_sub_{i}.png"))
            time.sleep(0.8)
        out["status"] = "ok"
    finally:
        ctx.free()
        p.terminate()
    return out


if __name__ == "__main__":
    print(json.dumps({"wid": wid_test(), "render": render_test()}, ensure_ascii=False, indent=2, default=str))
