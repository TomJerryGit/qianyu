# -*- coding: utf-8 -*-
"""Very small secret scanner for the repository (CI/release guard)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "dist", "build", "build-pyside6", "dist-pyside6", "tools", ".venv", "venv"}
TEXT_SUFFIXES = {".py", ".md", ".yml", ".yaml", ".toml", ".ini", ".ps1", ".cmd",
                 ".spec", ".iss", ".txt", ".json"}
PATTERNS = {
    "github token": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    "github pat": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "openai key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "aws key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "signpath token": re.compile(r"SIGNPATH_API_TOKEN\s*=\s*['\"][^'\"]+['\"]"),
}


def iter_files():
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        yield path


def main() -> int:
    findings = []
    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append((path.relative_to(ROOT), line, name))
    for path, line, name in findings:
        print(f"{path}:{line}: {name}")
    print(f"secret scan: {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
