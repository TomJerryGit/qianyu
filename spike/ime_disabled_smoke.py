# Diagnostic: disable IME for this process before Qt starts.
import ctypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(r"D:\qianyu") / "src"))
ctypes.windll.imm32.ImmDisableIME(0)

from qianyu.ui.app import main  # noqa: E402

sys.exit(main(["--smoke"]))
