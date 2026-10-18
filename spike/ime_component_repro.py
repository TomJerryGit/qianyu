# -*- coding: utf-8 -*-
"""Small Qt component reproductions for the IME crash."""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication, QLineEdit, QListWidget, QMainWindow, QMenu, QSystemTrayIcon,
    QTableView, QVBoxLayout, QWidget,
)
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtCore import QTimer

mode = os.environ.get("QIANYU_IME_MODE", "edit")
app = QApplication(sys.argv)
window = QMainWindow()
central = QWidget()
layout = QVBoxLayout(central)
layout.addWidget(QLineEdit("IME test"))

if mode == "timer":
    timer = QTimer(window)
    timer.timeout.connect(lambda: None)
    timer.start(200)

if mode in ("table", "all"):
    model = QStandardItemModel(100, 4)
    for row in range(100):
        for column in range(4):
            model.setItem(row, column, QStandardItem(f"cell {row}/{column}"))
    table = QTableView()
    table.setModel(model)
    layout.addWidget(table)

if mode in ("list", "all"):
    listing = QListWidget()
    for index in range(100):
        listing.addItem(f"item {index}")
    layout.addWidget(listing)

window.setCentralWidget(central)
window.resize(700, 500)

if mode in ("tray", "all"):
    tray = QSystemTrayIcon(QIcon(), window)
    menu = QMenu(window)
    menu.addAction("Test")
    tray.setContextMenu(menu)
    tray.show()

if mode in ("qss", "all"):
    app.setStyleSheet("QWidget { background: #171923; color: #ffffff; }")

window.show()
app.processEvents()
os._exit(0)
