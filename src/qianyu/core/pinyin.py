# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Pinyin helpers for local fuzzy search."""
from __future__ import annotations

try:
    from pypinyin import Style, lazy_pinyin
except Exception:  # pragma: no cover - optional dependency
    Style = None
    lazy_pinyin = None


def variants(text: str) -> tuple[str, str]:
    """Return (full_pinyin, initials) in lower case; empty when unavailable."""
    text = str(text or "").strip()
    if not text or lazy_pinyin is None:
        return "", ""
    try:
        full = "".join(lazy_pinyin(text)).casefold().replace(" ", "")
        initials = "".join(lazy_pinyin(text, style=Style.FIRST_LETTER)).casefold()
        return full, initials
    except Exception:
        return "", ""
