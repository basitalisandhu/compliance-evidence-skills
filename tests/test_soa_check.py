"""Tests for iso27001-soa-check/scripts/soa_check.py. The company, owners, risks and evidence files are synthetic
(tests/fixtures/soa and tables built here); no ISO control titles or text are used."""

from __future__ import annotations

import csv
import io
import json

from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("iso27001-soa-check", "soa_check.py")
FX = FIXTURES / "soa"
GOOD = FX / "soa-good.csv"
GAPS = FX / "soa-gaps.csv"
RISKS = FX / "risk-register.csv"
EVIDENCE = FX / "evidence"
ASOF = ["--as-of", "2026-10-26"]


def rules(rep, severity=None):
    return sorted(x["rule"] for x in rep["findings"] if severity is None or x["severity"] == severity)


def by_rule(rep, rule):
    return [x for x in rep["findings"] if x["rule"] == rule]


def write_csv(tmp_path, header, rows, name="soa.csv", delimiter=","):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimiter, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    p = tmp_path / name
    p.write_text(buf.getvalue(), encoding="utf-8")
    return p


def full_rows(**overrides):
    """All 93 controls, included, justified, implemented with an evidence path, owned and recently reviewed."""
    rows = []
    for clause, _, count in mod.THEMES:
        for n in range(1, count + 1):
            cid = f"A.{clause}.{n}"
            rows.append(overrides.get(cid, [cid, "Yes", "Risk R-01", "Implemented", "policies/acceptable-use.md",
                                            "Head of IT", "2026-06-01"]))
    return rows


HEADER = ["Control", "Applicable", "Justification", "Status", "Evidence", "Owner", "Last reviewed"]


def test_annex_a_has_93_controls_in_four_themes():
    assert len(mod.ANNEX_A) == 93 and len(set(mod.ANNEX_A)) == 93
    assert [(c, n) for c, _, n in mod.THEMES] == [("5", 37), ("6", 8), ("7", 14), ("8", 34)]
    assert mod.ANNEX_A[0] == "A.5.1" and mod.ANNEX_A[-1] == "A.8.34"


def test_good_soa_is_clean_with_evidence_and_risks():
    rc, rep = run_json(mod, [str(GOOD), "--evidence-root", str(EVIDENCE), "--risk-register", str(RISKS), *ASOF,
                             "--json", "--fail-on", "warning"])
    assert rc == 0 and rep["findings"] == []
    assert rep["annex_a_rows"] == 93
    assert [(t["theme"], t["in_soa"], t["excluded"]) for t in rep["themes"]] == [
        ("Organisational", 37, 0), ("People", 8, 0), ("Physical", 14, 3), ("Technological", 34, 1)]
    assert rep["evidence"]["missing"] == 0 and rep["evidence"]["found"] == rep["evidence"]["checked"] > 0


def test_gaps_fixture_reports_each_problem_with_its_line():
    rc, rep = run_json(mod, [str(GAPS), "--evidence-root", str(EVIDENCE), "--risk-register", str(RISKS), *ASOF,
                             "--json"])
    assert rc == 1
    expected = {
        "duplicate-id": ("A.5.15", 4), "implemented-no-evidence": ("A.5.17", 5),
        "included-no-justification": ("A.5.18", 6), "included-no-status": ("A.5.19", 7),
        "evidence-not-found": ("A.6.3", 10), "excluded-no-justification": ("A.7.4", 11),
        "status-contradicts-applicability": ("A.7.9", 12), "owner-missing": ("A.8.1", 13),
        "review-overdue": ("A.8.1", 13), "review-date-unreadable": ("A.8.5", 14),
        "risk-treats-excluded": ("A.8.13", 15), "evidence-outside-root": ("A.8.32", 17),
        "id-2013": ("A.12.4.1", 18), "excluded-but-implemented": ("A.8.13", 15),
    }
    for rule, (cid, line) in expected.items():
        hits = by_rule(rep, rule)
        assert [(h["control"], h["line"]) for h in hits] == [(cid, line)], rule
    assert sorted((h["control"], h["line"]) for h in by_rule(rep, "applicability-unclear")) == [
        ("A.5.23", 8), ("A.5.24", 9)]
    assert sorted(str(h["line"]) for h in by_rule(rep, "unknown-id")) == ["19", "20"]
    assert {h["control"] for h in by_rule(rep, "included-unreferenced")} == {"A.5.18", "A.8.16"}
    assert len(by_rule(rep, "missing-controls")) == 4
    assert rep["counts"] == {"error": 21, "warning": 9, "note": 0}


