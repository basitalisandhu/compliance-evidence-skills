"""Tests for maester-control-map/scripts/maester_map.py. The results files are synthetic (invented tenant
contoso-example, zero GUID) in the shape written by Invoke-Maester -OutputJsonFile."""

from __future__ import annotations

import csv
import hashlib
import json
import re

import pytest
from conftest import FIXTURES, SKILLS, load_script, run_json, run_main

mod = load_script("maester-control-map", "maester_map.py")
DIR = FIXTURES / "maester"
RESULTS = DIR / "results.json"
MAP = DIR / "map.csv"
SKILL = SKILLS / "maester-control-map"
BASE = [str(RESULTS), "--map", str(MAP), "--as-of", "2026-10-16"]


def control(rep, fw, cid):
    return next(c for c in rep["controls"] if c["framework"] == fw and c["control"] == cid)


def test_control_states_from_each_result_type():
    rc, rep = run_json(mod, [*BASE, "--json"])
    assert rc == 1  # A.8.2 is contradicted
    assert control(rep, "iso27001", "A.8.2")["state"] == "contradicted"
    assert control(rep, "iso27001", "A.8.5")["state"] == "supported"
    assert control(rep, "iso27001", "A.8.1")["state"] == "supported"
    assert control(rep, "soc2", "CC6.1")["state"] == "supported"
    assert control(rep, "soc2", "CC6.1")["counts"] == {"Passed": 1, "Failed": 0, "Skipped": 1, "NotRun": 0, "Error": 0, "Investigate": 0}
    inv = control(rep, "iso27001", "A.5.15")
    assert inv["state"] == "not assessable" and inv["needs_human_review"] == ["MT.1005"]
    assert control(rep, "iso27001", "A.8.9")["state"] == "not assessable"  # Error only
    assert rep["summary"]["results"] == {"Passed": 5, "Failed": 1, "Skipped": 1, "NotRun": 1, "Error": 1, "Investigate": 1}


