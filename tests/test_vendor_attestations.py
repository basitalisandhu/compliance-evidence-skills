"""Tests for vendor-attestation-digest/scripts/vendor_attestations.py. Every vendor, register row and document is
synthetic (tests/fixtures/vendors and rows built here)."""

from __future__ import annotations

import csv
import json
import re

import pytest
from conftest import FIXTURES, SKILLS, load_script, run_json, run_main

mod = load_script("vendor-attestation-digest", "vendor_attestations.py")
REG = FIXTURES / "vendors" / "register.csv"
VEN = FIXTURES / "vendors" / "vendors.csv"
DOCS = FIXTURES / "vendors" / "docs"
BASE = ["--register", str(REG), "--vendors", str(VEN), "--as-of", "2026-10-16"]
HEADER = (
    "vendor,type,issuer,period_start,period_end,valid_from,valid_to,opinion,exceptions,scope_services,cuecs,cuecs_reviewed,"
    "source_file,source_page\n"
)
BAD_VENDORS = "vendor,services_used,criticality,owner\nExample DNS,DNS,critical,Alex Kim\n"


def vendor(rep, name):
    return next(v for v in rep["vendors"] if v["vendor"] == name)


def codes(rep, name):
    return [f["code"] for f in vendor(rep, name)["findings"]]


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_fixture_findings_states_and_order():
    rc, rep = run_json(mod, [*BASE, "--docs", str(DOCS), "--json"])
    assert rc == 1
    assert [v["vendor"] for v in rep["vendors"]][:3] == ["Example Hosting", "Example Mail", "Example Signing"]
    assert rep["vendors"][-1]["criticality"] == "not in vendor list"
    assert codes(rep, "Example Hosting") == ["bridge-letter-expired", "exceptions-noted"]
    assert codes(rep, "Example Mail") == ["coverage-gap", "type1-only", "scope-mismatch"]
    assert codes(rep, "Example Signing") == ["opinion-not-unqualified", "exceptions-noted", "cuecs-not-reviewed"]
    assert codes(rep, "Example Analytics") == ["expiring", "source-unverified"]
    assert codes(rep, "Example Backup") == ["expired", "missing-field"]
    assert codes(rep, "Example Payroll") == ["no-attestation"]
    assert codes(rep, "Example Fonts") == [] and vendor(rep, "Example Fonts")["state"] == "not assessable"
    assert codes(rep, "Example DNS") == [] and vendor(rep, "Example DNS")["state"] == "supported"
    assert vendor(rep, "Example Mail")["state"] == "contradicted"
    assert rep["summary"]["findings"] == 13


def test_superseded_report_raises_nothing_and_bridge_covers_gap():
    _, rep = run_json(mod, [*BASE, "--docs", str(DOCS), "--json"])
    hosting = vendor(rep, "Example Hosting")["documents"]
    assert hosting[0]["superseded"] is True and hosting[1]["superseded"] is False
    assert all(f.get("register_row") != 1 for f in vendor(rep, "Example Hosting")["findings"])
    signing = vendor(rep, "Example Signing")
    assert "coverage-gap" not in codes(rep, "Example Signing")
    assert any("covered by the bridge letter in register row 7" in n for n in signing["documents"][0]["notes"])


def test_sources_hashed_only_with_docs():
    _, rep = run_json(mod, [*BASE, "--docs", str(DOCS), "--json"])
    dns = vendor(rep, "Example DNS")["documents"][0]
    assert re.fullmatch(r"[0-9a-f]{64}", dns["source_sha256"])
    _, rep = run_json(mod, [*BASE, "--json"])
    assert rep["sources_checked"] is False and "source-unverified" not in json.dumps(rep["summary"])
    assert vendor(rep, "Example Analytics")["state"] == "supported"


def test_missing_field_is_not_assessable_never_guessed(tmp_path):
    reg = write(tmp_path, "r.csv", HEADER + "Example DNS,soc2-type2,Example Audit LLP,2025-10-01,2026-09-30,,,unknown,,DNS,none,,dns.txt,\n")
    rc, rep = run_json(mod, ["--register", str(reg), "--vendors", str(VEN), "--as-of", "2026-10-16", "--json"])
    dns = vendor(rep, "Example DNS")
    fields = sorted(f["field"] for f in dns["findings"] if f["code"] == "missing-field")
    assert rc == 1 and fields == ["exceptions", "opinion", "source_page"]
    assert dns["documents"][0]["state"] == "not assessable" and dns["state"] == "not assessable"


