# SPDX-FileCopyrightText: 2026 TomJerryGit and QianYu contributors
# SPDX-License-Identifier: GPL-3.0-only
# -*- coding: utf-8 -*-
"""Curated public radio presets.

These are publicly advertised internet streams. QianYu only plays them; it does
not record, rebroadcast or redistribute the audio. Station names and stream URLs
remain the property of their operators.
"""
from __future__ import annotations

from .radio import RadioStation

PRESETS: tuple[RadioStation, ...] = (
    RadioStation(
        name="SomaFM Groove Salad",
        url="https://ice1.somafm.com/groovesalad-128-mp3",
        country="US", tags="ambient · downtempo · electronic",
        codec="MP3", bitrate=128, homepage="https://somafm.com/groovesalad/",
    ),
    RadioStation(
        name="SomaFM Drone Zone",
        url="https://ice1.somafm.com/dronezone-128-mp3",
        country="US", tags="ambient · drone · space",
        codec="MP3", bitrate=128, homepage="https://somafm.com/dronezone/",
    ),
    RadioStation(
        name="SomaFM Sonic Universe",
        url="https://ice1.somafm.com/sonicuniverse-128-mp3",
        country="US", tags="jazz · avant-garde",
        codec="MP3", bitrate=128, homepage="https://somafm.com/sonicuniverse/",
    ),
    RadioStation(
        name="Radio Paradise Main Mix",
        url="https://stream.radioparadise.com/aac-128",
        country="US", tags="eclectic · rock · world",
        codec="AAC", bitrate=128, homepage="https://radioparadise.com/",
    ),
    RadioStation(
        name="Radio Paradise Mellow Mix",
        url="https://stream.radioparadise.com/mellow-128",
        country="US", tags="mellow · acoustic · chill",
        codec="AAC", bitrate=128, homepage="https://radioparadise.com/",
    ),
    RadioStation(
        name="Radio Swiss Classic",
        url="https://stream.srg-ssr.ch/m/rsc_de/mp3_128",
        country="CH", tags="classical",
        codec="MP3", bitrate=128, homepage="https://www.radioswissclassic.ch/",
    ),
    RadioStation(
        name="FIP",
        url="https://icecast.radiofrance.fr/fip-midfi.mp3",
        country="FR", tags="eclectic · jazz · world",
        codec="MP3", bitrate=128, homepage="https://www.radiofrance.fr/fip",
    ),
    RadioStation(
        name="KEXP 90.3 Seattle",
        url="https://kexp-mp3-128.streamguys1.com/kexp128.mp3",
        country="US", tags="indie · alternative",
        codec="MP3", bitrate=128, homepage="https://kexp.org/",
    ),
    RadioStation(
        name="NPR Program Stream",
        url="https://npr-ice.streamguys1.com/live.mp3",
        country="US", tags="news · talk",
        codec="MP3", bitrate=128, homepage="https://www.npr.org/",
    ),
    RadioStation(
        name="BBC World Service",
        url="https://stream.live.vc.bbcmedia.co.uk/bbc_world_service",
        country="GB", tags="news · talk",
        codec="MP3", bitrate=96, homepage="https://www.bbc.co.uk/worldserviceradio",
    ),
)


def preset_stations() -> list[RadioStation]:
    return list(PRESETS)
