# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

### Added

- Reject citations attributed to a control that does not map that evidence.

## [0.2.0] - 2026-10-05

### Added

- `security-questionnaire-drafter`: `questionnaire.py` drafts answers to a security questionnaire (CSV, or Markdown as a table, a numbered list or question lines) from an evidence pack (hashes checked; a file that fails is never cited), a policy folder split at headings, and optionally a control map. Each question is `supported` with quoted, cited policy sections and evidence files, `contradicted` when it names a control the map marks contradicted, or `not assessable` with a request to route it to an owner. Never writes "Yes" or "No". Markdown, JSON, `--csv` with an owner column, `--out`, `--redact`. 11 tests with synthetic inputs.
- `essential-eight-evidence-map`: `e8_map.py` maps an evidence pack to the ASD Essential Eight Maturity Model (November 2023) through a mapping file (CSV or JSON, globs allowed), checks each mapped file against the manifest (present, SHA-256, optional age limit), gives each of the 153 requirements a state and each strategy the maturity level it can claim, and lists unmapped files as candidates per strategy. The bundled requirement list reproduces the model's statements under CC BY 4.0 with repository ids such as `PA-ML1-01`. Markdown, JSON, `--csv`, `--out`, `--redact`. 12 tests with synthetic packs.
- Dispatcher subcommands `questionnaire` and `e8`; the container check in CI runs their `--help`.

### Changed

- Version 0.2.0 in `pyproject.toml`, `plugin.json`, `marketplace.json`, the dispatcher, the pack builder's tool string and the README container examples; the READMEs list the new skills and the searches they answer; helper-copy wording no longer says "all five".

## [0.1.2] - 2026-10-05

### Changed

- Rewrote all five skill descriptions to 484 to 536 characters (from 765 to 840): each starts with a verb, states the goal before the mechanism, carries one quoted phrase a user would type, a "Use when ..." sentence and a "Not for ..." boundary, and stays double-quoted.
- `aws-identity-and-logging-evidence` states its boundary with `aws-account-audit` in aws-security-skills: the audit ranks risk, this skill turns the same saved CLI output into evidence rows.
- Tests open text files with `encoding="utf-8"` (the scripts already did), and CI runs tests, ruff and the `--help` check on `windows-latest` as well as Ubuntu and macOS. A `.gitattributes` keeps `tests/fixtures/` byte-exact so the committed SHA-256 manifests verify on a Windows checkout.
- The plugin and root READMEs mention SOC 2 Type II evidence, readiness assessments and Vanta or Drata exports, with what the skills do and do not read.
- `scripts/validate_plugins.py` now fails when a description is over 600 characters, is not double-quoted, or lacks "Use " or "Not for", and when a SKILL.md has no `## Limits` section; `tests/test_skill_frontmatter.py` covers each rule.
- Version 0.1.2 in `pyproject.toml`, `plugin.json`, `marketplace.json`, the dispatcher, the evidence pack tool string and the README container examples.

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
