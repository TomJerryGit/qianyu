# -*- coding: utf-8 -*-
"""Full-screen now-playing page with large cover, lyrics and blurred backdrop."""
from __future__ import annotations

from pathlib import Path

from ..qt import (
    QGraphicsBlurEffect, QHBoxLayout, QLabel, QListWidget, QPixmap, QPushButton,
    QSize, QVBoxLayout, QWidget, Qt, pyqtSignal,
)
from ..core.models import Track


class NowPlayingPage(QWidget):
    play_pause = pyqtSignal()
    previous_track = pyqtSignal()
    next_track = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window)
        self.setWindowTitle("浅语影音 · 正在播放")
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._background = QLabel(self)
        self._background.setScaledContents(True)
        self._blur = QGraphicsBlurEffect(self._background)
        self._blur.setBlurRadius(42)
        self._background.setGraphicsEffect(self._blur)
        self._background.lower()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(70, 55, 70, 40)
        layout.setSpacing(18)
        body = QHBoxLayout()
        body.setSpacing(54)
        self._cover = QLabel()
        self._cover.setObjectName("nowPageCover")
        self._cover.setFixedSize(380, 380)
        self._cover.setAlignment(Qt.AlignCenter)
        self._cover.setText("♪")
        body.addWidget(self._cover, 0, Qt.AlignVCenter)

        right = QVBoxLayout()
        right.setSpacing(8)
        self._title = QLabel("未在播放")
        self._title.setObjectName("nowPageTitle")
        self._meta = QLabel("")
        self._meta.setObjectName("nowPageMeta")
        self._lyrics = QListWidget()
        self._lyrics.setObjectName("nowPageLyrics")
        self._lyrics.setFocusPolicy(Qt.NoFocus)
        right.addWidget(self._title)
        right.addWidget(self._meta)
        right.addWidget(self._lyrics, 1)
        controls = QHBoxLayout()
        prev = QPushButton("上一首")
        prev.clicked.connect(self.previous_track)
        play = QPushButton("播放 / 暂停")
        play.clicked.connect(self.play_pause)
        nxt = QPushButton("下一首")
        nxt.clicked.connect(self.next_track)
        close = QPushButton("关闭")
        close.clicked.connect(self.close)
        controls.addWidget(prev)
        controls.addWidget(play)
        controls.addWidget(nxt)
        controls.addStretch(1)
        controls.addWidget(close)
        right.addLayout(controls)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)

    def set_track(self, track: Track) -> None:
        self._title.setText(track.title or Path(track.path).stem)
        meta = " · ".join(part for part in (track.artist, track.album) if part)
        self._meta.setText(meta or Path(track.path).parent.name)
        pixmap = QPixmap(track.cover) if track.cover else QPixmap()
        if pixmap.isNull():
            self._cover.setPixmap(QPixmap())
            self._cover.setText("♪")
            self._background.setPixmap(QPixmap())
            return
        self._background.setPixmap(pixmap.scaled(
            self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        ))
        self._cover.setPixmap(pixmap.scaled(
            QSize(380, 380), Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

    def set_lyrics(self, lines) -> None:
        self._lyrics.clear()
        for text in lines:
            self._lyrics.addItem(text)

    def set_position(self, index: int) -> None:
        if 0 <= index < self._lyrics.count():
            self._lyrics.setCurrentRow(index)
            self._lyrics.scrollToItem(self._lyrics.item(index), QListWidget.PositionAtCenter)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._background.setGeometry(self.rect())

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space:
            self.play_pause.emit()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)
