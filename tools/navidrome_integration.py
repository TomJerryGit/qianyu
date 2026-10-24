# -*- coding: utf-8 -*-
"""One-process Navidrome integration test.

Starts a temporary Navidrome instance, creates the first admin, then exercises
the same SubsonicClient used by QianYu (ping/search/albums/stream).
"""
from __future__ import annotations

import base64
import json
import math
import shutil
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.subsonic import SubsonicClient

COVER_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////"
    "////////////////////////////////////////////////////////2wBDAf//////////"
    "////////////////////////////////////////////////////////////wAARCAABAAED"
    "ASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAA"
    "AAAA/9oADAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QA"
    "FBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/a"
    "AAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAA"
    "AAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABD/xAAUEQEAAAAAAAAA"
    "AAAAAAAAAAAA/9oACAEDAQE/EB//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/"
    "EB//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/EB//2Q=="
)

EXE = ROOT / "tools" / "navidrome" / "navidrome.exe"
MUSIC = ROOT / "tools" / "navidrome-music"
DATA = ROOT / "tools" / "navidrome-test-data"
PORT = 4534
BASE = f"http://127.0.0.1:{PORT}"
USER = "qianyu"
PASSWORD = "qianyu-test-pass"
LOG = ROOT / "tools" / "navidrome_integration.log"
OUT = ROOT / "tools" / "navidrome_integration.json"


def ensure_music() -> None:
    MUSIC.mkdir(parents=True, exist_ok=True)
    cover = MUSIC / "cover.jpg"
    if not cover.exists():
        cover.write_bytes(COVER_JPEG)
    if any(MUSIC.glob("*.wav")):
        return
    for index, (frequency, name) in enumerate(((440, "single_tone.wav"),
                                               (220, "gapless_a.wav"))):
        path = MUSIC / name
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(44100)
            frames = bytearray()
            for sample in range(44100 * 2):
                value = int(12000 * math.sin(2 * math.pi * frequency * sample / 44100))
                frames += int(value).to_bytes(2, "little", signed=True)
            handle.writeframes(bytes(frames))



def say(message):
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(str(message) + "\n")


def wait_ready(timeout=30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BASE + "/ping", timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def create_admin() -> str:
    request = urllib.request.Request(
        BASE + "/auth/createAdmin",
        data=json.dumps({"username": USER, "password": PASSWORD}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "QianYu"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return f"created {response.status}"
    except Exception as exc:
        return f"skip {type(exc).__name__}: {exc}"


def main() -> int:
    LOG.write_text("", encoding="utf-8")
    if not EXE.exists():
        say("NO_NAVIDROME")
        return 2
    ensure_music()
    shutil.rmtree(DATA, ignore_errors=True)
    DATA.mkdir(parents=True, exist_ok=True)
    server_log = (ROOT / "tools" / "navidrome_server.log").open("wb")
    server = subprocess.Popen(
        [
            str(EXE),
            "--musicfolder", str(MUSIC),
            "--datafolder", str(DATA),
            "--address", "127.0.0.1",
            "--port", str(PORT),
            "--nobanner",
        ],
        cwd=str(EXE.parent),
        stdout=server_log,
        stderr=subprocess.STDOUT,
    )
    try:
        if not wait_ready():
            say("SERVER_NOT_READY")
            return 3
        say("READY " + BASE)
        say("ADMIN " + create_admin())
        client = SubsonicClient(BASE, USER, PASSWORD)
        say("PING " + str(client.ping()))
        songs = []
        deadline = time.time() + 45
        while time.time() < deadline:
            songs = client.search_songs("tone")
            if songs:
                break
            time.sleep(1)
        say(f"SEARCH {len(songs)}")
        for song in songs[:5]:
            say(f"SONG {song.title} | {song.artist} | {song.album}")
        albums = client.albums()
        say(f"ALBUMS {len(albums)}")
        album_tracks = []
        if albums:
            album_tracks = client.album_songs(albums[0].id)
            say(f"ALBUM_SONGS {len(album_tracks)}")
        stream_ok = False
        stream_bytes = 0
        cover_ok = False
        cover_bytes = 0
        if songs:
            stream = client.stream_url(songs[0])
            try:
                with urllib.request.urlopen(stream, timeout=15) as response:
                    chunk = response.read(4096)
                    stream_ok = response.status == 200
                    stream_bytes = len(chunk)
            except Exception as exc:
                say(f"STREAM_ERROR {type(exc).__name__}: {exc}")
            cover_url = client.cover_url(songs[0])
            if cover_url:
                try:
                    with urllib.request.urlopen(cover_url, timeout=15) as response:
                        cover = response.read(4096)
                        cover_ok = response.status == 200 and bool(cover)
                        cover_bytes = len(cover)
                except Exception as exc:
                    say(f"COVER_ERROR {type(exc).__name__}: {exc}")
        result = {
            "ready": True,
            "ping": True,
            "songs": len(songs),
            "albums": len(albums),
            "album_tracks": len(album_tracks),
            "stream": stream_ok,
            "stream_bytes": stream_bytes,
            "cover": cover_ok,
            "cover_bytes": cover_bytes,
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        say("RESULT " + json.dumps(result, ensure_ascii=False))
        return 0 if stream_ok and songs else 4
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        try:
            server_log.close()
        except Exception:
            pass
        say("SERVER_STOPPED")


if __name__ == "__main__":
    raise SystemExit(main())
