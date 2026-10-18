# Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io),
certificate by [SignPath Foundation](https://signpath.org).

This policy applies to Windows release artifacts published from the
QianYu repository.

## Team roles

- Authors/Committers: `@TomJerryGit`
- Reviewers: `@TomJerryGit`
- Approvers: `@TomJerryGit`

For a single-maintainer project all roles may be held by the same person.
Pull requests from non-committers still require review before merge.

## What is signed

- `QianYu.exe`
- `QianYu-<version>-setup.exe`

Only artifacts built by the public CI workflow from this repository are
eligible for signing.

## Privacy

See [PRIVACY.md](PRIVACY.md).

## Release approval

Every signing request requires manual approval by an Approver.
