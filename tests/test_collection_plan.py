"""Tests for evidence-collection-plan/scripts/collection_plan.py. Every organisation, owner and file is synthetic
(tests/fixtures/collection-plan and scopes built here); nothing connects to a system."""

from __future__ import annotations

import csv
import io
import json
import re

import pytest
from conftest import FIXTURES, SKILLS, load_script, run_json, run_main

mod = load_script("evidence-collection-plan", "collection_plan.py")
FX = FIXTURES / "collection-plan"
ISO = FX / "scope-iso27001.json"
SOC2 = FX / "scope-soc2.json"
MANIFEST = FX / "manifest.json"
ASOF = "2026-11-15"
BASE = ["--scope", str(ISO), "--manifest", str(MANIFEST), "--as-of", ASOF]
CATALOGUE = SKILLS / "evidence-collection-plan" / "references" / "request-catalogue.json"


def rows(rep, rid):
    return [r for r in rep["requests"] if r["request_id"] == rid]


def control(rep, cid):
    return next(c for c in rep["controls"] if c["id"] == cid)


def scope_file(tmp_path, **changes):
    doc = {
        "organisation": "Example Pty Ltd",
        "framework": "iso27001-2022",
        "period": {"start": "2026-07-01", "end": "2026-12-31"},
        "controls": ["A.8.15"],
        "systems": [{"kind": "aws", "owner": "Cloud platform lead"}],
    }
    doc.update(changes)
    p = tmp_path / "scope.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def manifest_file(tmp_path, entries):
    p = tmp_path / "manifest.json"
    files = [{"path": path, "collected_at": day + "T09:30:00Z"} for path, day in entries]
    p.write_text(json.dumps({"schema": "compliance-evidence-pack/1", "files": files}), encoding="utf-8")
    return p


def test_requests_are_selected_by_in_scope_control_ids():
    rc, rep = run_json(mod, [*BASE, "--json"])
    assert rc == 1
    selected = {r["request_id"] for r in rep["requests"]} | {n["request_id"] for n in rep["not_applicable"]}
    assert {"IAM-01", "LOG-01", "BKP-01", "HR-02", "CHG-01", "POL-01"} <= selected
    assert not {"INC-01", "VND-01", "END-01"} & selected  # their controls are not in this scope
    assert rep["summary"]["controls"] == 8


def test_systems_missing_from_the_inventory_are_listed_not_dropped():
    _, rep = run_json(mod, [*BASE, "--json"])
    na = {n["request_id"]: n for n in rep["not_applicable"]}
    assert set(na) == {"CHG-03", "GWS-01", "GWS-02"}
    assert na["GWS-02"]["system"] == "google-workspace" and na["GWS-02"]["controls"] == ["A.8.15"]
    assert not {"CHG-03", "GWS-01", "GWS-02"} & {r["request_id"] for r in rep["requests"]}
    _, md, _ = run_main(mod, BASE)
    assert "### Not applicable unless the system is added" in md and "GWS-02" in md


def test_quarterly_requests_get_one_row_per_quarter_and_others_one_row():
    _, rep = run_json(mod, [*BASE, "--json"])
    q = rows(rep, "IAM-01")
    assert [(r["slot"], r["slot_start"], r["due"]) for r in q] == [("Q1", "2026-07-01", "2026-09-30"), ("Q2", "2026-10-01", "2026-12-31")]
    assert len(rows(rep, "LOG-01")) == 1 and rows(rep, "LOG-01")[0]["due"] == "2026-12-31"
    _, soc = run_json(mod, ["--scope", str(SOC2), "--as-of", "2026-10-20", "--json"])
    assert [r["due"] for r in rows(soc, "IAM-01")] == ["2026-03-31", "2026-06-30", "2026-09-30", "2026-12-31"]


