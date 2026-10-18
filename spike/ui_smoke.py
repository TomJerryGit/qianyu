# -*- coding: utf-8 -*-
"""Headless smoke test for the 0.9 music UI.

Run:  QT_QPA_PLATFORM=offscreen python spike/ui_smoke.py
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from qianyu.qt import QApplication  # noqa: E402

from qianyu.config import Config  # noqa: E402
from qianyu.engine.mpv_engine import MpvEngine  # noqa: E402
from qianyu.ui.main_window import MainWindow  # noqa: E402

FIX = ROOT / "spike" / "fixtures"


def main():
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet((ROOT / "src" / "qianyu" / "ui" / "theme" / "dark.qss").read_text(encoding="utf-8"))
    tmp = Path(tempfile.mkdtemp(prefix="qianyu-ui-"))
    music = tmp / "music"
    music.mkdir()
    for name in ("single_tone.wav", "gapless_a.wav", "gapless_b.wav"):
        shutil.copy2(FIX / name, music / name)
    (music / "single_tone.lrc").write_text(
        "[ti:测试]\n[00:00.00]第一行歌词\n[00:01.00]第二行歌词\n[00:02.00]第三行歌词\n",
        encoding="utf-8",
    )
    from PIL import Image, ImageDraw
    cover = Image.new("RGB", (400, 400), (40, 70, 160))
    ImageDraw.Draw(cover).text((40, 180), "QIANYU 0.9", fill=(255, 255, 255))
    cover.save(music / "cover.jpg", quality=90)

    config = Config(tmp / "config.json")
    engine = MpvEngine(ao="null", volume=0)
    window = MainWindow(config, engine=engine, data_dir=tmp / "data")
    window.show()
    app.processEvents()

    result = window._library.scan(music)
    window._refresh_library()
    print("SCAN", result)
    print("COVER", window._library.tracks()[0].cover)
    print("ROWS", window._table.model().rowCount())
    window._table.selectRow(0)
    window._toggle_favorite()
    window._library_filter.setCurrentIndex(1)
    app.processEvents()
    print("FAVORITES", window._track_model.rowCount())
    for index, label in ((2, "RECENT"), (3, "ADDED"), (4, "MOST"), (5, "UNPLAYED")):
        window._library_filter.setCurrentIndex(index)
        app.processEvents()
        print(label, window._track_model.rowCount())
    window._library_filter.setCurrentIndex(0)
    app.processEvents()
    print("SLIDER_MAX", window._progress.maximum())

    window._play_library_row(0)
    deadline = time.time() + 8
    while time.time() < deadline and engine.position < 0.5:
        app.processEvents()
        time.sleep(0.05)
    print("POSITION", round(engine.position, 2), "DURATION", round(engine.duration, 2))
    print("PLAYLIST", window._playlist_view.count())
    print("LYRICS", window._lyrics_view.count())
    print("NOW", window._now_title.text())
    print("PROGRESS_SET", end=" ")
    window._progress.setValue(500)
    print(window._progress.value())
    window._volume.setValue(50)
    print("VOLUME", window._engine.volume)

    # The third row has a matching .lrc; verify lyrics and the now-playing panel.
    window._play_library_row(2)
    deadline = time.time() + 5
    while time.time() < deadline and window._lyrics_view.count() < 3:
        app.processEvents()
        time.sleep(0.05)
    print("LYRICS_AFTER", window._lyrics_view.count(), "NOW_AFTER", window._now_title.text())
    window._nudge_lyrics_offset(500)
    print("LYRICS_OFFSET", window._offset_label.text(), "INDEX", window._lyrics_index)

    shot = ROOT / "spike" / "out" / "ui_0.9.png"
    window.grab().save(str(shot))
    print("SHOT", shot, shot.exists())

    window._set_theme("light")
    app.processEvents()
    light_shot = ROOT / "spike" / "out" / "ui_0.9_light.png"
    window.grab().save(str(light_shot))
    print("SHOT_LIGHT", light_shot, light_shot.exists())

    window._desktop_action.setChecked(True)
    app.processEvents()
    time.sleep(0.2)
    app.processEvents()
    if window._desktop_lyrics is not None:
        print("DESKTOP_LYRICS", window._desktop_lyrics.isVisible(),
              window._desktop_lyrics._current.text())
        window._desktop_lyrics.grab().save(str(ROOT / "spike" / "out" / "desktop_lyrics.png"))
    window._desktop_action.setChecked(False)

    window._mini_action.setChecked(True)
    app.processEvents()
    time.sleep(0.2)
    app.processEvents()
    if window._mini is not None:
        print("MINI", window._mini.isVisible(), window._mini._title.text())
        window._mini.grab().save(str(ROOT / "spike" / "out" / "mini_player.png"))
    window._show_window()
    app.processEvents()

    from qianyu.ui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(window._config, window._engine, window)
    print("SETTINGS", dialog._device.count(), dialog._theme.currentData())
    dialog.reject()

    from qianyu.ui.lyrics_editor import LyricsEditorDialog

    editor = LyricsEditorDialog(music / "edited.lrc", "[00:00.00]edited\n")
    editor._save()
    print("LYRICS_EDIT", (music / "edited.lrc").exists())

    window._grid_toggle.setChecked(True)
    app.processEvents()
    time.sleep(0.2)
    print("GRID", window._album_view._grid.count(), window._library_stack.currentWidget() is window._album_view)
    window.grab().save(str(ROOT / "spike" / "out" / "ui_grid.png"))
    window._grid_toggle.setChecked(False)

    window._queue_toggle.setChecked(True)
    app.processEvents()
    print("QUEUE_HIDDEN", not window._playlist_view.isVisible())
    window._queue_toggle.setChecked(False)

    window._show_now_page()
    app.processEvents()
    time.sleep(0.3)
    print("NOW_PAGE", window._now_page.isVisible(), window._now_page._lyrics.count())
    window._now_page.grab().save(str(ROOT / "spike" / "out" / "now_playing.png"))
    window._now_page.close()
    app.processEvents()

    from qianyu.core.cue import parse_cue

    cue_path = music / "album.cue"
    cue_path.write_text(
        'PERFORMER "Artist"\nTITLE "Album"\nFILE "single_tone.wav" WAVE\n'
        '  TRACK 01 AUDIO\n    TITLE "Cue One"\n    INDEX 01 00:00:00\n'
        '  TRACK 02 AUDIO\n    TITLE "Cue Two"\n    INDEX 01 00:01:00\n',
        encoding="utf-8",
    )
    sheet = parse_cue(cue_path)
    window._play_cue(sheet, 0)
    deadline = time.time() + 8
    while time.time() < deadline:
        app.processEvents()
        if window._current is not None and window._current.title == "Cue Two":
            break
        time.sleep(0.2)
    print("CUE", len(sheet.tracks), window._current.title if window._current else None)

    window._config.set("close_to_tray", False)

    window.close()
    app.processEvents()
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
