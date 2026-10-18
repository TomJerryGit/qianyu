# -*- coding: utf-8 -*-
"""Shared libmpv loader for the spike.

python-mpv locates libmpv through ctypes.util.find_library, which on Windows
does not consider the current working directory.  Put the shipped DLL's
directory on PATH *before* importing mpv.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DLL_DIR = ROOT
os.environ["PATH"] = str(DLL_DIR) + os.pathsep + os.environ.get("PATH", "")

import mpv  # noqa: E402

print("python-mpv", mpv.__version__, "dll_dir", DLL_DIR, file=sys.stderr)
