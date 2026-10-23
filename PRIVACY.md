# Privacy policy

QianYu is a local-first Windows music and video player. It does not require
an account and does not include telemetry or analytics.

## Data stored locally

- Library database, playlists, settings, lyrics mappings and offsets.
- Cached cover images and downloaded lyrics.
- Logs written next to the application data directory.

These files stay on the user's computer unless the user copies them.

## Network requests

QianYu only contacts external services when the user explicitly invokes an
online action:

- **MusicBrainz** — title/artist query for metadata completion.
- **LRCLIB** — title/artist query for online lyrics.
- **Cover Art Archive** — release ID query for online cover art.
- **Radio Browser** — radio station searches.
- **iTunes Search** — podcast searches.
- **Podcast RSS feeds** — the feed URL is fetched to list episodes.
- **ListenBrainz** — optional scrobbling when enabled by the user. A user token
  is stored locally in the settings file and sent only to ListenBrainz.
- **Navidrome / Subsonic server** — only when the user configures a remote
  library. The server address, username and password are stored locally; the
  password is used to derive a short-lived Subsonic token and is never sent in
  clear text by API requests. Remote audio is streamed from that server.

No audio files and no local library contents are uploaded by these
requests. The services receive the query text and normal HTTP metadata
(IP address, user agent). Podcast downloads are stored locally and are not
uploaded anywhere.

If the user does not use the online actions, QianYu can be used fully
offline.

## Third-party components

QianYu bundles or depends on PySide6/Qt, libmpv, FFmpeg, mutagen and other
open-source components. Their privacy behavior is described by their own
projects. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Contact

1265338136@qq.com
