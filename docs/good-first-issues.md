# Good first issues

Small, well-specified pieces of work for a first contribution. Each is self-contained, has a test to add, and needs no GitHub organisation, AWS account, Microsoft 365 tenant, credentials or network access. Read [CONTRIBUTING.md](../CONTRIBUTING.md) first: three result states only, no framework text, standard library only, tests with every change, fixtures use `example.com`, account `123456789012` and zero GUIDs, plain language without em-dashes. If you change `_evidence.py`, copy it to all five skills.

To claim one, open an issue with the title below (or comment on the existing one) and say you are working on it. Run `python3 -m pytest -q`, `python3 -m ruff check .` and `python3 scripts/validate_plugins.py` before opening the pull request.

## 1. evidence-pack-builder: period coverage check

**Labels:** good first issue, evidence-pack-builder, python

**Context.** The sidecar records the audit `period`, and each file has a collection time. A file collected before the period ends cannot show the state at the end of the period.

**Acceptance criteria.**
- New subcommand option `expire --period-end-required`: files collected before `period.end` are reported with status `before-period-end`.
- A fixture sidecar with a period and a test for a file before and after the end date.

## 2. control-map-from-exports: report checks whose evidence glob matched nothing

**Labels:** good first issue, control-map-from-exports, python

**Context.** A check whose `evidence` pattern matches no pack file is `not assessable` with the gap "not in the pack". A typo in the map looks the same as a missing export.

**Acceptance criteria.**
- The report gains `unmatched_patterns`: every `evidence` pattern in the map that matched no file in the manifest.
- The Markdown output lists them under a heading; a test with a misspelt pattern.

## 3. github-change-control-evidence: dismissal of stale reviews

**Labels:** good first issue, github-change-control-evidence, python

**Context.** `branch-protection.json` carries `required_pull_request_reviews.dismiss_stale_reviews`. Without it, a pull request approved before later pushes can merge on the old approval.

**Acceptance criteria.**
- New row `GH-DISMISS-STALE` (A.8.32, CC8.1): `supported` when true, `contradicted` when false, `not assessable` without branch protection; rulesets read `dismiss_stale_reviews_on_push`.
- Fixture changes and tests for all three states; the docstring and `SKILL.md` list the row.

## 4. aws-identity-and-logging-evidence: CloudTrail delivery freshness

**Labels:** good first issue, aws-identity-and-logging-evidence, python

**Context.** `get-trail-status` returns `LatestDeliveryTime`. A trail can say `IsLogging: true` while deliveries stopped days ago.

**Acceptance criteria.**
- Config key `max_delivery_age_hours` (default 24); `AWS-CT-LOGGING` becomes `contradicted` when the latest delivery is older than the limit at `--as-of`, citing `LatestDeliveryTime`.
- A fixture status file with an old delivery time and a test.

## 5. auditor-narrative-drafter: per-control citation check

**Labels:** good first issue, auditor-narrative-drafter, python

**Context.** `narrative_lint.py` accepts a citation that exists anywhere in the control map, even under the wrong control heading.

**Acceptance criteria.**
- New rule `WRONG-CONTROL-CITATION`: a citation under `## <identifier>` that the control map does not cite for that identifier.
- A test with a citation moved to another control, and the existing drafts must still pass.

## 6. control-map-from-exports: starter map entries for Microsoft 365 audit log retention

**Labels:** good first issue, control-map-from-exports, documentation

**Context.** The starter map has no Microsoft 365 entry for A.8.15 or CC7.2. A read-only export of the unified audit log setting is available from Exchange Online PowerShell (`Get-AdminAuditLogConfig`, saved with `ConvertTo-Json`).

**Acceptance criteria.**
- A starter map check reading `m365/admin-audit-log-config.json` field `UnifiedAuditLogIngestionEnabled`, mapped to A.8.15 and CC7.2, with the export command and the read role (View-Only Audit Logs) added to the `control-map-from-exports` skill.
- A fixture file and a test; identifiers and paraphrases only.
