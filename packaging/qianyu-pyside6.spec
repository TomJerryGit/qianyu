# -*- mode: python ; coding: utf-8 -*-
"""PySide6/Qt6 onedir build (Python 3.11).

Build inside tools/venv311:
  python -m PyInstaller --noconfirm --clean `
    --distpath dist-pyside6 --workpath build-pyside6 packaging\qianyu-pyside6.spec
"""
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

spec_dir = globals().get("SPECPATH") or os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(spec_dir, ".."))
hiddenimports = ["mpv", "cryptography", "imageio_ffmpeg"] + collect_submodules("mutagen")
datas = [
    (os.path.join(root, "src", "qianyu", "ui", "theme"), "qianyu/ui/theme"),
] + collect_data_files("imageio_ffmpeg")

a = Analysis(
    [os.path.join(root, "run_dev.py")],
    pathex=[os.path.join(root, "src")],
    binaries=[(os.path.join(root, "libmpv-2.dll"), ".")],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "PIL", "PyQt5"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="QianYu",
    debug=False,
    version=os.path.join(spec_dir, "version_info.txt"),
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="QianYu",
)
