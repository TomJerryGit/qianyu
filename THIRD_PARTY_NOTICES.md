# Third-party notices

QianYu is licensed under GPL-3.0-only. It uses open-source components:

| Component | License | Use |
|---|---|---|
| PySide6 / Qt 6 | LGPL-3.0 / GPL-3.0 options | UI |
| libmpv / mpv | LGPL-2.1-or-later (build-dependent) | playback |
| FFmpeg | LGPL/GPL depending on build | decoding |
| mutagen | GPL-2.0-or-later | tags |
| python-mpv | MIT | libmpv binding |
| Pillow | HPND | cover color extraction (development) |
| PyInstaller | GPL-2.0-or-later with bootloader exception | packaging |
| Inno Setup | Inno Setup License | installer |

Before a public release, verify the exact license of the bundled libmpv and
FFmpeg builds and include their license texts and source offers where
required.

## Online services and content

QianYu also communicates with public services at the user's request:

| Service | Data | Notes |
|---|---|---|
| Radio Browser | radio station directory | community data; streams belong to stations |
| Apple iTunes Search API | podcast search results | “Powered by iTunes” attribution |
| Podcast RSS feeds | episode metadata/audio URLs | audio belongs to publishers |
| MusicBrainz | music metadata | attribution required |
| Deezer Search API | artist photos | display/cache only; rights remain with owners |
| LRCLIB | lyrics | lyrics copyright belongs to rights holders |
| Cover Art Archive | cover art | artwork copyright belongs to rights holders |
| ListenBrainz | optional scrobble records | user token, default off |

QianYu does not host or redistribute third-party audio, lyrics or artwork.
See [docs/online_compliance.md](docs/online_compliance.md).
