# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
"""Update manifest check, optional Ed25519 signature, and SHA-256 download.

A production release should configure `update_public_key`, sign the canonical
manifest with the offline private key, and sign the installer itself. SHA-256
alone only protects transport integrity, not authenticity.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class UpdateInfo:
    version: str
    url: str
    sha256: str = ""
    notes: str = ""


def _parts(version: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", version)
    return tuple(int(n) for n in numbers[:3]) or (0,)


def is_newer(current: str, latest: str) -> bool:
    return _parts(latest) > _parts(current)


def parse_manifest(payload: bytes) -> UpdateInfo:
    data = json.loads(payload.decode("utf-8"))
    version = str(data.get("version", "")).strip()
    url = str(data.get("url", "")).strip()
    if not version or not url:
        raise ValueError("manifest requires version and url")
    return UpdateInfo(
        version=version,
        url=url,
        sha256=str(data.get("sha256", "")).lower(),
        notes=str(data.get("notes", "")),
    )


def canonical_manifest(payload: bytes) -> bytes:
    """Canonical signed bytes: JSON without the `signature` field."""
    data = json.loads(payload.decode("utf-8"))
    data.pop("signature", None)
    return json.dumps(data, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def verify_manifest(payload: bytes, public_key_b64: str) -> UpdateInfo:
    """Verify an Ed25519 signature over canonical_manifest(payload)."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("cryptography is required for signed updates") from exc
    data = json.loads(payload.decode("utf-8"))
    signature = data.get("signature")
    if not signature:
        raise ValueError("manifest is missing signature")
    key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    key.verify(base64.b64decode(signature), canonical_manifest(payload))
    return parse_manifest(payload)


def fetch_manifest(url: str, timeout: float = 8.0, public_key: str = "") -> UpdateInfo:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = response.read()
    if public_key:
        return verify_manifest(payload, public_key)
    return parse_manifest(payload)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_update(info: UpdateInfo, destination: str | Path, timeout: float = 60.0) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(info.url, timeout=timeout) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    if info.sha256 and sha256_file(destination) != info.sha256.lower():
        destination.unlink(missing_ok=True)
        raise ValueError("update SHA-256 mismatch")
    return destination
