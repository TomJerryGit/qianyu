# Code signing policy

QianYu does **not** use SignPath Foundation or any third-party free signing
service.

## Current status

- Windows release artifacts are **unsigned**.
- The project does not claim a verified publisher or a signed build.
- Signing is optional and is not a prerequisite for building, releasing,
  updating or distributing QianYu.

## Integrity and verification

- Release assets are built by the public GitHub Actions workflow from this
  repository.
- Every release publishes `SHA256SUMS.txt`.
- The source tag and workflow logs are public.
- Optional update manifests can be Ed25519-signed independently of
  Authenticode.

See [docs/unsigned_distribution.md](docs/unsigned_distribution.md).

## What would be signed if a project-owned certificate is added

- `QianYu.exe`
- `QianYu-<version>-setup.exe`
- optionally the portable ZIP

Only artifacts produced by the public CI workflow are eligible.

## Team roles

- Author/Committer: `@TomJerryGit`
- Reviewer: `@TomJerryGit`
- Release approver: `@TomJerryGit`

For a single-maintainer project, roles may be held by the same person.
Pull requests from non-committers require review before merge.

## Release approval

Any future signing step requires explicit release approval by the project
maintainer. Unsigned releases must be labeled as unsigned.

## Privacy

See [PRIVACY.md](PRIVACY.md).
