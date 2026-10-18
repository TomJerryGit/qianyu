# -*- coding: utf-8 -*-
"""Tag writing via mutagen (ID3 for MP3/WAV; easy tags for FLAC/MP4/OGG)."""
from __future__ import annotations

from pathlib import Path

import mutagen
from mutagen.mp3 import MP3
from mutagen.wave import WAVE


FIELDS = ("title", "artist", "album", "genre", "date", "tracknumber", "discnumber")
ID3_FIELDS = {
    "title": "TIT2",
    "artist": "TPE1",
    "album": "TALB",
    "genre": "TCON",
    "date": "TDRC",
    "tracknumber": "TRCK",
    "discnumber": "TPOS",
}


def write_tags(path: str, values: dict[str, str]) -> None:
    audio = mutagen.File(path)
    if audio is None:
        raise ValueError(f"unsupported or unreadable audio file: {Path(path).name}")
    if isinstance(audio, WAVE):
        raise ValueError("WAV 标签写入暂不支持；请转为 FLAC/MP3 后编辑")

    tags = audio.tags
    is_id3 = (tags is not None and tags.__class__.__module__.startswith("mutagen.id3")) \
        or isinstance(audio, MP3)
    if is_id3:
        from mutagen.id3 import ID3

        if not isinstance(tags, ID3):
            tags = ID3()
        for key in FIELDS:
            if key not in values:
                continue
            value = str(values[key]).strip()
            frame_id = ID3_FIELDS[key]
            if value:
                tags.delall(frame_id)
                tags.add(_id3_frame(frame_id, value))
            else:
                tags.delall(frame_id)
        audio.tags = tags
        audio.save()
        return

    easy = mutagen.File(path, easy=True)
    if easy is None:
        raise ValueError(f"unsupported or unreadable audio file: {Path(path).name}")
    if easy.tags is None:
        easy.add_tags()
    for key in FIELDS:
        if key not in values:
            continue
        value = str(values[key]).strip()
        if value:
            easy[key] = [value]
        elif key in easy:
            del easy[key]
    easy.save()


def _id3_frame(frame_id: str, value: str):
    from mutagen.id3 import TALB, TCON, TDRC, TIT2, TPE1, TPOS, TRCK

    classes = {"TIT2": TIT2, "TPE1": TPE1, "TALB": TALB, "TCON": TCON,
               "TDRC": TDRC, "TRCK": TRCK, "TPOS": TPOS}
    return classes[frame_id](encoding=3, text=value)
