# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""WASAPI loopback capture for real-time spectrum on streams.

Uses only ctypes; captures the default render endpoint in shared loopback mode.
FFmpeg is not involved. The class is deliberately conservative: any COM error
is raised to the caller, which falls back to the decorative spectrum.
"""
from __future__ import annotations

import array
import ctypes
import time
from ctypes import wintypes

ole32 = ctypes.windll.ole32

HRESULT = ctypes.c_long
CLSCTX_ALL = 23


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid(text: str) -> GUID:
    value = GUID()
    parts = text.strip("{}").split("-")
    value.Data1 = int(parts[0], 16)
    value.Data2 = int(parts[1], 16)
    value.Data3 = int(parts[2], 16)
    for index, byte in enumerate(bytes.fromhex(parts[3] + parts[4])):
        value.Data4[index] = byte
    return value


CLSID_MMDeviceEnumerator = _guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_IMMDeviceEnumerator = _guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
IID_IAudioClient = _guid("{1CB9AD4C-DBFA-4C32-B178-C2F568A703B2}")
IID_IAudioCaptureClient = _guid("{C8ADBD64-E71E-48A0-A4DE-185C395CD317}")
AUDCLNT_STREAMFLAGS_LOOPBACK = 0x00020000


def _call(ptr, index, restype, argtypes, *args):
    vtable = ctypes.cast(ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    func = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)(vtable[index])
    return func(ptr, *args)


def _release(ptr) -> None:
    if ptr is not None and getattr(ptr, "value", None):
        try:
            _call(ptr, 2, wintypes.ULONG, [])
        except Exception:
            pass


class WasapiLoopback:
    def __init__(self, output_rate: int = 8000):
        self.output_rate = int(output_rate)
        self._enumerator = ctypes.c_void_p()
        self._device = ctypes.c_void_p()
        self._audio = ctypes.c_void_p()
        self._capture = ctypes.c_void_p()
        self._mix = ctypes.c_void_p()
        self.channels = 2
        self.sample_rate = 48000
        self._factor = 1

    def start(self) -> None:
        if ole32.CoInitializeEx(None, 0) < 0:
            pass
        hr = ole32.CoCreateInstance(
            ctypes.byref(CLSID_MMDeviceEnumerator), None, CLSCTX_ALL,
            ctypes.byref(IID_IMMDeviceEnumerator), ctypes.byref(self._enumerator),
        )
        if hr < 0:
            raise OSError(f"CoCreateInstance failed: {hr & 0xffffffff:#x}")
        hr = _call(self._enumerator, 4, HRESULT,
                   [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)],
                   0, 0, ctypes.byref(self._device))
        if hr < 0:
            self.stop()
            raise OSError(f"GetDefaultAudioEndpoint failed: {hr & 0xffffffff:#x}")
        hr = _call(self._device, 3, HRESULT,
                   [ctypes.POINTER(GUID), wintypes.DWORD, ctypes.c_void_p,
                    ctypes.POINTER(ctypes.c_void_p)],
                   ctypes.byref(IID_IAudioClient), CLSCTX_ALL, None,
                   ctypes.byref(self._audio))
        if hr < 0:
            self.stop()
            raise OSError(f"Activate failed: {hr & 0xffffffff:#x}")
        hr = _call(self._audio, 8, HRESULT, [ctypes.POINTER(ctypes.c_void_p)],
                   ctypes.byref(self._mix))
        if hr < 0:
            self.stop()
            raise OSError(f"GetMixFormat failed: {hr & 0xffffffff:#x}")
        base = ctypes.cast(self._mix, ctypes.c_void_p).value
        values = ctypes.cast(self._mix, ctypes.POINTER(ctypes.c_ushort * 8)).contents
        self.channels = int(values[1]) or 2
        self.sample_rate = int(ctypes.cast(base + 4, ctypes.POINTER(ctypes.c_uint32)).contents.value) or 48000
        self._factor = max(1, round(self.sample_rate / self.output_rate))
        period = ctypes.c_longlong()
        minimum = ctypes.c_longlong()
        _call(self._audio, 9, HRESULT,
              [ctypes.POINTER(ctypes.c_longlong), ctypes.POINTER(ctypes.c_longlong)],
              ctypes.byref(period), ctypes.byref(minimum))
        hr = _call(self._audio, 3, HRESULT,
                   [ctypes.c_int, wintypes.DWORD, ctypes.c_longlong,
                    ctypes.c_longlong, ctypes.c_void_p, ctypes.c_void_p],
                   0, AUDCLNT_STREAMFLAGS_LOOPBACK, period.value, 0, self._mix, None)
        if hr < 0:
            self.stop()
            raise OSError(f"Initialize failed: {hr & 0xffffffff:#x}")
        hr = _call(self._audio, 14, HRESULT,
                   [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)],
                   ctypes.byref(IID_IAudioCaptureClient), ctypes.byref(self._capture))
        if hr < 0:
            self.stop()
            raise OSError(f"GetService failed: {hr & 0xffffffff:#x}")
        hr = _call(self._audio, 10, HRESULT, [])
        if hr < 0:
            self.stop()
            raise OSError(f"Start failed: {hr & 0xffffffff:#x}")

    def read(self) -> bytes:
        """Return downmixed mono int16 PCM at output_rate, or b''."""
        chunks = bytearray()
        for _ in range(8):
            size = ctypes.c_uint32()
            hr = _call(self._capture, 5, HRESULT, [ctypes.POINTER(ctypes.c_uint32)],
                       ctypes.byref(size))
            if hr < 0 or size.value == 0:
                break
            data = ctypes.POINTER(ctypes.c_ubyte)()
            frames = ctypes.c_uint32()
            flags = ctypes.c_uint32()
            device_pos = ctypes.c_uint64()
            qpc = ctypes.c_uint64()
            hr = _call(self._capture, 3, HRESULT,
                       [ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
                        ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32),
                        ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_uint64)],
                       ctypes.byref(data), ctypes.byref(frames), ctypes.byref(flags),
                       ctypes.byref(device_pos), ctypes.byref(qpc))
            if hr < 0:
                break
            silent = bool(flags.value & 0x2) or not data
            if not silent and frames.value:
                raw = ctypes.string_at(data, frames.value * self.channels * 4)
                floats = array.array("f")
                floats.frombytes(raw[:len(raw) // 4 * 4])
                for index in range(0, len(floats) // self.channels, self._factor):
                    offset = index * self.channels
                    sample = sum(floats[offset:offset + self.channels]) / self.channels
                    value = max(-1.0, min(1.0, sample))
                    chunks += int(value * 32767).to_bytes(2, "little", signed=True)
            _call(self._capture, 4, HRESULT, [ctypes.c_uint32], frames.value)
        return bytes(chunks)

    def stop(self) -> None:
        if getattr(self._audio, "value", None):
            try:
                _call(self._audio, 11, HRESULT, [])
            except Exception:
                pass
        _release(self._capture)
        _release(self._audio)
        _release(self._device)
        _release(self._enumerator)
        self._capture = ctypes.c_void_p()
        self._audio = ctypes.c_void_p()
        self._device = ctypes.c_void_p()
        self._enumerator = ctypes.c_void_p()
        try:
            ole32.CoUninitialize()
        except Exception:
            pass


def convert_float32_to_i16(raw: bytes, channels: int, factor: int) -> bytes:
    floats = array.array("f")
    floats.frombytes(raw[:len(raw) // 4 * 4])
    out = bytearray()
    for index in range(0, len(floats) // max(1, channels), max(1, factor)):
        offset = index * channels
        sample = sum(floats[offset:offset + channels]) / channels
        sample = max(-1.0, min(1.0, sample))
        out += int(sample * 32767).to_bytes(2, "little", signed=True)
    return bytes(out)
