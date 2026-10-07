"""Tests for auditor-narrative-drafter/scripts/narrative.py: drafts cite evidence and pass the linter."""
import json
import re

from conftest import AS_OF, FIXTURES, load_script, run_json, run_main

mod = load_script("auditor-narrative-drafter", "narrative.py")
lint = load_script("auditor-narrative-drafter", "narrative_lint.py")
CMAP = FIXTURES / "narrative" / "control-map.json"


def draft(*args):
    rc, out, err = run_main(mod, [str(CMAP), "--as-of", AS_OF, *args])
    assert rc == 0, err
    return out


def test_supported_control_cites_every_evidence_sentence():
    out = draft("--control", "A.8.15")
    section = out.split("## A.8.15", 1)[1]
    assert "[evidence: aws/cloudtrail-status-org-trail.json#IsLogging]" in section
    assert "support every check mapped to this topic" in section
    prose = [line for line in section.splitlines() if line.startswith("For the check")][0]
    for sentence in re.split(r"(?<=\.)\s+(?=[A-Z])", prose):
        assert "[evidence:" in sentence, sentence


def test_contradicted_control_names_the_failing_value():
    out = draft("--control", "A.8.12")
    assert "contradicts a check mapped to this topic" in out
    assert "records security_and_analysis.secret_scanning_push_protection.status as `disabled`" in out
    assert 'where the mapping expects `equals "enabled"`' in out


def test_not_assessable_control_lists_open_items_without_claims():
    out = draft("--control", "A.8.16")
    assert "not assessable from the exports in this pack alone" in out
    assert "- Not assessable from this pack: aws-guardduty" in out
    assert "support" not in out.split("## A.8.16", 1)[1]


def test_draft_starts_with_the_disclaimer_and_paraphrase_note():
    out = draft("--all")
    head = out.split("## ", 1)[0]
    assert "Preparation for a human assessor" in head and "not the framework's text" in head
    assert out.count("\n## ") == 17


def test_drafts_pass_the_linter(tmp_path):
    md = tmp_path / "n.md"
    rc, _, _ = run_main(mod, [str(CMAP), "--all", "--out", str(md)])
    assert rc == 0
    rc, out = run_json(lint, [str(md), str(CMAP), "--json"])
    assert rc == 0, out["problems"]


def test_unknown_control_is_bad_input():
    rc, _, err = run_main(mod, [str(CMAP), "--control", "A.99.1"])
    assert rc == 2 and "not in the control map" in err


def test_not_a_control_map_is_bad_input(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"rows": []}), encoding="utf-8")
    rc, _, err = run_main(mod, [str(p), "--all"])
    assert rc == 2 and "not a control map" in err


def test_redact_and_json(tmp_path):
    cm = json.loads(CMAP.read_text(encoding="utf-8"))
    cm["controls"][0]["gaps"] = ["owner jane.doe@example.com did not export"]
    p = tmp_path / "cm.json"
    p.write_text(json.dumps(cm), encoding="utf-8")
    rc, out = run_json(mod, [str(p), "--all", "--json", "--redact"])
    assert rc == 0 and "jane.doe@example.com" not in out["markdown"] and "@redacted.invalid" in out["markdown"]
    assert out["disclaimer"].startswith("Preparation for a human assessor")


def test_backticks_in_values_cannot_break_out_of_code():
    assert mod.code("a`b\nc") == "`a'b c`"
