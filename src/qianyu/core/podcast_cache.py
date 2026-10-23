# -*- coding: utf-8 -*-
"""Offline cache for podcast episodes."""
from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

USER_AGENT = "QianYu/0.9 (local media player)"
AUDIO_SUFFIXES = {".mp3", ".m4a", ".m4b", ".aac", ".ogg", ".opus", ".wav", ".flac", ".mp4"}


class PodcastCache:
    def __init__(self, root: str | Path, limit_mb: int = 2048):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.limit_bytes = max(64, int(limit_mb)) * 1024 * 1024
        self.index_path = self.root / "index.json"
        self._index = self._load()

    def _load(self) -> dict:
        try:
            raw = json.loads(self.index_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        tmp = self.index_path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.index_path)
        except OSError:
            pass

    def _key(self, url: str) -> str:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()[:24]

    def path_for(self, url: str) -> Path:
        suffix = Path(urllib.parse.urlparse(url).path).suffix.lower()
        if suffix not in AUDIO_SUFFIXES:
            suffix = ".mp3"
        return self.root / (self._key(url) + suffix)

    def get(self, url: str) -> Path | None:
        entry = self._index.get(url)
        if not isinstance(entry, dict):
            return None
        path = self.root / str(entry.get("file", ""))
        try:
            if path.is_file() and path.stat().st_size > 0:
                return path
        except OSError:
            pass
        return None

    def is_downloaded(self, url: str) -> bool:
        return self.get(url) is not None

    def total_bytes(self) -> int:
        total = 0
        for entry in self._index.values():
            try:
                total += (self.root / str(entry.get("file", ""))).stat().st_size
            except OSError:
                pass
        return total

    def download(self, url: str, title: str = "", timeout: float = 30.0,
                 progress: Callable[[int, int], None] | None = None,
                 cancelled: Callable[[], bool] | None = None) -> Path:
        existing = self.get(url)
        if existing is not None:
            return existing
        path = self.path_for(url)
        temp = path.with_suffix(path.suffix + ".part")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response, temp.open("wb") as handle:
                total = int(response.headers.get("Content-Length") or 0)
                done = 0
                while True:
                    if cancelled is not None and cancelled():
                        raise RuntimeError("下载已取消")
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    done += len(chunk)
                    if progress is not None:
                        progress(done, total)
        except Exception:
            try:
                temp.unlink()
            except OSError:
                pass
            raise
        if temp.stat().st_size <= 0:
            temp.unlink(missing_ok=True)
            raise RuntimeError("下载得到空文件")
        os.replace(temp, path)
        self._index[url] = {
            "file": path.name,
            "title": title,
            "size": path.stat().st_size,
            "downloaded_at": int(time.time()),
        }
        self._save()
        self.prune()
        return path

    def remove(self, url: str) -> bool:
        entry = self._index.pop(url, None)
        if entry is None:
            self._save()
            return False
        path = self.root / str(entry.get("file", ""))
        try:
            path.unlink()
        except OSError:
            pass
        self._save()
        return True

    def prune(self) -> None:
        entries = sorted(
            self._index.items(),
            key=lambda item: int(item[1].get("downloaded_at", 0)) if isinstance(item[1], dict) else 0,
        )
        total = self.total_bytes()
        for url, entry in entries:
            if total <= self.limit_bytes:
                break
            path = self.root / str(entry.get("file", ""))
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            try:
                path.unlink()
            except OSError:
                pass
            total -= size
            self._index.pop(url, None)
        self._save()