def test_policy_options_change_the_result(tmp_path):
    reg = write(tmp_path, "r.csv", HEADER + "Example DNS,soc2-type2,Example Audit LLP,2024-12-01,2025-11-30,,,unqualified,0,DNS,none,,dns.txt,2\n")
    args = ["--register", str(reg), "--vendors", str(VEN), "--as-of", "2026-10-16", "--json"]
    _, rep = run_json(mod, args)
    assert codes(rep, "Example DNS") == ["expiring", "coverage-gap"]
    _, rep = run_json(mod, [*args, "--max-report-age-months", "6"])
    assert codes(rep, "Example DNS") == ["expired"] and vendor(rep, "Example DNS")["state"] == "contradicted"
    _, rep = run_json(mod, [*args, "--bridge-max-months", "12", "--expiring-days", "30"])
    assert codes(rep, "Example DNS") == [] and vendor(rep, "Example DNS")["state"] == "supported"
    assert rep["policy"]["bridge_max_months"] == 12


def test_json_register_and_clean_run_exits_0(tmp_path):
    reg = write(
        tmp_path,
        "r.json",
        json.dumps(
            {
                "attestations": [
                    {
                        "vendor": "Example DNS",
                        "type": "iso27001-certificate",
                        "issuer": "Example Certification Ltd",
                        "valid_from": "2025-01-15",
                        "valid_to": "2028-01-14",
                        "scope_services": ["DNS"],
                        "source_file": "dns-iso-certificate.txt",
                        "source_page": 1,
                    }
                ]
            }
        ),
    )
    ven = write(tmp_path, "v.csv", "vendor,services_used,criticality,owner\nExample DNS,DNS,high,Alex Kim\nExample Fonts,Web fonts,low,Sam Lee\n")
    rc, rep = run_json(mod, ["--register", str(reg), "--vendors", str(ven), "--docs", str(DOCS), "--as-of", "2026-10-16", "--json"])
    assert rc == 0 and rep["summary"]["findings"] == 0
    assert vendor(rep, "Example DNS")["state"] == "supported"


def test_markdown_csv_out_and_redact(tmp_path):
    out, sheet = tmp_path / "digest.md", tmp_path / "actions.csv"
    rc, printed, _ = run_main(mod, [*BASE, "--docs", str(DOCS), "--out", str(out), "--csv", str(sheet), "--redact"])
    md = out.read_text(encoding="utf-8")
    assert rc == 1 and printed == ""
    assert "jane.doe@example.com" not in md and "Sam Lee" not in md and "@redacted.invalid" in md and "owner-" in md
    assert "| Example Payroll | medium |" in md and "Preparation for a human assessor" in md
    assert not re.search(r"\bcompliant\b", md, re.I)
    with sheet.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert sum(1 for r in rows if r["finding"]) == 13 and "jane.doe@example.com" not in sheet.read_text(encoding="utf-8")
    assert {r["vendor"] for r in rows if not r["finding"]} == {"Example DNS", "Example Fonts", "Example Unlisted"}


@pytest.mark.parametrize(
    "register,vendors,extra,message",
    [
        ("", None, [], "empty register"),
        ("[1, 2", None, [], "invalid JSON"),
        (HEADER + "Example DNS,soc3,X,,,,,,,,,,a.txt,1\n", None, [], "type must be one of"),
        (HEADER + "Example DNS,soc2-type2,X,2025-01-01,2025-12-31,,,clean,0,DNS,none,,a.txt,1\n", None, [], "opinion must be one of"),
        (HEADER + "Example DNS,soc2-type2,X,2025-01-01,2025-12-31,,,unqualified,two,DNS,none,,a.txt,1\n", None, [], "whole number"),
        (HEADER + ",soc2-type2,X,,,,,,,,,,a.txt,1\n", None, [], "has no vendor"),
        (HEADER + "Example DNS,other,X,,,,2027-01-01,,,,,,a.txt,1\n", BAD_VENDORS, [], "criticality must be"),
        (HEADER + "Example DNS,other,X,,,,2027-01-01,,,,,,a.txt,1\n", None, ["--bridge-max-months", "-1"], "--bridge-max-months"),
    ],
)
def test_bad_input_exits_2(tmp_path, register, vendors, extra, message):
    suffix = ".json" if register.startswith("[") else ".csv"
    reg = write(tmp_path, "r" + suffix, register)
    ven = write(tmp_path, "v.csv", vendors) if vendors else VEN
    rc, _, err = run_main(mod, ["--register", str(reg), "--vendors", str(ven), "--as-of", "2026-10-16", *extra])
    assert rc == 2 and err.startswith("error:") and message in err


def test_as_of_is_required_and_checked_and_help():
    rc, _, err = run_main(mod, ["--register", str(REG), "--vendors", str(VEN)])
    assert rc == 2 and "--as-of" in err
    rc, _, err = run_main(mod, [*BASE[:-1], "16/10/2026"])
    assert rc == 2 and "YYYY-MM-DD" in err
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "Exit codes" in out and "--redact" in out and "--json" in out and "not assessable" in out


def test_script_reads_files_only():
    text = (SKILLS / "vendor-attestation-digest" / "scripts" / "vendor_attestations.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*(import|from)\s+(socket|subprocess|urllib|http|requests|ssl)\b", text, re.M)
    assert "os.environ" not in text and "getenv" not in text
