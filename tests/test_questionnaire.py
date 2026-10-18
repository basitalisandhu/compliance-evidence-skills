"""Tests for security-questionnaire-drafter/scripts/questionnaire.py. Every input is synthetic and built here."""

from __future__ import annotations

import csv
import hashlib
import json

import pytest
from conftest import load_script, run_json, run_main

mod = load_script("security-questionnaire-drafter", "questionnaire.py")

POLICY = """# Access Control Policy

## Multi-factor authentication
All staff sign in with multi-factor authentication through the identity provider. Exceptions need written approval.

## Leavers
Accounts are disabled on the last working day.
"""
BACKUP = "Backups of production databases run nightly and are kept for 35 days. Restores are tested each quarter.\n"


def make_pack(root, files, tamper=None):
    pack = root / "pack"
    entries = []
    for rel, (content, command) in files.items():
        p = pack / "evidence" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        entries.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "command": command,
                "source_system": rel.split("/")[0],
                "collected_at": "2026-10-01T09:30:00Z",
                "collector": "jane.doe@example.com",
            }
        )
    (pack / "manifest.json").write_text(json.dumps({"schema": "compliance-evidence-pack/1", "mode": "copy", "files": entries}), encoding="utf-8")
    if tamper:
        (pack / "evidence" / tamper).write_text("changed", encoding="utf-8")
    return pack


@pytest.fixture
def sources(tmp_path):
    pol = tmp_path / "policies"
    pol.mkdir()
    (pol / "access-control.md").write_text(POLICY, encoding="utf-8")
    (pol / "backup.txt").write_text(BACKUP, encoding="utf-8")
    pack = make_pack(
        tmp_path,
        {
            "m365/conditional-access-mfa.json": ('{"state": "enabled"}', "mgc identity conditional-access policies list --output json"),
            "aws/backup-plans.json": ('{"BackupPlansList": []}', "aws backup list-backup-plans --output json"),
        },
    )
    return pol, pack


def questionnaire(tmp_path, rows):
    p = tmp_path / "q.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ID", "Question", "Answer"])
        w.writerows(rows)
    return p


def by_id(rep):
    return {a["id"]: a for a in rep["answers"]}


def test_answers_cite_policy_and_evidence(tmp_path, sources):
    pol, pack = sources
    q = questionnaire(
        tmp_path,
        [
            ["1.1", "Do you enforce multi-factor authentication (MFA) for all users?", ""],
            ["1.2", "How often are backups taken and restores tested?", ""],
        ],
    )
    rc, rep = run_json(mod, [str(q), "--policies", str(pol), "--evidence", str(pack), "--json"])
    assert rc == 0
    mfa, backup = by_id(rep)["1.1"], by_id(rep)["1.2"]
    assert mfa["state"] == "supported" and mfa["basis"] == "policy and evidence"
    assert "[policy: access-control.md#Multi-factor authentication]" in mfa["citations"]
    assert "[evidence: m365/conditional-access-mfa.json]" in mfa["citations"]
    assert "collected 2026-10-01" in mfa["draft_answer"]
    assert "[policy: backup.txt#backup]" in backup["citations"] and "[evidence: aws/backup-plans.json]" in backup["citations"]


def test_unmatched_question_is_not_assessable_and_exits_1(tmp_path, sources):
    pol, pack = sources
    q = questionnaire(tmp_path, [["2.1", "Is your data centre certified for physical security of the building?", ""]])
    rc, rep = run_json(mod, [str(q), "--policies", str(pol), "--evidence", str(pack), "--json"])
    assert rc == 1
    ans = by_id(rep)["2.1"]
    assert ans["state"] == "not assessable" and ans["citations"] == []
    assert "do not answer from memory" in ans["draft_answer"]
    rc, _ = run_json(mod, [str(q), "--policies", str(pol), "--json", "--fail-on", "none"])
    assert rc == 0


def test_tampered_evidence_is_never_cited(tmp_path):
    pack = make_pack(
        tmp_path,
        {"m365/mfa-registration.json": ("{}", "mgc reports authentication-methods user-registration-details list")},
        tamper="m365/mfa-registration.json",
    )
    q = questionnaire(tmp_path, [["3", "Is MFA required?", ""]])
    rc, rep = run_json(mod, [str(q), "--evidence", str(pack), "--json"])
    assert rc == 1 and rep["answers"][0]["state"] == "not assessable"
    assert any("SHA-256 does not match" in n for n in rep["notes"])


