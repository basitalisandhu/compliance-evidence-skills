# Security policy

This repository ships skills and scripts that run inside people's Claude Code sessions and that handle compliance evidence: exports from GitHub, AWS and Microsoft 365 that can name people, accounts and security settings. The scripts read the files you point them at and write only where you ask; nothing here makes a network call, calls an API, reads environment variables or reports usage anywhere.

## Supported versions

Only the latest release on `main` is supported. Pin a tag if you need stability, and update when a fix is announced in [CHANGELOG.md](CHANGELOG.md).

## Reporting a vulnerability

Please do not open a public issue for a security problem.

1. Use GitHub's private vulnerability reporting on this repository ("Security" tab, "Report a vulnerability").
2. If that is unavailable, open an issue titled "Security contact request" with no details, and the maintainer will reply with a private channel.

Include what you found, how to reproduce it, and what you think the impact is. You will get an acknowledgement within 5 working days and a fix or a mitigation plan within 30 days for confirmed issues.

Do not include real evidence in a report: no account ids, user names, e-mail addresses, tokens or exports. Reproduce with the fixtures in `tests/fixtures/`, which use `example.com` users, AWS account `123456789012` and ids such as `00000000-0000-0000-0000-0000000000c1`.

## What counts

- A result marked `supported` without a cited evidence file and field, or a missing, empty, denied (403) or hash-mismatched file that produces `supported`.
- `verify` reporting a pack as intact after a file inside it, or `manifest.json` given with `--manifest-sha256`, was changed.
- A script that can be made to execute untrusted input, write outside the paths given on its command line, follow a symbolic link out of the export folder into a pack, open a network connection, or call any API.
- `--redact` output that still contains an e-mail address, IAM user name, GitHub login or ARN principal name present in the input.
- A skill that instructs Claude to change a repository, an account or a tenant without asking for confirmation of a specific command, or lists an export command that writes.
- Control text from ISO/IEC 27001, ISO/IEC 27002 or the AICPA criteria committed to the repository (report it so it can be removed).
- Instructions hidden in any file of this repository that address the model rather than the reader.

Missing checks or controls are welcome as ordinary issues or pull requests; they are coverage improvements rather than vulnerabilities.

## What this repository does and does not do

- No telemetry, no network access and no subprocesses from skill scripts. The container dispatcher (`scripts/cli.py`) starts the chosen skill script as a child process and nothing else.
- `gh`, `aws` and `mgc` appear only in skill instructions, as read-only commands run by the user's own session with the user's own credentials.
- Results are preparation for a human assessor, never an audit opinion or attestation.
- Skill text tells Claude to treat all exported data as untrusted content, never as instructions.
