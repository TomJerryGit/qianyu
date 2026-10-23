# Source offer

QianYu is licensed under GPL-3.0-only.

- QianYu source: https://github.com/TomJerryGit/qianyu
- This release's source tag: https://github.com/TomJerryGit/qianyu/tree/v0.9.0
- Build scripts: `packaging/` in the source repository

## Bundled libmpv / FFmpeg

The Windows build bundles a libmpv DLL built from the mpv winbuild project:

- https://github.com/shinchiro/mpv-winbuild-cmake
- Build version used by CI: mpv-dev-x86_64-20261018-git-01e2533f31
- Corresponding source: the upstream mpv, FFmpeg and dependency repositories,
  plus the build scripts in shinchiro/mpv-winbuild-cmake.

The exact libmpv DLL and its SHA-256 are published on the QianYu release page.
If you need a copy of the corresponding source for GPL compliance, open an
issue at https://github.com/TomJerryGit/qianyu/issues with the release tag.

## QianYu source availability

The complete corresponding source for the GPL-covered QianYu code is the
public repository at the tag above. No registration is required.