def test_monthly_rows_follow_the_period_and_clamp_the_last_one(tmp_path):
    scope = scope_file(tmp_path, controls=["A.8.16"], systems=[{"kind": "ticketing", "owner": "Security lead"}],
                       period={"start": "2026-01-31", "end": "2026-04-30"})  # fmt: skip
    _, rep = run_json(mod, ["--scope", str(scope), "--as-of", "2026-03-15", "--json"])
    alr = rows(rep, "ALR-01")
    assert [(r["slot"], r["due"]) for r in alr] == [("M01", "2026-02-27"), ("M02", "2026-03-30"), ("M03", "2026-04-29"), ("M04", "2026-04-30")]
    assert [r["status"] for r in alr] == ["overdue", "missing", "missing", "missing"]  # no manifest: only the row already past due is overdue


def test_met_stale_missing_and_overdue_with_a_pinned_date():
    _, rep = run_json(mod, [*BASE, "--json"])
    by = {(r["request_id"], r["slot"]): r for r in rep["requests"]}
    assert by["IAM-01", "Q1"]["status"] == "met" and by["IAM-01", "Q1"]["evidence_file"] == "aws/credential-report.csv"
    assert by["HR-02", "period"]["status"] == "stale" and "133 days" in by["HR-02", "period"]["note"]
    assert by["IAM-01", "Q2"]["status"] == "missing" and "before this slot" in by["IAM-01", "Q2"]["note"]
    assert by["ACC-01", "Q1"]["status"] == "overdue" and by["ACC-01", "Q2"]["status"] == "missing"
    assert by["POL-01", "period"]["status"] == "met"
    assert by["ACC-02", "population"]["status"] == "met"
    # the same files an earlier day: the training report is still fresh and nothing is overdue yet
    _, early = run_json(mod, ["--scope", str(ISO), "--manifest", str(MANIFEST), "--as-of", "2026-09-01", "--json"])
    assert {r["status"] for r in early["requests"]} <= {"met", "missing"}


def test_future_dated_and_out_of_slot_files_do_not_count(tmp_path):
    entries = [("aws/cloudtrail-trails.json", "2026-06-30"), ("aws/cloudtrail-status-org-trail.json", "2026-12-20")]
    scope = scope_file(tmp_path)
    _, rep = run_json(mod, ["--scope", str(scope), "--manifest", str(manifest_file(tmp_path, entries)), "--as-of", "2026-11-15", "--json"])
    (row,) = rows(rep, "LOG-01")
    assert row["status"] == "missing" and "before this slot" in row["note"]  # 30 June is before the period
    _, late = run_json(mod, ["--scope", str(scope), "--manifest", str(manifest_file(tmp_path, entries)), "--as-of", "2027-01-10", "--json"])
    (row,) = rows(late, "LOG-01")
    assert row["status"] == "met" and row["evidence_file"] == "aws/cloudtrail-status-org-trail.json"
    _, after = run_json(mod, ["--scope", str(scope), "--manifest", str(manifest_file(tmp_path, [("aws/cloudtrail-trails.json", "2027-01-05")])),
                              "--as-of", "2027-01-10", "--json"])  # fmt: skip
    (row,) = rows(after, "LOG-01")
    assert row["status"] == "overdue" and "after the due date" in row["note"]


def test_request_id_in_the_manifest_matches_without_a_filename_pattern(tmp_path):
    scope = scope_file(tmp_path)
    p = tmp_path / "m.json"
    p.write_text(
        json.dumps({"files": [{"path": "exports/trail-listing.txt", "collected_at": "2026-10-01", "request_id": "log-01"}]}), encoding="utf-8"
    )
    _, rep = run_json(mod, ["--scope", str(scope), "--manifest", str(p), "--as-of", "2026-11-15", "--json"])
    assert rows(rep, "LOG-01")[0]["status"] == "met"


def test_control_status_is_the_worst_status_of_its_rows():
    _, rep = run_json(mod, [*BASE, "--json"])
    # A.5.18 has met, missing and overdue rows; A.8.15 only met; A.8.5 met and missing
    assert control(rep, "A.5.18")["status"] == "overdue"
    assert control(rep, "A.8.15")["status"] == "met"
    assert control(rep, "A.8.5")["status"] == "missing"
    assert control(rep, "A.6.3")["status"] == "stale"
    s = rep["summary"]["controls_by_status"]
    assert s == {"met": 1, "missing": 4, "stale": 1, "overdue": 1, "gap": 1}