def test_investigate_never_supports_and_failed_wins(tmp_path):
    m = tmp_path / "m.csv"
    m.write_text("match,framework,control,note\nMT.1005,iso27001,A.8.2,x\nMT.1006,iso27001,A.8.2,x\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(RESULTS), "--map", str(m), "--as-of", "2026-10-16", "--json"])
    assert rc == 0 and control(rep, "iso27001", "A.8.2")["state"] == "not assessable"  # Passed + Investigate
    m.write_text("match,framework,control,note\nMT.1005,iso27001,A.8.2,x\nCIS.M365.1.1.3,iso27001,A.8.2,x\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(RESULTS), "--map", str(m), "--as-of", "2026-10-16", "--json"])
    assert rc == 1 and control(rep, "iso27001", "A.8.2")["state"] == "contradicted"
    m.write_text("match,framework,control,note\nEIDSCA.AP04,soc2,CC6.1,x\nCISA.MS.AAD.3.1,soc2,CC6.1,x\n", encoding="utf-8")
    _, rep = run_json(mod, [str(RESULTS), "--map", str(m), "--as-of", "2026-10-16", "--json"])
    assert control(rep, "soc2", "CC6.1")["state"] == "not assessable"  # Skipped and NotRun only


def test_matching_by_id_prefix_tag_and_name_fallback():
    _, rep = run_json(mod, [*BASE, "--json"])
    ids = {t["id"] for t in control(rep, "iso27001", "A.8.5")["tests"]}
    assert ids == {"EIDSCA.AF01", "CISA.MS.AAD.3.1", "MT.1006"}  # exact id, tag:EIDSCA.AF01 and CISA.MS.AAD.3.*
    assert [t["id"] for t in control(rep, "iso27001", "A.8.2")["tests"]] == ["CIS.M365.1.1.1", "CIS.M365.1.1.3"]
    assert [t["id"] for t in control(rep, "iso27001", "A.8.9")["tests"]] == ["MT.1021"]  # Id from Name
    assert control(rep, "iso27001", "A.8.2")["tests"][1]["citation"] == "[evidence: results.json#Tests[3].Result]"
    assert rep["unmapped_tests"] == [{"id": "MT.1033", "result": "Passed"}]
    assert rep["unmatched_map_rows"] == [{"line": 10, "match": "ORCA.*", "framework": "soc2", "control": "CC7.2"}]
    assert control(rep, "soc2", "CC7.2")["state"] == "not assessable"


def test_hash_executed_at_and_stale():
    _, rep = run_json(mod, [*BASE, "--json"])
    assert rep["results_sha256"] == hashlib.sha256(RESULTS.read_bytes()).hexdigest()
    assert rep["executed_at"].startswith("2026-10-10T09:15:00") and rep["freshness"]["stale"] is False
    rc, rep = run_json(mod, [str(RESULTS), "--as-of", "2026-12-31", "--json"])
    assert rc == 1 and rep["freshness"]["stale"] is True and rep["controls"] == []
    rc, rep = run_json(mod, [str(RESULTS), "--as-of", "2026-12-31", "--max-age-days", "90", "--json"])
    assert rc == 0 and rep["freshness"]["stale"] is False


def test_missing_executed_at_is_stale_and_counts_are_checked(tmp_path):
    doc = json.loads(RESULTS.read_text(encoding="utf-8"))
    del doc["ExecutedAt"]
    doc["PassedCount"] = 99
    p = tmp_path / "r.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc, rep = run_json(mod, [str(p), "--as-of", "2026-10-16", "--json"])
    assert rc == 1 and rep["freshness"]["stale"] is True and "ExecutedAt" in rep["freshness"]["reason"]
    assert rep["warnings"] == ["PassedCount in the file is 99 but the Tests list has 5"]


def test_powershell_51_date_format(tmp_path):
    doc = json.loads(RESULTS.read_text(encoding="utf-8"))
    doc["ExecutedAt"] = "/Date(1791622800000)/"  # 2026-10-10T09:00:00Z
    p = tmp_path / "r.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    rc, rep = run_json(mod, [str(p), "--as-of", "2026-10-16", "--json"])
    assert rc == 0 and rep["freshness"]["age_days"] == 5


def test_annotated_csv_markdown_out_and_redact(tmp_path):
    out, sheet = tmp_path / "map.md", tmp_path / "annotated.csv"
    rc, printed, _ = run_main(mod, [*BASE, "--out", str(out), "--annotated-csv", str(sheet), "--redact"])
    md = out.read_text(encoding="utf-8")
    assert rc == 1 and printed == ""
    assert "contoso-example" not in md and "00000000-0000-0000-0000-000000000001" not in md and "tenant-" in md
    assert "| iso27001 | A.8.2 |" in md and "needs human review" in md and "Preparation for a human assessor" in md
    assert not re.search(r"\| (non-?)?compliant \|", md, re.I)  # never a verdict; test titles may use the word
    with sheet.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 10 and rows[0]["Id"] == "MT.1001" and rows[0]["iso27001"] == "A.8.1"
    assert next(r for r in rows if r["Id"] == "EIDSCA.AF01")["soc2"] == "CC6.1"
    assert next(r for r in rows if r["Id"] == "MT.1033")["iso27001"] == ""
    _, js, _ = run_main(mod, [*BASE, "--json", "--redact"])
    assert "it-admin@example.com" not in js and "contoso-example" not in js


def test_example_map_is_valid_and_labelled_as_an_example():
    text = (SKILL / "references" / "example-map.csv").read_text(encoding="utf-8")
    rows = list(csv.DictReader(text.splitlines()))
    assert 3 <= len(rows) <= 8 and all(r["note"].startswith("EXAMPLE to review") for r in rows)
    rc, rep = run_json(mod, [str(RESULTS), "--map", str(SKILL / "references" / "example-map.csv"), "--as-of", "2026-10-16", "--json"])
    assert rc == 1 and rep["unmatched_map_rows"] == []


def test_identifier_lists_are_copies_of_control_map_lists():
    for name in ("iso27001-identifiers.md", "soc2-identifiers.md"):
        mine = (SKILL / "references" / name).read_text(encoding="utf-8")
        theirs = (SKILLS / "control-map-from-exports" / "references" / name).read_text(encoding="utf-8")
        assert mine == theirs, f"{name} differs from the control-map-from-exports copy"


def test_extra_identifier_list(tmp_path):
    m = tmp_path / "m.csv"
    m.write_text("match,framework,control,note\nMT.1033,iso27001,A.5.16,x\n", encoding="utf-8")
    rc, _, err = run_main(mod, [str(RESULTS), "--map", str(m), "--as-of", "2026-10-16"])
    assert rc == 2 and "A.5.16" in err and "--identifiers" in err
    extra = tmp_path / "ids.md"
    extra.write_text("| A.5.16 | Identities are managed through their whole life | Entra ID |\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(RESULTS), "--map", str(m), "--identifiers", str(extra), "--as-of", "2026-10-16", "--json"])
    assert rc == 0 and control(rep, "iso27001", "A.5.16")["state"] == "supported"


@pytest.mark.parametrize(
    "results,map_text,extra,message",
    [
        ("truncated-results.txt", None, [], "invalid JSON"),
        ("empty.json", None, [], "empty file"),
        ("no-tests.json", None, [], "Tests list"),
        ("bad-result.json", None, [], "Result must be one of"),
        ("no-id.json", None, [], "neither Id nor Name"),
        ("results.json", "match,framework,control,note\nMT.1001,nist,A.8.1,x\n", [], "framework must be"),
        ("results.json", "match,framework,control,note\nMT.1001,iso27001,A.99.1,x\n", [], "identifier list"),
        ("results.json", "match,framework\nMT.1001,iso27001\n", [], "needs the columns"),
        ("results.json", None, ["--as-of", "soon"], "YYYY-MM-DD"),
        ("results.json", None, ["--max-age-days", "-1"], "--max-age-days"),
    ],
)
def test_bad_input_exits_2(tmp_path, results, map_text, extra, message):
    args = [str(DIR / results), *extra]
    if map_text is not None:
        m = tmp_path / "m.csv"
        m.write_text(map_text, encoding="utf-8")
        args += ["--map", str(m)]
    rc, _, err = run_main(mod, args)
    assert rc == 2 and err.startswith("error:") and message in err


def test_help_and_reads_files_only():
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "Exit codes" in out and "--redact" in out and "--json" in out and "Investigate" in out
    text = (SKILL / "scripts" / "maester_map.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(socket|subprocess|urllib|http|requests|ssl)\b", text, re.M)
    assert "os.environ" not in text and "getenv" not in text


def test_example_map_uses_real_maester_test_ids():
    # Maester has no MFA tag and its CISA tests are CISA.MS.AAD.*; checked against the Maester repository (2.3.0, 3.0
    # previews). Tags are written differently by Maester 3, so the shipped example matches by id only.
    rows = list(csv.DictReader((SKILL / "references" / "example-map.csv").read_text(encoding="utf-8").splitlines()))
    for r in rows:
        assert not r["match"].lower().startswith("tag:"), r
        assert re.match(r"^(MT\.\d{4}|CIS\.M365\.|CISA\.MS\.|EIDSCA\.|ORCA\.)", r["match"]), r
