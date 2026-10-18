#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Development launcher (adds src/ to sys.path)."""
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


def _boot(message: str) -> None:
    try:
        from qianyu.logs import bootstrap

        bootstrap(message)
    except Exception:
        try:
            import tempfile

            with (Path(tempfile.gettempdir()) / "qianyu-boot.log").open("a", encoding="utf-8") as fh:
                fh.write(message + "\n")
        except Exception:
            pass


_boot("run_dev: start")
try:
    from qianyu.ui.app import main

    _boot("run_dev: imported app")
    sys.exit(main())
except BaseException:
    _boot("run_dev: FAILED\n" + traceback.format_exc())
    raise
