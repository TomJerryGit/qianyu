# -*- coding: utf-8 -*-
"""Locate and import libmpv.

The DLL may sit next to the executable (frozen build), in the project root
(source checkout), or at QIANYU_MPV_DLL.  python-mpv resolves the library via
ctypes.util.find_library, which on Windows ignores the current directory, so
the containing directory must be on PATH before importing mpv.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidates() -> list[Path]:
    here = Path(__file__).resolve()
    out: list[Path] = []
    env = os.environ.get("QIANYU_MPV_DLL")
    if env:
        out.append(Path(env))
    if getattr(sys, "frozen", False):
        out.append(Path(sys.executable).resolve().parent)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            out.append(Path(meipass))
    # src/qianyu/engine/_loader.py -> project root is parents[3]
    out.append(here.parents[3])
    out.append(here.parents[3] / "vendor")
    return out


def dll_dir() -> Path:
    for base in _candidates():
        if base.is_file():
            return base.parent
        for name in ("libmpv-2.dll", "mpv-2.dll", "mpv-1.dll"):
            if (base / name).exists():
                return base
    raise FileNotFoundError(
        "libmpv not found; put libmpv-2.dll next to the app, or set QIANYU_MPV_DLL"
    )


DIR = dll_dir()
os.environ["PATH"] = str(DIR) + os.pathsep + os.environ.get("PATH", "")

import mpv  # noqa: E402  (must come after PATH is prepared)
