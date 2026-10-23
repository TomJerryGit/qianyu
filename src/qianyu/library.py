# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""SQLite-backed local music library.

Scanning is deliberately boring: walk a folder, read tags with mutagen, upsert
rows in batches.  It runs in a worker thread in the UI, never on the main
thread.
"""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from .core.models import Track

AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".oga", ".opus",
    ".ape", ".wma", ".aiff", ".aif", ".alac", ".wv", ".dsf", ".dff",
}
FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS tracks_ai AFTER INSERT ON tracks BEGIN
    INSERT INTO tracks_fts(rowid, title, artist, album)
    VALUES (new.rowid, new.title, new.artist, new.album);
END;
CREATE TRIGGER IF NOT EXISTS tracks_ad AFTER DELETE ON tracks BEGIN
    INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album)
    VALUES ('delete', old.rowid, old.title, old.artist, old.album);
END;
CREATE TRIGGER IF NOT EXISTS tracks_au AFTER UPDATE ON tracks BEGIN
    INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album)
    VALUES ('delete', old.rowid, old.title, old.artist, old.album);
    INSERT INTO tracks_fts(rowid, title, artist, album)
    VALUES (new.rowid, new.title, new.artist, new.album);
END;
"""
SCHEMA = """
CREATE TABLE IF NOT EXISTS tracks (
    path TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    artist TEXT DEFAULT '',
    album TEXT DEFAULT '',
    duration REAL DEFAULT 0,
    track_no INTEGER DEFAULT 0,
    disc_no INTEGER DEFAULT 0,
    codec TEXT DEFAULT '',
    sample_rate INTEGER DEFAULT 0,
    channels INTEGER DEFAULT 0,
    bitrate INTEGER DEFAULT 0,
    mtime REAL DEFAULT 0,
    added_at REAL DEFAULT 0,
    cover TEXT DEFAULT '',
    cue_path TEXT DEFAULT '',
    start REAL DEFAULT 0,
    end REAL DEFAULT 0,
    favorite INTEGER DEFAULT 0,
    play_count INTEGER DEFAULT 0,
    last_played REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tracks_artist ON tracks(artist);
CREATE INDEX IF NOT EXISTS idx_tracks_album ON tracks(album);
CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(title COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_tracks_sort ON tracks(
    artist COLLATE NOCASE, album COLLATE NOCASE, disc_no, track_no, title
);
"""


@dataclass
class ScanResult:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0

    @property
    def total(self) -> int:
        return self.added + self.updated