def test_control_with_no_request_is_a_gap_and_exits_1(tmp_path):
    entries = [("aws/cloudtrail-trails.json", "2026-09-10")]
    scope = scope_file(tmp_path, controls=["A.8.15", "A.7.4"])
    rc, rep = run_json(mod, ["--scope", str(scope), "--manifest", str(manifest_file(tmp_path, entries)), "--as-of", ASOF, "--json"])
    assert rc == 1
    assert rep["gaps"] == [{"control": "A.7.4", "topic": "", "reason": "no request in the catalogue"}]
    assert control(rep, "A.7.4")["status"] == "gap"
    _, md, _ = run_main(mod, ["--scope", str(scope), "--as-of", ASOF])
    assert "A.7.4" in md and "no request in the catalogue" in md


def test_control_only_covered_by_a_system_not_in_the_inventory_is_a_gap(tmp_path):
    scope = scope_file(tmp_path, controls=["A.8.15"], systems=[])
    rc, rep = run_json(mod, ["--scope", str(scope), "--as-of", ASOF, "--json"])
    assert rc == 1
    assert "not in the inventory" in rep["gaps"][0]["reason"] and "google-workspace" in rep["gaps"][0]["reason"]


def test_clean_plan_exits_0(tmp_path):
    entries = [("aws/cloudtrail-trails.json", "2026-09-10")]
    scope = scope_file(tmp_path)
    rc, md, _ = run_main(mod, ["--scope", str(scope), "--manifest", str(manifest_file(tmp_path, entries)), "--as-of", ASOF])
    assert rc == 0
    assert "1 met" in md and "None: every in-scope control has at least one applicable request." in md
    # without a manifest and before anything is due, a plan is also clean
    rc, _, _ = run_main(mod, ["--scope", str(scope), "--as-of", "2026-07-02"])
    assert rc == 0


def test_csv_is_the_pbc_spreadsheet_with_fixed_columns():
    rc, out, _ = run_main(mod, [*BASE, "--format", "csv"])
    assert rc == 1
    table = list(csv.reader(io.StringIO(out)))
    assert table[0] == ["request_id", "title", "controls", "system", "owner", "how_to_obtain", "frequency", "slot", "due_date", "freshness_days",
                        "status", "evidence_file", "collected_at", "used_by", "note"]  # fmt: skip
    assert all(len(r) == 15 for r in table)
    by = {(r[0], r[7]): r for r in table[1:] if r[0]}
    assert by["IAM-01", "Q1"][10] == "met" and by["IAM-01", "Q1"][11] == "aws/credential-report.csv"
    assert by["GWS-02", ""][10] == "not applicable"
    assert any(r[10] == "no request" and r[2] == "A.7.4" for r in table[1:])


