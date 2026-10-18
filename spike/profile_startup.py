import cProfile
import pstats
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(r"D:\qianyu")
sys.path.insert(0, str(ROOT / "src"))

from qianyu.qt import QApplication
from qianyu.config import Config
from qianyu.engine.mpv_engine import MpvEngine
from qianyu.library import Library
from qianyu.ui.main_window import MainWindow

tmp = Path(tempfile.mkdtemp(prefix="qianyu-prof-"))
lib = Library(tmp / "library.db")
conn = lib._connect()
conn.executemany(
    """INSERT OR REPLACE INTO tracks(path,title,artist,album,duration,track_no,disc_no,
       codec,sample_rate,channels,bitrate,mtime,added_at,cover)
       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    [(f"D:/fake/{i}.flac", f"Track {i:05d}", f"Artist {i % 200}", f"Album {i % 1000}",
      180.0, i % 20, 0, "flac", 44100, 2, 900000, 0, time.time(), "") for i in range(10000)],
)
conn.commit()
conn.close()
app = QApplication([])
config = Config(tmp / "config.json")
engine = MpvEngine(ao="null", volume=0)

profile = cProfile.Profile()
profile.enable()
window = MainWindow(config, engine=engine, data_dir=tmp)
profile.disable()
pstats.Stats(profile).sort_stats("cumulative").print_stats(25)
window.shutdown()
engine.shutdown()