class Library:
    def __init__(self, db_path: str | Path, covers_dir: str | Path | None = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.covers_dir = Path(covers_dir) if covers_dir else self.db_path.parent / "covers"
        try:
            self.covers_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Read-only/ACL-restricted profiles still get a working library;
            # only embedded-cover caching needs a writable directory.
            self.covers_dir = Path(tempfile.mkdtemp(prefix="qianyu-covers-"))
        with closing(self._connect()) as conn:
            conn.executescript(SCHEMA)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(tracks)")}
            if "cover" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN cover TEXT DEFAULT ''")
            if "cue_path" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN cue_path TEXT DEFAULT ''")
            if "start" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN start REAL DEFAULT 0")
            if "end" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN end REAL DEFAULT 0")
            if "favorite" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN favorite INTEGER DEFAULT 0")
            if "play_count" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN play_count INTEGER DEFAULT 0")
            if "last_played" not in columns:
                conn.execute("ALTER TABLE tracks ADD COLUMN last_played REAL DEFAULT 0")
            self._fts_ready = self._init_fts(conn)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-20000")
        conn.execute("PRAGMA temp_store=MEMORY")
        try:
            conn.execute("PRAGMA mmap_size=268435456")
        except sqlite3.DatabaseError:
            pass
        return conn

    @staticmethod
    def _init_fts(conn: sqlite3.Connection) -> bool:
        """Trigram FTS5 supports substring search for CJK and Latin text."""
        try:
            conn.execute(
                """CREATE VIRTUAL TABLE IF NOT EXISTS tracks_fts USING fts5(
                       title, artist, album,
                       content='tracks', content_rowid='rowid',
                       tokenize='trigram'
                   )"""
            )
            conn.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS tracks_ai AFTER INSERT ON tracks BEGIN
                    INSERT INTO tracks_fts(rowid, title, artist, album)
                    VALUES (new.rowid, new.title, new.artist, new.album);
                END;
                CREATE TRIGGER IF NOT EXISTS tracks_ad AFTER DELETE ON tracks BEGIN
                    INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album)
                    VALUES ('delete', old.rowid, old.title, old.artist, old.album);
                END;
                CREATE TRIGGER IF NOT EXISTS tracks_au AFTER UPDATE ON tracks BEGIN
                    INSERT INTO tracks_fts(tracks_fts, rowid, title, artist, album)
                    VALUES ('delete', old.rowid, old.title, old.artist, old.album);
                    INSERT INTO tracks_fts(rowid, title, artist, album)
                    VALUES (new.rowid, new.title, new.artist, new.album);
                END;
                """
            )
            rows = conn.execute("SELECT count(*) FROM tracks").fetchone()[0]
            indexed = conn.execute("SELECT count(*) FROM tracks_fts").fetchone()[0]
            if rows != indexed:
                conn.execute("INSERT INTO tracks_fts(tracks_fts) VALUES ('rebuild')")
            return True
        except sqlite3.DatabaseError:
            return False

    # ------------------------------------------------------------------
    # scanning
    # ------------------------------------------------------------------
    def scan(
        self,
        folder: str | Path,
        progress: Optional[Callable[[int, str], None]] = None,
        cancel: Optional[Callable[[], bool]] = None,
    ) -> ScanResult:
        result = ScanResult()
        root = Path(folder)
        from .core.cue import parse_cue

        cue_sheets = {}
        cue_audio: set[Path] = set()
        for path in self._walk(root):
            if path.suffix.lower() != ".cue":
                continue
            try:
                sheet = parse_cue(path)
            except Exception:
                continue
            if sheet.tracks:
                cue_sheets[path] = sheet
                cue_audio.update(Path(track.path) for track in sheet.tracks)
        audio_files = [
            p for p in self._walk(root)
            if p.suffix.lower() in AUDIO_EXTENSIONS and p.resolve() not in cue_audio
        ]
        files = audio_files + list(cue_sheets)
        conn = self._connect()
        rebuilt = False
        try:
            if self._fts_ready:
                conn.executescript(
                    "DROP TRIGGER IF EXISTS tracks_ai;"
                    "DROP TRIGGER IF EXISTS tracks_ad;"
                    "DROP TRIGGER IF EXISTS tracks_au;"
                )
            for audio in cue_audio:
                conn.execute("DELETE FROM tracks WHERE path=?", (str(audio),))
            for index, path in enumerate(files, 1):
                if cancel and cancel():
                    break
                if progress:
                    progress(index, str(path))
                try:
                    if path.suffix.lower() == ".cue":
                        self._scan_cue(conn, cue_sheets[path], result)
                        continue
                    stat = path.stat()
                    existing = conn.execute(
                        "SELECT mtime FROM tracks WHERE path=?", (str(path),)
                    ).fetchone()
                    if existing and abs(float(existing["mtime"]) - stat.st_mtime) < 1:
                        result.skipped += 1
                        continue
                    track = self._read_track(path)
                    if track is None:
                        result.errors += 1
                        continue
                    self._upsert(conn, track, stat.st_mtime)
                    if existing:
                        result.updated += 1
                    else:
                        result.added += 1
                except Exception:
                    result.errors += 1
            conn.commit()
            if self._fts_ready:
                conn.execute("INSERT INTO tracks_fts(tracks_fts) VALUES ('rebuild')")
                conn.executescript(FTS_TRIGGERS)
                conn.commit()
                rebuilt = True
        finally:
            if self._fts_ready and not rebuilt:
                try:
                    conn.executescript(FTS_TRIGGERS)
                    conn.commit()
                except sqlite3.DatabaseError:
                    pass
            conn.close()
        return result

    def _scan_cue(self, conn, sheet, result: ScanResult) -> None:
        cache: dict[str, Track] = {}
        keep = []
        for index, cue in enumerate(sheet.tracks):
            audio_path = Path(cue.path)
            if not audio_path.is_file():
                result.errors += 1
                continue
            base = cache.get(str(audio_path))
            if base is None:
                base = self._read_track(audio_path)
                if base is None:
                    result.errors += 1
                    continue
                cache[str(audio_path)] = base
            virtual_path = f"{audio_path}#cue:{index:02d}"
            keep.append(virtual_path)
            existing = conn.execute(
                "SELECT mtime FROM tracks WHERE path=?", (virtual_path,)
            ).fetchone()
            track = Track(
                path=virtual_path,
                title=cue.title or f"Track {cue.track_no:02d}",
                artist=cue.artist or sheet.performer,
                album=cue.album or sheet.title,
                duration=cue.duration,
                track_no=cue.track_no,
                disc_no=1,
                codec=base.codec,
                sample_rate=base.sample_rate,
                channels=base.channels,
                bitrate=base.bitrate,
                cover=base.cover,
                cue_path=sheet.cue_path,
                start=cue.start,
                end=cue.end,
            )
            mtime = max(
                audio_path.stat().st_mtime,
                Path(sheet.cue_path).stat().st_mtime,
            )
            self._upsert(conn, track, mtime)
            if existing:
                result.updated += 1
            else:
                result.added += 1
        if keep:
            placeholders = ",".join("?" for _ in keep)
            conn.execute(
                f"DELETE FROM tracks WHERE cue_path=? AND path NOT IN ({placeholders})",
                (sheet.cue_path, *keep),
            )

    @staticmethod
    def _walk(root: Path) -> Iterable[Path]:
        if not root.exists():
            return
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for name in filenames:
                if not name.startswith("."):
                    yield Path(dirpath) / name

    def _read_track(self, path: Path) -> Optional[Track]:
        import mutagen
        from mutagen import File as MutagenFile

        try:
            audio = MutagenFile(str(path), easy=True)
        except Exception:
            audio = None
        title = path.stem
        artist = album = ""
        duration = track_no = disc_no = 0.0
        codec = sample_rate = channels = bitrate = 0
        if audio is not None:
            tags = getattr(audio, "tags", None) or {}
            try:
                title = str(tags.get("title", [title])[0] or title)
                artist = str(tags.get("artist", [""])[0] or "")
                album = str(tags.get("album", [""])[0] or "")
                track_no = int(str(tags.get("tracknumber", ["0"])[0]).split("/")[0] or 0)
                disc_no = int(str(tags.get("discnumber", ["0"])[0]).split("/")[0] or 0)
            except (ValueError, IndexError, TypeError):
                pass
            info = getattr(audio, "info", None)
            if info is not None:
                duration = float(getattr(info, "length", 0.0) or 0.0)
                sample_rate = int(getattr(info, "sample_rate", 0) or 0)
                channels = int(getattr(info, "channels", 0) or 0)
                bitrate = int(getattr(info, "bitrate", 0) or 0)
            codec = type(audio).__name__.lower()
        try:
            if not duration:
                duration = float(mutagen.File(str(path)).info.length)
        except Exception:
            pass
        cover = self._cover_for(path, audio)
        return Track(
            path=str(path), title=title, artist=artist, album=album,
            duration=duration, track_no=int(track_no), disc_no=int(disc_no),
            codec=codec, sample_rate=sample_rate, channels=channels,
            bitrate=bitrate, cover=cover,
        )

    def _cover_for(self, path: Path, audio) -> str:
        for name in ("cover.jpg", "cover.jpeg", "cover.png", "folder.jpg",
                     "folder.jpeg", "folder.png", "front.jpg", "album.jpg"):
            candidate = path.parent / name
            if candidate.exists():
                return str(candidate)
        for suffix in (".jpg", ".jpeg", ".png"):
            candidate = path.with_suffix(suffix)
            if candidate.exists():
                return str(candidate)
        data = self._embedded_cover(audio)
        if not data:
            return ""
        payload, mime = data
        digest = hashlib.sha1(f"{path}|{path.stat().st_mtime_ns}".encode("utf-8")).hexdigest()
        extension = ".png" if "png" in (mime or "").lower() else ".jpg"
        target = self.covers_dir / f"{digest}{extension}"
        if not target.exists():
            try:
                target.write_bytes(payload)
            except OSError:
                return ""
        return str(target)

    @staticmethod
    def _embedded_cover(audio) -> tuple[bytes, str] | None:
        if audio is None:
            return None
        tags = getattr(audio, "tags", None)
        try:
            if tags is not None and hasattr(tags, "getall"):
                pictures = tags.getall("APIC")
                if pictures:
                    return bytes(pictures[0].data), getattr(pictures[0], "mime", "image/jpeg")
        except Exception:
            pass
        try:
            pictures = getattr(audio, "pictures", None)
            if pictures:
                return bytes(pictures[0].data), getattr(pictures[0], "mime", "image/jpeg")
        except Exception:
            pass
        try:
            if tags is not None and "covr" in tags:
                value = tags["covr"][0]
                return bytes(value), "image/jpeg"
        except Exception:
            pass
        return None

    @staticmethod
    def _upsert(conn: sqlite3.Connection, track: Track, mtime: float) -> None:
        import time

        conn.execute(
            """INSERT INTO tracks(path,title,artist,album,duration,track_no,disc_no,
                                  codec,sample_rate,channels,bitrate,mtime,added_at,cover,
                                  cue_path,start,end)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET
                 title=excluded.title, artist=excluded.artist, album=excluded.album,
                 duration=excluded.duration, track_no=excluded.track_no,
                 disc_no=excluded.disc_no, codec=excluded.codec,
                 sample_rate=excluded.sample_rate, channels=excluded.channels,
                 bitrate=excluded.bitrate, mtime=excluded.mtime, cover=excluded.cover,
                 cue_path=excluded.cue_path, start=excluded.start, end=excluded.end""",
            (
                track.path, track.title, track.artist, track.album, track.duration,
                track.track_no, track.disc_no, track.codec, track.sample_rate,
                track.channels, track.bitrate, mtime, time.time(), track.cover,
                track.cue_path, track.start, track.end,
            ),
        )

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------
    def tracks(self) -> list[Track]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM tracks ORDER BY artist COLLATE NOCASE, album COLLATE NOCASE, disc_no, track_no, title"
            ).fetchall()
        return [self._row_to_track(row) for row in rows]

    def search(self, keyword: str) -> list[Track]:
        keyword = keyword.strip()
        if not keyword:
            return self.tracks()
        if getattr(self, "_fts_ready", False) and len(keyword) >= 3:
            tokens = re.findall(r"[\w\u4e00-\u9fff]+", keyword, re.UNICODE)
            if tokens:
                query = " ".join(f'"{token}"' for token in tokens)
                try:
                    with closing(self._connect()) as conn:
                        rows = conn.execute(
                            """SELECT t.* FROM tracks t
                               JOIN tracks_fts f ON f.rowid = t.rowid
                               WHERE tracks_fts MATCH ?
                               ORDER BY t.artist COLLATE NOCASE, t.album COLLATE NOCASE,
                                        t.track_no, t.title""",
                            (query,),
                        ).fetchall()
                    return [self._row_to_track(row) for row in rows]
                except sqlite3.DatabaseError:
                    pass
        like = f"%{keyword}%"
        with closing(self._connect()) as conn:
            rows = conn.execute(
                """SELECT * FROM tracks
                   WHERE title LIKE ? OR artist LIKE ? OR album LIKE ? OR path LIKE ?
                   ORDER BY artist COLLATE NOCASE, album COLLATE NOCASE, track_no, title""",
                (like, like, like, like),
            ).fetchall()
        return [self._row_to_track(row) for row in rows]

    def get(self, path: str) -> Optional[Track]:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM tracks WHERE path=?", (path,)).fetchone()
        return self._row_to_track(row) if row else None

    def update_metadata(self, path: str, fields: dict[str, str]) -> None:
        allowed = {"title", "artist", "album", "track_no", "disc_no"}
        sets = []
        values = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            sets.append(f"{key}=?")
            values.append(value)
        if not sets:
            return
        values.append(path)
        with closing(self._connect()) as conn:
            conn.execute(f"UPDATE tracks SET {', '.join(sets)} WHERE path=?", values)
            conn.commit()

    def set_favorite(self, path: str, favorite: bool) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE tracks SET favorite=? WHERE path=?",
                (1 if favorite else 0, path),
            )
            conn.commit()

    def mark_played(self, path: str) -> None:
        import time

        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE tracks SET play_count=play_count+1, last_played=? WHERE path=?",
                (time.time(), path),
            )
            conn.commit()

    def set_cover(self, path: str, cover: str) -> None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT cue_path FROM tracks WHERE path=?", (path,)).fetchone()
            conn.execute("UPDATE tracks SET cover=? WHERE path=?", (cover, path))
            if row is not None and row["cue_path"]:
                conn.execute(
                    "UPDATE tracks SET cover=? WHERE cue_path=?",
                    (cover, row["cue_path"]),
                )
            conn.commit()

    def remove_paths(self, paths: Iterable[str]) -> int:
        removed = 0
        with closing(self._connect()) as conn:
            for path in paths:
                removed += conn.execute("DELETE FROM tracks WHERE path=?", (path,)).rowcount
            conn.commit()
        return removed

    @staticmethod
    def _fingerprint(path: str) -> str:
        file_path = Path(path)
        stat = file_path.stat()
        digest = hashlib.sha1()
        digest.update(str(stat.st_size).encode())
        with file_path.open("rb") as handle:
            digest.update(handle.read(64 * 1024))
            if stat.st_size > 64 * 1024:
                handle.seek(max(0, stat.st_size - 64 * 1024))
                digest.update(handle.read(64 * 1024))
        return digest.hexdigest()

    def find_duplicates(self, deep: bool = False) -> list[list[Track]]:
        """Group same title/artist/duration, then confirm by file fingerprint.

        With deep=True, ask Chromaprint via fpcalc for an acoustic fingerprint
        and group recordings with >=90% similarity.
        """
        with closing(self._connect()) as conn:
            candidates = conn.execute(
                """SELECT lower(title) AS t, lower(artist) AS a, round(duration) AS d
                   FROM tracks GROUP BY t, a, d HAVING count(*) > 1"""
            ).fetchall()
            groups: list[list[Track]] = []
            for candidate in candidates:
                rows = conn.execute(
                    """SELECT * FROM tracks
                       WHERE lower(title)=? AND lower(artist)=? AND round(duration)=?
                       ORDER BY path""",
                    (candidate["t"], candidate["a"], candidate["d"]),
                ).fetchall()
                tracks = [self._row_to_track(row) for row in rows]
                by_fingerprint: dict[str, list[Track]] = {}
                for track in tracks:
                    try:
                        key = self._fingerprint(track.path)
                    except OSError:
                        continue
                    by_fingerprint.setdefault(key, []).append(track)
                for same in by_fingerprint.values():
                    if len(same) > 1:
                        groups.append(same)
            if deep:
                from .core.fingerprint import (
                    audio_fingerprint, content_fingerprint, envelope_similarity,
                    find_fpcalc, similarity,
                )

                use_chromaprint = bool(find_fpcalc())
                rows = conn.execute(
                    """SELECT lower(title) AS t, lower(artist) AS a
                       FROM tracks GROUP BY t, a HAVING count(*) > 1"""
                ).fetchall()
                for candidate in rows:
                    tracks = [self._row_to_track(row) for row in conn.execute(
                        """SELECT * FROM tracks WHERE lower(title)=? AND lower(artist)=?
                           ORDER BY path""", (candidate["t"], candidate["a"])
                    ).fetchall()]
                    fingerprinted = []
                    for track in tracks:
                        fp = audio_fingerprint(track.path) if use_chromaprint \
                            else content_fingerprint(track.path)
                        if fp:
                            fingerprinted.append((track, fp))
                    while fingerprinted:
                        base, base_fp = fingerprinted.pop(0)
                        same = [base]
                        remaining = []
                        for track, fp in fingerprinted:
                            score = similarity(base_fp, fp) if use_chromaprint \
                                else envelope_similarity(base_fp, fp)
                            if score >= 0.90:
                                same.append(track)
                            else:
                                remaining.append((track, fp))
                        fingerprinted = remaining
                        if len(same) > 1:
                            groups.append(same)
        return groups

    def count(self) -> int:
        with closing(self._connect()) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0])

    def remove_missing(self) -> int:
        removed = 0
        with closing(self._connect()) as conn:
            for row in conn.execute("SELECT path, cue_path FROM tracks").fetchall():
                path = row["path"]
                cue_path = row["cue_path"] or ""
                if cue_path:
                    if Path(cue_path).is_file() and Path(path.split("#cue:", 1)[0]).is_file():
                        continue
                elif Path(path).is_file():
                    continue
                conn.execute("DELETE FROM tracks WHERE path=?", (path,))
                removed += 1
            conn.commit()
        return removed

    @staticmethod
    def _row_to_track(row: sqlite3.Row) -> Track:
        return Track(
            path=row["path"], title=row["title"], artist=row["artist"],
            album=row["album"], duration=row["duration"], track_no=row["track_no"],
            disc_no=row["disc_no"], codec=row["codec"], sample_rate=row["sample_rate"],
            channels=row["channels"], bitrate=row["bitrate"], cover=row["cover"] or "",
            cue_path=(row["cue_path"] or "") if "cue_path" in row.keys() else "",
            start=float(row["start"] or 0) if "start" in row.keys() else 0.0,
            end=float(row["end"] or 0) if "end" in row.keys() else 0.0,
            favorite=bool(row["favorite"]) if "favorite" in row.keys() else False,
            play_count=int(row["play_count"] or 0) if "play_count" in row.keys() else 0,
            last_played=float(row["last_played"] or 0) if "last_played" in row.keys() else 0.0,
            added_at=float(row["added_at"] or 0) if "added_at" in row.keys() else 0.0,
        )
