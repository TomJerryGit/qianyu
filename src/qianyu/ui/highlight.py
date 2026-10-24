# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Search-term highlighting for the library table."""
from __future__ import annotations

import re

from ..qt import (
    QColor, QFontMetrics, QPainter, QStyle, QStyledItemDelegate,
    QStyleOptionViewItem, Qt,
)


def query_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[\w\u4e00-\u9fff]+", str(text or ""),
                                         re.UNICODE) if len(token) >= 1]


def match_spans(text: str, tokens: list[str]) -> list[tuple[int, int]]:
    text = str(text or "")
    spans: list[tuple[int, int]] = []
    for token in tokens:
        if not token:
            continue
        for match in re.finditer(re.escape(token), text, re.IGNORECASE):
            start, end = match.span()
            if start < end:
                spans.append((start, end))
    if not spans:
        return []
    spans.sort()
    merged = [spans[0]]
    for start, end in spans[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    return merged


class HighlightDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tokens: list[str] = []
        self._highlight = QColor("#e0b45e")

    def set_query(self, text: str) -> None:
        self._tokens = query_tokens(text)
        if self.parent() is not None and hasattr(self.parent(), "viewport"):
            self.parent().viewport().update()

    def paint(self, painter: QPainter, option, index) -> None:
        if not self._tokens or index.column() not in (0, 1, 2):
            super().paint(painter, option, index)
            return
        text = str(index.data(Qt.DisplayRole) or "")
        spans = match_spans(text, self._tokens)
        if not spans:
            super().paint(painter, option, index)
            return
        style_option = QStyleOptionViewItem(option)
        style_option.text = ""
        widget = option.widget
        style = widget.style() if widget is not None else None
        if style is not None:
            style.drawControl(QStyle.CE_ItemViewItem, style_option, painter, widget)
        painter.save()
        painter.setClipRect(option.rect)
        selected = bool(option.state & QStyle.State_Selected)
        normal_color = option.palette.highlightedText().color() if selected else option.palette.text().color()
        highlight_color = QColor("#fff2d2") if selected else self._highlight
        font = option.font
        metrics = QFontMetrics(font)
        x = option.rect.left() + 6
        baseline = option.rect.top() + (option.rect.height() + metrics.ascent() - metrics.descent()) // 2
        cursor = 0
        right = option.rect.right() - 4
        for start, end in spans:
            if start > cursor:
                segment = text[cursor:start]
                painter.setFont(font)
                painter.setPen(normal_color)
                painter.drawText(x, baseline, segment)
                x += metrics.horizontalAdvance(segment)
            segment = text[start:end]
            bold = font
            bold.setBold(True)
            painter.setFont(bold)
            painter.setPen(highlight_color)
            painter.drawText(x, baseline, segment)
            x += metrics.horizontalAdvance(segment)
            if x > right:
                break
            cursor = end
        if cursor < len(text) and x <= right:
            painter.setFont(font)
            painter.setPen(normal_color)
            painter.drawText(x, baseline, text[cursor:])
        painter.restore()
