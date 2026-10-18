# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir spec for 浅语影音 0.9.

Build:  pyinstaller --noconfirm packaging/qianyu.spec
Output: dist/QianYu/QianYu.exe
"""
import os

from PyInstaller.utils.hooks import collect_submodules

spec_dir = globals().get("SPECPATH") or os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(spec_dir, ".."))
hiddenimports = ["mpv"] + collect_submodules("mutagen")

a = Analysis(
    [os.path.join(root, "run_dev.py")],
    pathex=[os.path.join(root, "src")],
    binaries=[(os.path.join(root, "libmpv-2.dll"), ".")],
    datas=[(os.path.join(root, "src", "qianyu", "ui", "theme"), "qianyu/ui/theme")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "PIL", "PySide6", "shiboken6"],
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
