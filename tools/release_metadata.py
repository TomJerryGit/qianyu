# -*- coding: utf-8 -*-
"""Generate release SBOM / license inventory without third-party services.

The output is intentionally simple and reproducible:
  dist/release-meta/sbom.json
  dist/release-meta/THIRD_PARTY_LICENSES.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from importlib import metadata
from pathlib import Path

PACKAGE_LICENSES = {
    "PySide6": "LGPL-3.0 / GPL-3.0 / commercial",
    "PySide6-Essentials": "LGPL-3.0 / GPL-3.0 / commercial",
    "PyQt5": "GPL-3.0 / commercial",
    "python-mpv": "GPL-2.0-or-later",
    "mutagen": "GPL-2.0-or-later",
    "Pillow": "MIT-CMU",
    "pypinyin": "MIT",
    "imageio-ffmpeg": "BSD-2-Clause",
    "cryptography": "Apache-2.0 OR BSD-3-Clause",
    "numpy": "BSD-3-Clause",
    "coverage": "Apache-2.0",
}
SHIPPED = ("PySide6", "PySide6-Essentials", "python-mpv", "mutagen", "Pillow",
           "pypinyin", "imageio-ffmpeg", "cryptography")


def _canonical(name: str) -> str:
    return str(name or "").strip().lower().replace("_", "-")


SHIPPED_CANONICAL = {_canonical(name) for name in SHIPPED}


def _license_of(dist) -> str:
    name = _canonical(dist.metadata.get("Name") or "")
    for key, value in PACKAGE_LICENSES.items():
        if name == _canonical(key):
            return value
    raw = dist.metadata.get("License-Expression") or dist.metadata.get("License") or ""
    raw = raw.strip()
    if raw and raw.upper() != "UNKNOWN":
        return raw
    classifiers = [item for item in dist.metadata.get_all("Classifier") or []
                   if item.startswith("License ::")]
    return "; ".join(classifiers) or "UNKNOWN"


def _components() -> list[dict]:
    found = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") or ""
        if not name:
            continue
        canonical = _canonical(name)
        if canonical not in SHIPPED_CANONICAL:
            continue
        found[canonical] = {
            "type": "library",
            "name": name,
            "version": dist.version,
            "licenses": [{"license": {"name": _license_of(dist)}}],
            "purl": f"pkg:pypi/{canonical}@{dist.version}",
        }
    # Native components that are not Python distributions.
    found["libmpv"] = {
        "type": "library",
        "name": "libmpv",
        "version": "system/bundled",
        "licenses": [{"license": {"name": "GPL-2.0-or-later / LGPL-2.1-or-later"}}],
    }
    try:
        import imageio_ffmpeg

        output = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-version"],
            capture_output=True, text=True, timeout=10,
        )
        first = (output.stdout or "").splitlines()[0] if output.stdout else "FFmpeg"
    except Exception:
        first = "FFmpeg"
    found["FFmpeg"] = {
        "type": "application",
        "name": "FFmpeg",
        "version": first[:120],
        "licenses": [{"license": {"name": "LGPL/GPL build-dependent"}}],
    }
    return sorted(found.values(), key=lambda item: item["name"].lower())


def _markdown(components: list[dict]) -> str:
    lines = [
        "# Third-party components",
        "",
        "Generated from the release environment. Verify the final binary package",
        "and license texts before publishing.",
        "",
        "| Component | Version | License |",
        "|---|---|---|",
    ]
    for component in components:
        license_name = component["licenses"][0]["license"]["name"]
        lines.append(f"| {component['name']} | {component['version']} | {license_name} |")
    lines += [
        "",
        "FFmpeg and libmpv are distributed as separate native components; their",
        "exact license depends on the build. QianYu does not relicense them.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="dist/release-meta")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    components = _components()
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "QianYu",
                "version": "0.9.0",
                "licenses": [{"license": {"name": "GPL-3.0-only"}}],
            }
        },
        "components": components,
    }
    (output / "sbom.json").write_text(
        json.dumps(sbom, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "THIRD_PARTY_LICENSES.md").write_text(
        _markdown(components), encoding="utf-8"
    )
    print(f"wrote {output / 'sbom.json'}")
    print(f"wrote {output / 'THIRD_PARTY_LICENSES.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
