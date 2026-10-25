# -*- coding: utf-8 -*-
"""One-process real Jellyfin integration test for QianYu."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qianyu.core.jellyfin import JellyfinClient

SERVER = ROOT / "tools" / "jellyfin-server" / "jellyfin" / "jellyfin.exe"
MUSIC = ROOT / "tools" / "jellyfin-music"
DATA = ROOT / "tools" / "jellyfin-test-data"
CONFIG = ROOT / "tools" / "jellyfin-test-config"
CACHE = ROOT / "tools" / "jellyfin-test-cache"
LOGS = ROOT / "tools" / "jellyfin-test-logs"
BASE = "http://127.0.0.1:8096"
USER = "qianyu"
PASSWORD = "qianyu-test-pass"
OUT = ROOT / "tools" / "jellyfin_integration.json"
LOG = ROOT / "tools" / "jellyfin_integration.log"


def ensure_music() -> None:
    album_dir = MUSIC / "Test Artist" / "Test Album"
    album_dir.mkdir(parents=True, exist_ok=True)
    track = album_dir / "01 - Test Song.mp3"
    if not track.exists():
        ffmpeg = SERVER.parent / "ffmpeg.exe"
        subprocess.run(
            [
                str(ffmpeg), "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
                "-metadata", "title=Test Song", "-metadata", "artist=Test Artist",
                "-metadata", "album=Test Album", "-metadata", "album_artist=Test Artist",
                "-metadata", "track=1", "-metadata", "date=2026",
                "-codec:a", "libmp3lame", "-q:a", "3", str(track),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    cover = album_dir / "cover.jpg"
    if not cover.exists():
        ffmpeg = SERVER.parent / "ffmpeg.exe"
        subprocess.run(
            [
                str(ffmpeg), "-y", "-f", "lavfi", "-i", "color=c=0x2E86C1:s=128x128",
                "-frames:v", "1", str(cover),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )



def say(message):
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(str(message) + "\n")


def request(path, method="GET", body=None, token="", params=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"User-Agent": "QianYu", "Accept": "application/json"}
    headers["X-Emby-Authorization"] = (
        'MediaBrowser Client="QianYu", Device="Windows", '
        'DeviceId="qianyu-test", Version="0.9.0"'
    )
    headers["Authorization"] = headers["X-Emby-Authorization"]
    if token:
        headers["X-Emby-Token"] = token
        headers["Authorization"] = headers["Authorization"] + f', Token="{token}"'
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
            try:
                return response.status, json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                return response.status, raw
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, exc.read(500).decode("utf-8", "replace")
        except Exception:
            return exc.code, str(exc)
    except Exception as exc:
        return 0, f"{type(exc).__name__}: {exc}"


def wait_public(timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, _ = request("/System/Info/Public")
        if status == 200:
            return True
        time.sleep(1)
    return False


def wait_startup(timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, _ = request("/Startup/Configuration")
        if status == 200:
            return True
        time.sleep(1)
    return False


def setup():
    status, body = request("/Startup/User")
    say(f"FIRST_USER {status} {str(body)[:120]}")
    status, body = request("/Startup/Configuration", "POST", {
        "ServerName": "QianYu Test",
        "UICulture": "en-US",
        "MetadataCountryCode": "US",
        "PreferredMetadataLanguage": "en",
    })
    say(f"CONFIG {status} {str(body)[:120]}")
    status, body = request("/Startup/User", "POST", {
        "Name": USER, "Password": PASSWORD,
    })
    say(f"USER {status} {str(body)[:120]}")
    status, body = request("/Startup/RemoteAccess", "POST", {
        "EnableRemoteAccess": False, "EnableAutomaticPortMapping": False,
    })
    say(f"REMOTE {status} {str(body)[:120]}")
    status, body = request("/Startup/Complete", "POST", {})
    say(f"COMPLETE {status} {str(body)[:120]}")


def add_library(token: str):
    params = {
        "name": "Music",
        "collectionType": "music",
        "paths": str(MUSIC),
        "refreshLibrary": "true",
    }
    status, body = request("/Library/VirtualFolders", "POST", token=token,
                           params=params)
    say(f"LIBRARY {status} {str(body)[:200]}")
    status, body = request("/Library/Refresh", "POST", token=token)
    say(f"REFRESH {status} {str(body)[:120]}")


def main() -> int:
    LOG.write_text("", encoding="utf-8")
    if not SERVER.exists():
        say("NO_SERVER")
        return 2
    ensure_music()
    for path in (DATA, CONFIG, CACHE, LOGS):
        shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        [str(SERVER), "--datadir", str(DATA), "--configdir", str(CONFIG),
         "--cachedir", str(CACHE), "--logdir", str(LOGS)],
        cwd=str(SERVER.parent), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_public():
            say("PUBLIC_TIMEOUT")
            return 3
        say("PUBLIC_READY")
        if not wait_startup():
            say("STARTUP_TIMEOUT")
            return 4
        say("STARTUP_READY")
        setup()
        status, body = request("/Startup/User")
        say(f"USER_AFTER {status} {str(body)[:120]}")
        status, body = request("/Users/AuthenticateByName", "POST", {
            "Username": USER, "Pw": PASSWORD,
        })
        say(f"RAW_LOGIN {status} {str(body)[:300]}")
        status, body = request("/Users/AuthenticateByName", "POST", {
            "Username": "PL", "Pw": PASSWORD,
        })
        say(f"RAW_LOGIN_PL {status} {str(body)[:300]}")
        client = JellyfinClient(BASE, USER, PASSWORD)
        try:
            client.login()
        except Exception as exc:
            say(f"LOGIN_ERROR {type(exc).__name__}: {exc}")
            return 5
        say(f"LOGIN token={bool(client.token)} user={client.user_id}")
        add_library(client.token)
        songs = []
        albums = []
        deadline = time.time() + 90
        while time.time() < deadline:
            try:
                songs = client.search_songs("test")
                albums = client.albums()
            except Exception as exc:
                say(f"SCAN_WAIT {type(exc).__name__}: {exc}")
            if songs or albums:
                break
            time.sleep(2)
        say(f"SEARCH {len(songs)} ALBUMS {len(albums)}")
        album_tracks = []
        if albums:
            try:
                album_tracks = client.album_songs(albums[0].id)
            except Exception as exc:
                say(f"ALBUM_SONGS_ERROR {type(exc).__name__}: {exc}")
            say(f"ALBUM_SONGS {len(album_tracks)}")
        cover_ok = False
        cover_bytes = 0
        if albums:
            try:
                with urllib.request.urlopen(
                    client.album_cover_url(albums[0]), timeout=20
                ) as response:
                    cover = response.read(4096)
                    cover_ok = response.status == 200 and bool(cover)
                    cover_bytes = len(cover)
            except Exception as exc:
                say(f"COVER_ERROR {type(exc).__name__}: {exc}")
            say(f"COVER {cover_ok} {cover_bytes}")
        stream_ok = False
        stream_bytes = 0
        if songs:
            with urllib.request.urlopen(client.stream_url(songs[0]), timeout=20) as response:
                stream_bytes = len(response.read(4096))
                stream_ok = response.status == 200
        result = {
            "login": True,
            "songs": len(songs),
            "albums": len(albums),
            "album_tracks": len(album_tracks),
            "cover": cover_ok,
            "cover_bytes": cover_bytes,
            "stream": stream_ok,
            "stream_bytes": stream_bytes,
        }
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        say("RESULT " + json.dumps(result, ensure_ascii=False))
        return 0 if songs and stream_ok and cover_ok else 6
    finally:
        process.terminate()
        try:
            process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill()
        say("SERVER_STOPPED")


if __name__ == "__main__":
    raise SystemExit(main())
