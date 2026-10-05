# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

- Reject citations attributed to a control that does not map that evidence.

## [0.1.1] - 2026-10-04

### Fixed

- Quoted SKILL.md descriptions that contained a colon so the frontmatter parses under strict YAML readers such as the skills CLI; the validator now fails on unquoted scalars with ': ' or ' #'.

## [0.1.0] - 2026-10-04

### Added

- Plugin marketplace `compliance-evidence-skills` with one plugin, `compliance-evidence`.
- `evidence-pack-builder`: `evidence_pack.py` with `sidecar` (skeleton provenance file), `build` (copy or reference mode, SHA-256 per file, collector, collection time, source system and command from the sidecar, `manifest.json` and `MANIFEST.md`, provenance gaps, manifest hash printed), `verify` (modified, missing and unexpected files, optional manifest hash check) and `expire` (age per file, per-source limits).
- `control-map-from-exports`: `control_map.py` applies a YAML or JSON mapping (field paths with list fan-out, `where` filters, value and count conditions, `any_of`, `absent_when`, `on_fail`) to a pack after re-checking each file's hash, and reports per control `supported`, `contradicted` or `not assessable` with citations and gaps, plus pack files no check read. Ships a starter map for GitHub, AWS and Microsoft 365 exports and identifier lists for ISO/IEC 27001:2022 Annex A and SOC 2 with paraphrases only.
- `github-change-control-evidence`: `github_evidence.py`, 14 evidence rows from `gh api` and `gh pr list` exports (branch protection or rulesets, required reviews, admin enforcement, status checks, force pushes, independent approval of every merged pull request in the period, CODEOWNERS, signed commits, Dependabot alerts and security updates, secret scanning and push protection, open alert age). 403 and plan-limit responses are `not assessable`.
- `aws-identity-and-logging-evidence`: `aws_evidence.py`, 12 evidence rows from saved `aws` CLI output and stderr (CloudTrail coverage, logging and validation, root MFA and keys, console MFA, key age, password policy, GuardDuty and Config per region, account S3 public access block, AWS Backup plans).
- `auditor-narrative-drafter`: `narrative.py` drafts narratives with `[evidence: file#field]` citations from a control map; `narrative_lint.py` rejects uncited outcome claims, untraceable citations, state mismatches, unknown controls, certainty wording, listed copied phrases in long lines, and a missing disclaimer.
- `--json` and `--redact` on every script; shared `_evidence.py` and `_miniyaml.py` helpers copied into each skill with a drift test.
- `scripts/cli.py` dispatcher (`compliance-evidence <subcommand>`), a two-stage `Dockerfile` on a digest-pinned base image, and `publish-github-packages.yml` that tests, checks versions against the tag, builds, pushes, attests and signs the image and creates the release with an SBOM.
- Offline pytest suite with hand-written fixtures (including a pack with a planted modified file and a narrative with planted problems), `scripts/validate_plugins.py`, ruff configuration, a CI workflow with read-only permissions and SHA-pinned actions, and Dependabot for actions and the base image.
