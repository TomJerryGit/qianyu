# Diagnostic: activate a specific Windows keyboard layout before Qt starts.
import ctypes
import sys
from pathlib import Path

ROOT = Path(r"D:\qianyu")
sys.path.insert(0, str(ROOT / "src"))
user32 = ctypes.windll.user32
hkl = user32.LoadKeyboardLayoutW("E0200804", 0x00000001)  # KLF_ACTIVATE
print("HKL", hex(hkl or 0), flush=True)
if hkl:
    user32.ActivateKeyboardLayout(hkl, 0)

from qianyu.ui.app import main  # noqa: E402

sys.exit(main(["--smoke"]))
