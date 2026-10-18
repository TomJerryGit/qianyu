# -*- coding: utf-8 -*-
"""Minimal PySide6 + QLineEdit + show reproduction for the IME crash."""
import os
import sys

from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow

app = QApplication(sys.argv)
window = QMainWindow()
edit = QLineEdit()
edit.setPlaceholderText("IME minimal reproduction")
window.setCentralWidget(edit)
window.resize(480, 160)
window.show()
app.processEvents()
os._exit(0)