def test_csv_cells_cannot_start_a_spreadsheet_formula(tmp_path):
    cat = tmp_path / "cat.json"
    cat.write_text(
        json.dumps(
            {
                "requests": [
                    {
                        "id": "X-01",
                        "title": '=HYPERLINK("http://example.com")',
                        "controls": {"iso27001-2022": ["A.8.15"]},
                        "system": "aws",
                        "how": "+cmd",
                        "frequency": "once-per-period",
                        "freshness_days": 10,
                        "owner_role": "@role",
                        "consumers": [],
                        "match": {"path_glob": []},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    _, out, _ = run_main(mod, ["--scope", str(scope_file(tmp_path)), "--catalogue", str(cat), "--as-of", ASOF, "--format", "csv"])
    row = next(r for r in csv.reader(io.StringIO(out)) if r[0] == "X-01")
    assert row[1].startswith("'=") and row[5] == "'+cmd" and row[4] == "Cloud platform lead"


def test_custom_catalogue_adds_a_request_and_overrides_by_id():
    args = [*BASE, "--catalogue", str(FX / "catalogue-custom.json"), "--json"]
    rc, rep = run_json(mod, args)
    assert rep["catalogue_overrides"] == 1
    # the added PHY-01 request is a document request, so A.7.4 is no longer a gap and gets quarterly rows with the added topic
    assert [r["slot"] for r in rows(rep, "PHY-01")] == ["Q1", "Q2"]
    assert rep["gaps"] == [] and control(rep, "A.7.4")["topic"].startswith("Premises")
    # the override turned IAM-02 monthly: six rows, and the bundled once-per-period row is gone
    assert len(rows(rep, "IAM-02")) == 6 and rows(rep, "IAM-02")[0]["freshness_days"] == 35
    assert rc == 1  # the planted stale and overdue rows are still there


def test_bundled_catalogue_schema():
    doc = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    requests, topics = mod.validate_catalogue(doc, "bundled")
    assert 28 <= len(requests) <= 45
    known_systems = {"aws", "m365", "entra", "github", "google-workspace", "hr-system", "endpoint-mdm", "ticketing", "document"}
    known_consumers = {"evidence-pack-builder", "control-map-from-exports", "access-review-pack", "github-change-control-evidence",
                       "aws-identity-and-logging-evidence", "vendor-attestation-digest"}  # fmt: skip
    assert len({r["id"] for r in requests}) == len(requests)
    used = set()
    for r in requests:
        assert any(r["controls"].values()), r["id"]
        assert r["frequency"] in mod.FREQUENCIES and r["freshness_days"] > 0
        assert r["system"] in known_systems, r["id"]
        assert r["consumers"] and set(r["consumers"]) <= known_consumers, r["id"]
        assert len(r["title"]) < 120 and len(r["how"]) <= 400 and r["owner_role"]
        assert r["path_glob"], r["id"]
        used |= {c for ids in r["controls"].values() for c in ids}
    assert {"iso27001-2022", "soc2"} == {fw for r in requests for fw in r["controls"] if r["controls"][fw]}
    assert used <= set(topics)  # every covered control has a paraphrase
    assert all(len(t.split()) <= 20 for t in topics.values())  # paraphrases only, never standard text
    assert all(is_control_id(c) for c in topics)
    for fw in ("iso27001-2022", "soc2"):
        assert sum(1 for r in requests if r["controls"].get(fw)) >= 20


def is_control_id(cid):
    return any(rx.match(cid) for rx in mod.CONTROL_RES.values())


def test_bundled_catalogue_keeps_to_identifiers_and_short_paraphrases():
    text = CATALOGUE.read_text(encoding="utf-8")
    assert not re.search(r"(?i)\bshall\b", text)  # standards wording, not ours
    assert chr(0x2014) not in text and chr(0x2013) not in text
    for r in json.loads(text)["requests"]:
        assert len(r["title"]) < 120


def test_malformed_inputs_exit_2(tmp_path):
    for argv in (
        ["--scope", str(FX / "scope-malformed.txt")],
        ["--scope", str(tmp_path / "missing.json")],
        [*BASE[:2], "--manifest", str(FX / "manifest-malformed.json")],
        [*BASE[:2], "--manifest", str(tmp_path / "missing.json")],
        [*BASE[:2], "--catalogue", str(tmp_path / "missing.json")],
        [*BASE[:2], "--as-of", "2026-13-40"],
        [*BASE[:2], "--as-of", "15/11/2026"],
    ):
        rc, out, err = run_main(mod, argv)
        assert rc == 2 and out == "" and err.startswith("error: "), argv
    bad_manifest = tmp_path / "bad.json"
    bad_manifest.write_text("[1, 2]", encoding="utf-8")
    assert run_main(mod, [*BASE[:2], "--manifest", str(bad_manifest)])[0] == 2
    bad_catalogue = tmp_path / "cat.json"
    bad_catalogue.write_text(json.dumps({"requests": [{"id": "X-1", "title": "t"}]}), encoding="utf-8")
    assert run_main(mod, [*BASE[:2], "--catalogue", str(bad_catalogue)])[0] == 2
    assert run_main(mod, [])[0] == 2  # --scope is required


@pytest.mark.parametrize(
    "changes",
    [
        {"period": {"start": "2026-12-31", "end": "2026-07-01"}},
        {"period": {"start": "2026-07-01", "end": "2026-02-30"}},
        {"period": {"start": "2020-01-01", "end": "2026-12-31"}},
        {"period": {"start": "2026-07-01"}},
        {"framework": "pci-dss"},
        {"framework": "soc2"},  # ISO ids are not SOC 2 ids
        {"controls": []},
        {"controls": ["A.8.15", "not-a-control"]},
        {"systems": [{"kind": "aws"}, {"kind": "AWS"}]},
        {"systems": [{"owner": "nobody"}]},
    ],
)
def test_bad_scope_values_exit_2(tmp_path, changes):
    rc, _, err = run_main(mod, ["--scope", str(scope_file(tmp_path, **changes)), "--as-of", ASOF])
    assert rc == 2 and err.startswith("error: ")


def test_period_end_before_start_and_unknown_framework_messages(tmp_path):
    _, _, err = run_main(mod, ["--scope", str(scope_file(tmp_path, period={"start": "2026-12-31", "end": "2026-07-01"})), "--as-of", ASOF])
    assert "before the start" in err
    _, _, err = run_main(mod, ["--scope", str(scope_file(tmp_path, framework="pci-dss")), "--as-of", ASOF])
    assert "unknown framework" in err


def test_help_names_every_option_and_the_exit_codes():
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0
    for needle in (
        "--scope",
        "--catalogue",
        "--manifest",
        "--as-of",
        "--format",
        "--out",
        "--json",
        "--redact",
        "Exit codes",
        "0 every",
        "1 any",
        "2 bad input",
    ):
        assert needle in out


def test_out_file_json_and_redaction(tmp_path):
    scope = scope_file(tmp_path, systems=[{"kind": "aws", "owner": "jane.doe@example.com"}])
    out = tmp_path / "plan.json"
    rc, stdout, _ = run_main(mod, ["--scope", str(scope), "--as-of", ASOF, "--format", "json", "--redact", "--out", str(out)])
    assert rc == 0 and stdout == ""
    text = out.read_text(encoding="utf-8")
    assert "jane.doe@example.com" not in text and "@redacted.invalid" in text
    assert json.loads(text)["framework"] == "iso27001-2022"
    unredacted = run_main(mod, ["--scope", str(scope), "--as-of", ASOF])[1]
    assert "jane.doe@example.com" in unredacted
    named = scope_file(tmp_path, systems=[{"kind": "aws", "owner": "Jane Doe"}])
    assert "Jane Doe" not in run_main(mod, ["--scope", str(named), "--as-of", ASOF, "--redact"])[1]


def test_secret_shaped_text_in_a_catalogue_is_masked(tmp_path):
    cat = tmp_path / "cat.json"
    key = "AKIA" + "ABCDEFGHIJKLMNOP"
    cat.write_text(
        json.dumps(
            {
                "requests": [
                    {
                        "id": "X-02",
                        "title": "Key check",
                        "controls": {"iso27001-2022": ["A.8.15"]},
                        "system": "aws",
                        "how": f"look at {key}",
                        "frequency": "once-per-period",
                        "freshness_days": 10,
                        "owner_role": "Lead",
                        "consumers": [],
                        "match": {"path_glob": []},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out = run_main(mod, ["--scope", str(scope_file(tmp_path)), "--catalogue", str(cat), "--as-of", ASOF])[1]
    assert key not in out and "[masked secret]" in out


def test_example_scope_in_references_runs_with_the_bundled_catalogue():
    example = SKILLS / "evidence-collection-plan" / "references" / "example-scope-iso27001.json"
    rc, rep = run_json(mod, ["--scope", str(example), "--as-of", "2026-10-20", "--json"])
    assert rc == 1 and rep["summary"]["rows"] > 10


def test_golden_markdown_for_the_iso_fixture():
    golden = FX / "expected-iso27001.md"
    rc, out, _ = run_main(mod, BASE)
    assert rc == 1
    assert out == golden.read_text(encoding="utf-8")


def test_script_has_no_network_or_subprocess_code():
    text = (SKILLS / "evidence-collection-plan" / "scripts" / "collection_plan.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(socket|subprocess|urllib|http|requests|ssl)\b", text, re.M)
    assert "os.environ" not in text and "getenv" not in text
