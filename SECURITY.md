# Security policy

## Supported versions

QianYu 0.9.x receives security fixes on the current release branch.

## Reporting a vulnerability

Please report security issues privately to **1265338136@qq.com** with:

- affected version/commit;
- reproduction steps;
- impact assessment;
- whether credentials or user data may be exposed.

Do not open a public GitHub issue before a fix is available.  
Please do not include live passwords, tokens or personal media in reports.

## Scope

In scope:

- QianYu desktop application and installer;
- credential storage (Windows DPAPI);
- remote media-library handling;
- online radio/podcast/cover/lyrics data handling;
- update manifest verification.

Out of scope:

- third-party stations, podcasts, servers or platforms;
- issues requiring a compromised local administrator account;
- deliberate misuse of DRM or platform terms.

## Security baseline

- Online features are opt-in where they send user data.
- Credentials are stored with Windows DPAPI, not plaintext.
- Remote URLs are restricted to http/https; response sizes are bounded.
- Release assets publish SHA-256 checksums.
- Update manifests can be Ed25519-signed independently of Authenticode.
- QianYu does not use SignPath; unsigned builds are labeled as unsigned.

See [docs/security.md](docs/security.md) for the threat model.