def test_control_map_states_carry_through(tmp_path):
    cmap = tmp_path / "control-map.json"
    cmap.write_text(
        json.dumps(
            {
                "controls": [
                    {
                        "id": "A.8.12",
                        "state": "contradicted",
                        "citations": [{"file": "github/repo.json", "field": "push_protection", "value": "disabled"}],
                        "gaps": ["secret scanning push protection is disabled"],
                    },
                    {
                        "id": "A.8.15",
                        "state": "supported",
                        "citations": [{"file": "aws/trail.json", "field": "IsLogging", "value": True}],
                        "gaps": [],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    q = questionnaire(tmp_path, [["4.1", "Describe data leakage prevention (A.8.12).", ""], ["4.2", "Is logging (A.8.15) in place?", ""]])
    rc, rep = run_json(mod, [str(q), "--control-map", str(cmap), "--json"])
    assert rc == 1
    assert by_id(rep)["4.1"]["state"] == "contradicted" and "push protection is disabled" in by_id(rep)["4.1"]["draft_answer"]
    assert by_id(rep)["4.2"]["citations"] == ["[evidence: aws/trail.json#IsLogging]"]
    rc, _ = run_json(mod, [str(q), "--control-map", str(cmap), "--json", "--fail-on", "contradicted"])
    assert rc == 1


def test_markdown_questionnaire_shapes(tmp_path, sources):
    pol, _ = sources
    table = tmp_path / "q.md"
    table.write_text("| # | Question |\n|---|---|\n| A1 | Is MFA enforced? |\n| A2 | Are leavers removed promptly? |\n", encoding="utf-8")
    _, rep = run_json(mod, [str(table), "--policies", str(pol), "--json", "--fail-on", "none"])
    assert [a["id"] for a in rep["answers"]] == ["A1", "A2"]
    listed = tmp_path / "list.md"
    listed.write_text("Intro text.\n\n1. Is MFA enforced?\n2. Are backups tested?\n", encoding="utf-8")
    _, rep = run_json(mod, [str(listed), "--policies", str(pol), "--json", "--fail-on", "none"])
    assert [a["id"] for a in rep["answers"]] == ["1", "2"] and rep["counts"]["supported"] == 2


def test_csv_out_and_redact(tmp_path, sources):
    pol, pack = sources
    (pol / "contacts.md").write_text("# Security contact\nReport multi-factor authentication issues to security@example.com.\n", encoding="utf-8")
    q = questionnaire(tmp_path, [["5", "Who do we contact about MFA problems?", ""]])
    out, sheet = tmp_path / "report.md", tmp_path / "answers.csv"
    rc, printed, _ = run_main(mod, [str(q), "--policies", str(pol), "--out", str(out), "--csv", str(sheet), "--redact"])
    assert rc == 0 and printed == ""
    text = out.read_text(encoding="utf-8") + sheet.read_text(encoding="utf-8")
    assert "security@example.com" not in text and "@redacted.invalid" in text
    with sheet.open(encoding="utf-8", newline="") as fh:
        row = next(csv.DictReader(fh))
    assert row["state"] == "supported" and row["owner"] == ""
    assert "Preparation for a human assessor" in out.read_text(encoding="utf-8")


def test_secret_shapes_are_masked(tmp_path):
    pol = tmp_path / "p"
    pol.mkdir()
    key = "AKIA" + "IOSFODNN7EXAMPLE"  # split so the repository secret scan does not match the test itself
    (pol / "keys.md").write_text(f"# Encryption keys\nThe old key {key} was rotated; encryption at rest uses KMS.\n", encoding="utf-8")
    q = questionnaire(tmp_path, [["6", "How are encryption keys managed?", ""]])
    _, out, _ = run_main(mod, [str(q), "--policies", str(pol)])
    assert key not in out and "[masked secret]" in out


@pytest.mark.parametrize(
    "content,suffix,extra",
    [
        ("ID,Answer\n1,yes\n", ".csv", []),
        ("", ".md", []),
        ("ID,Question\n1,Is MFA on?\n", ".csv", ["--min-score", "0"]),
    ],
)
def test_bad_input_exits_2(tmp_path, sources, content, suffix, extra):
    pol, _ = sources
    q = tmp_path / f"bad{suffix}"
    q.write_text(content, encoding="utf-8")
    rc, _, err = run_main(mod, [str(q), "--policies", str(pol), *extra])
    assert rc == 2 and err.startswith("error:")


def test_needs_a_source_and_help(tmp_path):
    q = questionnaire(tmp_path, [["1", "Is MFA on?", ""]])
    rc, _, err = run_main(mod, [str(q)])
    assert rc == 2 and "at least one of" in err
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "not assessable" in out and "Exit codes" in out and "--redact" in out


def test_semicolon_csv_in_windows_1252(tmp_path, sources):
    pol, pack = sources
    q = tmp_path / "q.csv"  # Excel in a European locale: ";" separated, Windows-1252 ("é" is one byte)
    q.write_bytes("ID;Question;Answer\nQ1;Do you enforce multi-factor authentication for all staff (accès)?;\n".encode("cp1252"))
    rc, rep = run_json(mod, [str(q), "--policies", str(pol), "--evidence", str(pack), "--json"])
    a = by_id(rep)["Q1"]
    assert a["question"].endswith("(accès)?") and a["state"] == "supported"


def test_utf16_unicode_text_export(tmp_path, sources):
    pol, _ = sources
    q = tmp_path / "q.tsv"
    q.write_bytes("ID\tQuestion\nQ7\tAre backups tested?\n".encode("utf-16"))
    _, rep = run_json(mod, [str(q), "--policies", str(pol), "--json"])
    assert by_id(rep)["Q7"]["question"] == "Are backups tested?"


def test_repeated_ids_never_collide_with_ids_in_the_file(tmp_path, sources):
    pol, _ = sources
    q = questionnaire(tmp_path, [["1", "Do you use MFA?", ""], ["1", "Are backups tested?", ""], ["1-2", "Do you log access?", ""]])
    _, rep = run_json(mod, [str(q), "--policies", str(pol), "--json"])
    assert [a["id"] for a in rep["answers"]] == ["1", "1-2", "1-2-2"]
    assert len({a["id"] for a in rep["answers"]}) == 3


def test_manifest_paths_outside_the_pack_are_not_cited(tmp_path, sources):
    pol, pack = sources
    outside = tmp_path / "secret-mfa-notes.json"
    outside.write_text("{}", encoding="utf-8")
    doc = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    doc["files"].append({"path": "../../secret-mfa-notes.json", "command": "mfa conditional-access", "sha256": ""})
    (pack / "manifest.json").write_text(json.dumps(doc), encoding="utf-8")
    q = questionnaire(tmp_path, [["1", "Do you enforce MFA through conditional access?", ""]])
    _, rep = run_json(mod, [str(q), "--evidence", str(pack), "--json"])
    assert any("outside the pack" in n for n in rep["notes"])
    assert not any("secret-mfa-notes" in c for c in json.dumps(rep["answers"]).split('"'))


def test_hidden_files_in_a_plain_folder_are_not_evidence(tmp_path):
    ev = tmp_path / "ev"
    (ev / ".git").mkdir(parents=True)
    (ev / ".git" / "mfa-config").write_text("x", encoding="utf-8")
    (ev / ".DS_Store").write_text("x", encoding="utf-8")
    (ev / "mfa-policy-export.json").write_text("{}", encoding="utf-8")
    q = questionnaire(tmp_path, [["1", "Do you enforce MFA?", ""]])
    _, rep = run_json(mod, [str(q), "--evidence", str(ev), "--json"])
    assert rep["sources"]["evidence_files"] == 1


def test_undecodable_questionnaire_exits_2(tmp_path, sources):
    pol, _ = sources
    q = tmp_path / "q.csv"
    q.write_bytes(b"ID,Question\n1,\x81\x8d\x8f\x90\x9d?\n")  # bytes Windows-1252 leaves undefined
    rc, _, err = run_main(mod, [str(q), "--policies", str(pol)])
    assert rc == 2 and "Windows-1252" in err


def test_fixture_questionnaire_from_the_skill_try_it_line():
    from conftest import FIXTURES

    d = FIXTURES / "questionnaire"
    rc, rep = run_json(mod, [str(d / "questionnaire.csv"), "--policies", str(d / "policies"), "--json"])
    states = {a["id"]: a["state"] for a in rep["answers"]}
    assert rc == 1 and states["Q1"] == "supported" and states["Q2"] == "supported" and states["Q4"] == "not assessable"
