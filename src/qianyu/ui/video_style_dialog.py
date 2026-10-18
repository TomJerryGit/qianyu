# -*- coding: utf-8 -*-
"""Subtitle style and video color dialogs for the 1.0 video window."""
from __future__ import annotations

from ..qt import Qt
from ..qt import QColor
from ..qt import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFontComboBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget,
)

DEFAULT_SUBTITLE = {
    "font": "Microsoft YaHei",
    "size": 36,
    "color": "#FFFFFF",
    "border": 2.0,
    "delay": 0.0,
    "position": "bottom",
    "bold": False,
    "italic": False,
    "codepage": "auto",
}

DEFAULT_COLOR = {"brightness": 0, "contrast": 0, "saturation": 0, "gamma": 0}
DEFAULT_HDR = {
    "tone_mapping": "bt.2390",
    "target_peak": "auto",
    "compute_peak": True,
    "target_hint": True,
}


class SubtitleStyleDialog(QDialog):
    def __init__(self, style: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("字幕样式")
        self.resize(460, 320)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._font = QFontComboBox()
        self._font.setCurrentFont(self._font.currentFont())
        self._font.setCurrentText(str(style.get("font", "Microsoft YaHei")))
        form.addRow("字体", self._font)

        self._size = QSpinBox()
        self._size.setRange(10, 72)
        self._size.setValue(int(style.get("size", 36)))
        form.addRow("字号", self._size)

        color_row = QHBoxLayout()
        self._color_edit = QLineEdit(str(style.get("color", "#FFFFFF")))
        self._color_edit.setMaximumWidth(120)
        pick = QPushButton("选择…")
        pick.clicked.connect(self._pick_color)
        color_row.addWidget(self._color_edit)
        color_row.addWidget(pick)
        color_row.addStretch(1)
        wrapper = QWidget()
        wrapper.setLayout(color_row)
        form.addRow("颜色", wrapper)

        self._border = QDoubleSpinBox()
        self._border.setRange(0, 10)
        self._border.setSingleStep(0.5)
        self._border.setValue(float(style.get("border", 2.0)))
        form.addRow("描边", self._border)

        self._delay = QDoubleSpinBox()
        self._delay.setRange(-10, 10)
        self._delay.setSingleStep(0.1)
        self._delay.setDecimals(1)
        self._delay.setSuffix(" s")
        self._delay.setValue(float(style.get("delay", 0.0)))
        form.addRow("延迟", self._delay)

        self._position = QComboBox()
        for label, value in (("底部", "bottom"), ("居中", "center"), ("顶部", "top")):
            self._position.addItem(label, value)
        pos = str(style.get("position", "bottom"))
        index = self._position.findData(pos)
        self._position.setCurrentIndex(max(0, index))
        form.addRow("位置", self._position)

        self._codepage = QComboBox()
        for label, value in (("自动", "auto"), ("UTF-8", "utf-8"), ("GBK", "gbk"),
                             ("GB18030", "gb18030"), ("BIG5", "big5"),
                             ("UTF-16LE", "utf-16le"), ("UTF-16BE", "utf-16be")):
            self._codepage.addItem(label, value)
        code_index = self._codepage.findData(str(style.get("codepage", "auto")))
        self._codepage.setCurrentIndex(max(0, code_index))
        form.addRow("编码", self._codepage)

        flags = QHBoxLayout()
        self._bold = QCheckBox("粗体")
        self._bold.setChecked(bool(style.get("bold", False)))
        self._italic = QCheckBox("斜体")
        self._italic.setChecked(bool(style.get("italic", False)))
        flags.addWidget(self._bold)
        flags.addWidget(self._italic)
        flags.addStretch(1)
        flag_widget = QWidget()
        flag_widget.setLayout(flags)
        form.addRow("样式", flag_widget)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color_edit.text() or "#FFFFFF"), self, "字幕颜色")
        if color.isValid():
            self._color_edit.setText(color.name().upper())

    def values(self) -> dict:
        return {
            "font": self._font.currentText(),
            "size": int(self._size.value()),
            "color": self._color_edit.text().strip() or "#FFFFFF",
            "border": float(self._border.value()),
            "delay": float(self._delay.value()),
            "position": str(self._position.currentData()),
            "bold": self._bold.isChecked(),
            "italic": self._italic.isChecked(),
            "codepage": str(self._codepage.currentData()),
        }


class ColorAdjustDialog(QDialog):
    def __init__(self, values: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("色彩调整")
        self.resize(380, 300)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._sliders = {}
        self._labels = {}
        for key, label in (("brightness", "亮度"), ("contrast", "对比度"),
                           ("saturation", "饱和度"), ("gamma", "伽马")):
            row = QHBoxLayout()
            slider = QSlider(Qt.Horizontal)
            slider.setRange(-100, 100)
            slider.setValue(int(values.get(key, 0)))
            value_label = QLabel(str(slider.value()))
            slider.valueChanged.connect(lambda value, lab=value_label: lab.setText(str(value)))
            row.addWidget(slider, 1)
            row.addWidget(value_label)
            holder = QWidget()
            holder.setLayout(row)
            form.addRow(label, holder)
            self._sliders[key] = slider
            self._labels[key] = value_label
        layout.addLayout(form)
        reset = QPushButton("重置为 0")
        reset.clicked.connect(self._reset)
        layout.addWidget(reset)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _reset(self) -> None:
        for slider in self._sliders.values():
            slider.setValue(0)

    def values(self) -> dict:
        return {key: int(slider.value()) for key, slider in self._sliders.items()}


class HdrDialog(QDialog):
    def __init__(self, values: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HDR 色调映射")
        self.resize(420, 240)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._tone = QComboBox()
        for label, value in (("BT.2390（推荐）", "bt.2390"), ("Spline", "spline"),
                             ("Mobius", "mobius"), ("Reinhard", "reinhard"),
                             ("Hable", "hable"), ("Clip", "clip")):
            self._tone.addItem(label, value)
        index = self._tone.findData(str(values.get("tone_mapping", "bt.2390")))
        self._tone.setCurrentIndex(max(0, index))
        form.addRow("色调映射", self._tone)

        self._peak_target = QComboBox()
        for label, value in (("自动", "auto"), ("100 nits", "100"), ("200 nits", "200"),
                             ("300 nits", "300"), ("500 nits", "500"), ("1000 nits", "1000")):
            self._peak_target.addItem(label, value)
        target_index = self._peak_target.findData(str(values.get("target_peak", "auto")))
        self._peak_target.setCurrentIndex(max(0, target_index))
        form.addRow("目标峰值", self._peak_target)

        self._peak = QCheckBox("计算源峰值（hdr-compute-peak）")
        self._peak.setChecked(bool(values.get("compute_peak", True)))
        form.addRow("", self._peak)

        self._hint = QCheckBox("向显示端传递 HDR 元数据（target-colorspace-hint）")
        self._hint.setChecked(bool(values.get("target_hint", True)))
        form.addRow("", self._hint)

        layout.addLayout(form)
        note = QLabel("真实 HDR10/HLG 验收仍需 HDR 显示器与样片；本页只控制 mpv 映射参数。")
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "tone_mapping": str(self._tone.currentData()),
            "target_peak": str(self._peak_target.currentData()),
            "compute_peak": self._peak.isChecked(),
            "target_hint": self._hint.isChecked(),
        }
