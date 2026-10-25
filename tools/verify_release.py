# -*- coding: utf-8 -*-
"""Verify a QianYu release directory against SHA256SUMS.txt."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def parse_sums(path: Path) -> list[tuple[str, str]]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ValueError(f"invalid checksum line: {line}")
        entries.append((parts[1].lstrip("*"), parts[0].lower()))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", nargs="?", default="dist")
    args = parser.parse_args()
    return verify_directory(Path(args.directory))


def verify_directory(root: Path) -> int:
    root = Path(root)
    sums = root / "SHA256SUMS.txt"
    if not sums.is_file():
        print(f"missing {sums}")
        return 2
    failures = 0
    entries = parse_sums(sums)
    index = {path.name: path for path in root.rglob("*") if path.is_file()}
    for name, expected in entries:
        path = index.get(name)
        if path is None:
            print(f"MISSING {name}")
            failures += 1
            continue
        actual = sha256(path)
        if actual != expected:
            print(f"MISMATCH {name}: {actual} != {expected}")
            failures += 1
        else:
            print(f"OK {name}")
    print(f"verified {len(entries) - failures}/{len(entries)} assets")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