def test_theme_counts_leave_out_other_frameworks_and_2013_rows():
    rc, rep = run_json(mod, [str(GAPS), *ASOF, "--json"])
    assert sum(t["in_soa"] for t in rep["themes"]) == rep["annex_a_rows"] == 15
    assert [r["id"] for r in rep["other_rows"]] == ["A.12.4.1", "A.5.38", "CC6.1"]
    assert rep["columns"]["control"] == "Annex A ref" and rep["columns"]["applicable"] == "Applicable?"
    assert rep["columns"]["justification"] == "Reason" and rep["columns"]["evidence"] == "Evidence location"


def test_identifier_forms_and_2013_detection():
    assert mod.normalise_id("A.5.1") == ("2022", "A.5.1")
    assert mod.normalise_id("5.1") == ("2022", "A.5.1")
    assert mod.normalise_id("A 8.34") == ("2022", "A.8.34")
    assert mod.normalise_id("Annex A 6.8") == ("2022", "A.6.8")
    assert mod.normalise_id("A.12.4.1") == ("2013", "A.12.4.1")
    assert mod.normalise_id("A.5.1.1") == ("2013", "A.5.1.1")
    assert mod.normalise_id("A.9.2") == ("2013", "A.9.2")
    assert mod.normalise_id("A.8.35") == ("unknown", "A.8.35")
    assert mod.normalise_id("CC6.1")[0] == "unknown" and mod.normalise_id("  ")[0] == "blank"


def test_map_overrides_semicolon_and_separate_justification_columns(tmp_path):
    header = ["ISO ref", "In scope", "Why included", "Why excluded", "State", "Proof", "Accountable", "Checked on"]
    rows = [[r[0], r[1], r[2] if r[1] == "Yes" else "", "", r[3], r[4], r[5], "01/06/2026"] for r in full_rows()]
    rows[0] = ["A.5.1", "No", "", "No such activity (scope statement)", "", "", "", ""]
    p = write_csv(tmp_path, header, rows, delimiter=";")
    rc, out, err = run_main(mod, [str(p), *ASOF])
    assert rc == 2 and "no control identifier column" in err
    args = [str(p), *ASOF, "--json", "--map", "control=ISO ref", "--map", "inclusion_justification=Why included",
            "--map", "exclusion_justification=Why excluded", "--map", "status=State", "--map", "evidence=Proof",
            "--map", "reviewed=Checked on"]
    rc, rep = run_json(mod, args)
    assert rc == 0 and rep["findings"] == [], rep["findings"]
    assert rep["themes"][0]["excluded"] == 1
    assert run_main(mod, [str(p), "--map", "control=Nope"])[0] == 2
    assert run_main(mod, [str(p), "--map", "colour=ISO ref"])[0] == 2


def test_review_age_limit_and_missing_columns(tmp_path):
    p = write_csv(tmp_path, HEADER, full_rows(**{"A.6.1": ["A.6.1", "Yes", "Risk R-01", "Implemented",
                                                           "x.md", "People lead", "2025-09-01"]}))
    rc, rep = run_json(mod, [str(p), *ASOF, "--json"])
    assert rules(rep) == ["review-overdue"]
    assert run_json(mod, [str(p), *ASOF, "--json", "--max-age-days", "500"])[1]["findings"] == []
    bare = write_csv(tmp_path, ["Control", "Applicable", "Reason"], [[r[0], "Yes", "Contract"] for r in full_rows()],
                     name="bare.csv")
    rc, rep = run_json(mod, [str(bare), *ASOF, "--json"])
    assert rules(rep) == ["no-owner-column", "no-review-column", "no-status-column"]


def test_risk_register_cross_checks(tmp_path):
    soa = write_csv(tmp_path, HEADER, full_rows(**{"A.8.13": ["A.8.13", "No", "Hosting provider does it", "", "",
                                                              "", ""]}))
    risks = write_csv(tmp_path, ["ID", "Treatment"], [["R-01", "A.8.13, 5.17 and A.9.4.1"], ["R-02", "8.40"]],
                      name="risks.csv")
    rc, rep = run_json(mod, [str(soa), "--risk-register", str(risks), *ASOF, "--json"])
    assert rc == 1 and rules(rep, "error") == ["risk-treats-excluded"]
    assert by_rule(rep, "risk-unknown-control")[0]["detail"].startswith("risk R-02")
    unref = {h["control"] for h in by_rule(rep, "included-unreferenced")}
    assert unref == set()  # every justification names a risk
    soa2 = write_csv(tmp_path, HEADER, full_rows(**{"A.5.2": ["A.5.2", "Yes", "Good idea", "Planned", "", "Head of IT",
                                                              "2026-06-01"]}), name="soa2.csv")
    rc, rep = run_json(mod, [str(soa2), "--risk-register", str(risks), *ASOF, "--json"])
    assert [h["control"] for h in by_rule(rep, "included-unreferenced")] == ["A.5.2"] and rc == 0
    assert run_main(mod, [str(soa2), "--risk-register", str(risks), *ASOF, "--fail-on", "warning"])[0] == 1
    norisk = write_csv(tmp_path, ["ID", "Owner"], [["R-01", "CTO"]], name="norisk.csv")
    assert run_main(mod, [str(soa2), "--risk-register", str(norisk)])[0] == 2


