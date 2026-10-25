# -*- coding: utf-8 -*-
"""Query OSV for known vulnerabilities in shipped Python dependencies."""
from __future__ import annotations

import json
import sys
import urllib.request
from importlib import metadata

PACKAGES = ("PySide6", "PySide6-Essentials", "python-mpv", "mutagen", "Pillow",
            "pypinyin", "imageio-ffmpeg")
API = "https://api.osv.dev/v1/querybatch"


def installed_versions() -> list[tuple[str, str]]:
    mapping = {}
    for dist in metadata.distributions():
        name = (dist.metadata.get("Name") or "").strip()
        canonical = name.lower().replace("_", "-")
        mapping[canonical] = (name, dist.version)
    result = []
    for package in PACKAGES:
        canonical = package.lower().replace("_", "-")
        found = mapping.get(canonical)
        if found:
            result.append((package, found[1]))
    return result


def main() -> int:
    packages = installed_versions()
    if not packages:
        print("no packages found")
        return 2
    queries = [{"package": {"name": name, "ecosystem": "PyPI"}, "version": version}
               for name, version in packages]
    request = urllib.request.Request(
        API,
        data=json.dumps({"queries": queries}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "QianYu/0.9"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"OSV query failed: {type(exc).__name__}: {exc}")
        return 2
    findings = 0
    for (name, version), result in zip(packages, data.get("results", [])):
        vulns = result.get("vulns") or []
        if vulns:
            findings += len(vulns)
            print(f"{name} {version}: {len(vulns)} advisory(ies)")
            for vuln in vulns:
                print(f"  {vuln.get('id')} {vuln.get('summary', '')[:100]}")
        else:
            print(f"{name} {version}: clean")
    print(f"OSV: {findings} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
