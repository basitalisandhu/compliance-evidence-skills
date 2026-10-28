# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

### Fixed

- `aws-identity-and-logging-evidence`: `AWS-CT-LOGGING` checks `LatestDeliveryTime` against `--as-of` and configurable `max_delivery_age_hours` (default 24); stale deliveries contradict the row, while unknown or future delivery times are not assessable (#7).

## [0.7.0] - 2026-10-26

### Added

- `iso27001-soa-check`: `soa_check.py` lints an ISO/IEC 27001:2022 Statement of Applicability exported as CSV (comma, semicolon or tab; UTF-8 or UTF-16) or as a JSON list of rows. Columns are found by header name, with `--map FIELD=HEADER` overrides, and identifiers may be written A.5.1, 5.1 or A 5.1. It reports, with the line of each row: Annex A 2022 controls missing from the SoA (per theme), unknown, duplicate and 2013-style identifiers (three-part ids and clauses 9 to 18, with a note that the 2022 transition is needed), applicability that is not a clear yes or no, exclusions and inclusions without a justification, included controls with no implementation status or a status that contradicts the decision, implemented controls with no evidence reference, evidence paths that do not exist under `--evidence-root`, missing owners, and reviews older than `--max-age-days`. With `--risk-register` it lists risks treated by a control the SoA excludes and, as warnings, included controls that no risk or stated requirement refers to. A table counts Organisational, People, Physical and Technological controls separately, and rows with other identifiers are kept out of it. Ships the 93 identifiers only, no ISO titles or text. Markdown or JSON, `--out`, `--redact`, `--fail-on`. Exit 0 nothing at or above `--fail-on`, 1 findings, 2 bad input. 12 tests with a synthetic company's SoA, risk register and evidence folder. Dispatcher subcommand `soa`; the container check in CI runs its `--help`.

### Changed

- Version 0.7.0 in `pyproject.toml`, `plugin.json`, `marketplace.json`, the dispatcher, the pack builder's tool string and the README container examples; the READMEs, plugin and marketplace descriptions list eleven skills and a sample output section for the new one.

## [0.6.0] - 2026-10-20

### Added

- `evidence-collection-plan`: `collection_plan.py` answers "what evidence do we need to collect for each control, from which system, how, how often and by when?" before collection starts, as an auditor-style PBC request list, and on later runs shows which requests an evidence pack already meets. Input is a scope file (framework `iso27001-2022` or `soc2`, audit period, in-scope control identifiers, system inventory with an owner role each), an optional extra or overriding catalogue (`--catalogue`) and an optional pack `manifest.json` (`--manifest`, matched to requests by `request_id` or filename pattern). The bundled catalogue (`references/request-catalogue.json`) holds 33 starter requests for common ISO 27001:2022 Annex A and SOC 2 identifiers, each with the system, a read-only way to obtain it, frequency (`once-per-period`, `quarterly`, `monthly`, `population-sample`), freshness window, default owner role and the skill that consumes the file; control identifiers carry short paraphrases only. Quarterly and monthly requests get one row per slot with a due date; each row is `met`, `stale`, `missing` or `overdue` on `--as-of` and a control takes the worst status of its rows. Requests for a system outside the inventory are listed as not applicable unless the system is added, and controls no request covers are listed as gaps. Markdown, JSON or CSV (the PBC spreadsheet), `--out`, `--redact`. Exit 0 every control covered and nothing stale or overdue, 1 otherwise, 2 bad input. 34 tests with synthetic scope, manifest and catalogue files and a golden report. Motivated by getprobo/probo#1981, getprobo/probo#1728 and trycompai/comp#3541.
- Dispatcher subcommand `plan`; the container check in CI runs its `--help`.

### Changed

- Version 0.6.0 in `pyproject.toml`, `plugin.json`, `marketplace.json`, the dispatcher, the pack builder's tool string and the README container examples; the READMEs, plugin and marketplace descriptions list ten skills and a sample output section for the new one.

## [0.5.0] - 2026-10-18

### Added

- `control-map-from-exports`: the report lists every `evidence` pattern in the map that matched no pack file (`unmatched_patterns` in the JSON, a "Map patterns that matched no pack file" section in Markdown), so a misspelt pattern no longer looks the same as a missing export (closes #5).
- `essential-eight-evidence-map`: `references/example-e8-map.csv`, a three-row example to copy from, and a "try it" run on the repository's fixture exports.
- `security-questionnaire-drafter`: reads semicolon and tab separated questionnaires, Excel "Unicode Text" (UTF-16) and Windows-1252 CSV, as spreadsheet programs save them; a fixture questionnaire and policy folder for a first run.
- Every SKILL.md has a "try it" command on the repository's fixtures and says where the script is when the skill folder is copied without the plugin system (closes #18).

### Fixed

- `maester-control-map`: the example map and the docs assumed an `MFA` tag and `MS.AAD.3.*` test ids. Checked against the Maester repository (2.3.0 and the 3.0 previews): Maester has never had an `MFA` tag, its CISA SCuBA tests are `CISA.MS.AAD.*`, and Maester 3 no longer writes its old tags into result rows. The example map now matches by test id only (`MT.1006` for MFA on administrators, `CIS.M365.1.1.*`, `EIDSCA.*`, `CISA.MS.AAD.3.*`), the fixture results use real ids and tags, and a test keeps the example to real id patterns.
- `security-questionnaire-drafter`: a manifest entry pointing outside the pack (`..` or an absolute path) was read and could be cited; it is now skipped with a note. In a plain evidence folder, hidden files such as `.DS_Store` and `.git` contents were cited as evidence. A repeated question id could be renamed to an id the file already used.
- `essential-eight-evidence-map`: requirement ids in lower case, `./` and `\` in evidence paths made rows fail as unknown or not in the manifest; they are normalised. A manifest path outside the pack now stops the run, a JSON map value that is not a path or list of paths exits 2 instead of a traceback, a CSV row without evidence names its line, and with `--max-age-days` a file collected after `--as-of` is not assessable.
- `auditor-narrative-drafter`: a control map entry without `id`, `state` or `topic`, or a citation without `file` or `field`, crashed with a traceback; an empty map drafted nothing silently; an unwritable `--out` crashed. All exit 2 now. Control ids are matched without regard to case and a repeated `--control` is drafted once.

### Changed

- `control-map-from-exports` and `essential-eight-evidence-map` descriptions say they are not an access review pack or a tenant baseline, so prompts for `access-review-pack` and `entra-posture-review` do not land here.
- Version 0.5.0 in the marketplace, plugin manifest, `pyproject.toml`, the CLI, the evidence pack tool string and the container examples.

## [0.4.0] - 2026-10-16

### Added

- `vendor-attestation-digest`: `vendor_attestations.py` reads a register of vendor SOC 2 Type 1 and Type 2 reports, ISO 27001 certificates, bridge letters, penetration test summaries and other attestations (CSV or JSON, one row per document with the page each field came from) and a vendor list (services used, criticality, owner), optionally hashes each source document found in `--docs`, and flags `no-attestation`, `expired`, `expiring`, `coverage-gap` (SOC 2 period ended longer ago than the bridge window with no bridge letter), `bridge-letter-expired`, `type1-only` (high criticality), `opinion-not-unqualified`, `exceptions-noted`, `scope-mismatch`, `cuecs-not-reviewed`, `missing-field` (never guessed) and `source-unverified`. Report age, bridge window and expiry warning are options with the skill's defaults (12 months, 3 months, 60 days); `--as-of` is required. Digest per vendor ordered by criticality with owner actions; Markdown, JSON, `--csv` (one row per finding), `--out`, `--redact`. Exit 0 no findings, 1 findings, 2 bad input. 17 tests with synthetic vendors and documents. It does not read PDFs.
- `maester-control-map`: `maester_map.py` reads a Maester results file (`Invoke-Maester -OutputJsonFile`; a missing test Id is taken from Name) and a mapping CSV (exact test id, id prefix with `*`, or `tag:<Tag>`, to ISO 27001 or SOC 2 identifiers checked against the bundled identifier lists or `--identifiers`), and reports per control `supported` (a mapped test Passed, none Failed or Investigate), `contradicted` (a mapped test Failed) or `not assessable` (only Skipped, NotRun or Error, or Investigate as "needs human review"), with a citation per test. Also writes the test list with `iso27001` and `soc2` columns (`--annotated-csv`), lists unmapped tests and map rows that matched nothing, reports the file's SHA-256 and ExecutedAt, and warns when the run is older than `--max-age-days` (default 30) or the counts disagree. Ships `references/example-map.csv`, five rows labelled as an example to review. Markdown, JSON, `--out`, `--redact` (TenantName, TenantId, e-mail addresses). Exit 0 nothing contradicted and not stale, 1 otherwise, 2 bad input. 21 tests with a synthetic results file (tenant contoso-example) and malformed variants.
- Dispatcher subcommands `vendors` and `maester`; the container check in CI runs their `--help`, and `tests/test_cli.py` runs `maester` through the dispatcher.

### Changed

- Version 0.4.0 in `pyproject.toml`, `plugin.json`, `marketplace.json`, the dispatcher, the pack builder's tool string and the README container examples; the READMEs, plugin and marketplace descriptions list nine skills and a sample output section for the two new ones.

## [0.3.0] - 2026-10-09

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