def test_json_input_utf16_and_title_pass_through(tmp_path):
    rc, rep = run_json(mod, [str(FX / "soa-small.json"), *ASOF, "--json"])
    assert rc == 1 and rep["annex_a_rows"] == 2
    assert by_rule(rep, "excluded-no-justification")[0]["control"] == "A.7.3"
    text = "Control\tApplicable\tTitle\nA.5.1\tmaybe\tOur own policy wording\n"
    p = tmp_path / "unicode.txt"
    p.write_bytes(text.encode("utf-16"))
    rc, rep = run_json(mod, [str(p), *ASOF, "--json"])
    hit = by_rule(rep, "applicability-unclear")[0]
    assert hit["title"] == "Our own policy wording"
    rc, out, _ = run_main(mod, [str(p), *ASOF])
    assert "A.5.1 (Our own policy wording)" in out


def test_redact_hides_emails_and_owners(tmp_path):
    rows = full_rows(**{"A.5.3": ["A.5.3", "Yes", "Risk R-01", "Implemented", "", "Ada Example", "2026-06-01"],
                        "A.5.4": ["A.5.4", "Maybe", "", "", "", "ada@example.com", "2026-06-01"]})
    rows.append(["A.5.4", "Yes", "Risk R-01", "Implemented", "notes from ada@example.com and Ada Example.md",
                 "Ada Example", "2026-06-01"])
    p = write_csv(tmp_path, HEADER, rows)
    rc, out, _ = run_main(mod, [str(p), *ASOF, "--json"])
    assert "ada@example.com" not in out  # duplicate rows are not read further
    p2 = write_csv(tmp_path, HEADER, full_rows(**{"A.5.4": ["A.5.4", "Yes", "Risk R-01", "Implemented",
                                                            "notes from ada@example.com and Ada Example.md",
                                                            "Ada Example", "2026-06-01"]}), name="p2.csv")
    rc, out, _ = run_main(mod, [str(p2), *ASOF, "--evidence-root", str(tmp_path), "--json"])
    assert "ada@example.com" in out and "Ada Example" in out
    rc, out, _ = run_main(mod, [str(p2), *ASOF, "--evidence-root", str(tmp_path), "--json", "--redact"])
    assert "ada@example.com" not in out and "Ada Example" not in out and "@redacted.invalid" in out


def test_bad_input_exits_2(tmp_path):
    cases = {
        "latin1.csv": "Control,Applicable\nA.5.1,sí\n".encode("cp1252"),
        "empty.csv": b"",
        "header-only.csv": b"Control,Applicable\n",
        "book.csv": b"PK\x03\x04rest-of-a-zip",
        "bad.json": b"[{",
        "shape.json": b'{"rows": "no"}',
    }
    for name, data in cases.items():
        p = tmp_path / name
        p.write_bytes(data)
        rc, out, err = run_main(mod, [str(p), *ASOF])
        assert rc == 2 and err.startswith("soa_check.py: ") and "Traceback" not in err, name
    assert run_main(mod, [str(tmp_path / "missing.csv")])[0] == 2
    assert run_main(mod, [str(GOOD), "--as-of", "26/10/2026"])[0] == 2
    assert run_main(mod, [str(GOOD), "--max-age-days", "0"])[0] == 2
    assert run_main(mod, [str(GOOD), "--evidence-root", str(tmp_path / "nope")])[0] == 2
    rc, _, err = run_main(mod, [str(GOOD), *ASOF, "--out", str(tmp_path / "no" / "dir" / "r.md")])
    assert rc == 2 and "cannot write output" in err


def test_markdown_report_and_out_file(tmp_path):
    rc, out, _ = run_main(mod, [str(GAPS), *ASOF])
    assert rc == 1
    assert out.startswith("## Statement of Applicability check: ")
    assert "| Physical (7.x) | 14 | 2 | 1 | 1 | 0 | 0 | 2 |" in out
    assert "preparation for a human assessor" in out.lower()
    target = tmp_path / "r.json"
    rc, out, _ = run_main(mod, [str(GOOD), *ASOF, "--json", "--out", str(target)])
    assert rc == 0 and out == ""
    assert json.loads(target.read_text(encoding="utf-8"))["annex_a_rows"] == 93
