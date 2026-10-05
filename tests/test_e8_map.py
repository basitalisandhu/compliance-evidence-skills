"""Tests for essential-eight-evidence-map/scripts/e8_map.py. Every pack and mapping is synthetic and built here."""

from __future__ import annotations

import csv
import hashlib
import json

import pytest
from conftest import SKILLS, load_script, run_json, run_main

mod = load_script("essential-eight-evidence-map", "e8_map.py")
CATALOGUE = SKILLS / "essential-eight-evidence-map" / "references" / "e8-requirements-2023-11.json"
BASE = ["--as-of", "2026-10-05", "--json"]


def make_pack(root, files, tamper=None, drop=None):
    pack = root / "pack"
    entries = []
    for rel, (content, collected) in files.items():
        p = pack / "evidence" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        entries.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "collected_at": collected,
                "command": f"export of {rel}",
                "collector": "jane.doe@example.com",
            }
        )
    (pack / "manifest.json").write_text(
        json.dumps({"schema": "compliance-evidence-pack/1", "mode": "copy", "built_at": "2026-10-02T00:00:00Z", "files": entries}), encoding="utf-8"
    )
    if tamper:
        (pack / "evidence" / tamper).write_text("changed", encoding="utf-8")
    if drop:
        (pack / "evidence" / drop).unlink()
    return pack


@pytest.fixture
def pack(tmp_path):
    return make_pack(
        tmp_path,
        {
            "aws/backup-plans.json": ('{"plans": 2}', "2026-10-01T09:00:00Z"),
            "aws/backup-restore-test.md": ("Restore test passed", "2026-09-20T09:00:00Z"),
            "m365/conditional-access-mfa.json": ('{"state": "enabled"}', "2026-10-01T09:00:00Z"),
            "m365/intune-update-rings.json": ("{}", "2026-10-01T09:00:00Z"),
            "old/legacy-backup.json": ("{}", "2025-01-01T09:00:00Z"),
        },
    )


def write_map(tmp_path, rows):
    p = tmp_path / "map.csv"
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["requirement", "evidence", "state", "note"])
        w.writerows(rows)
    return p


def strategy(rep, code):
    return next(s for s in rep["strategies"] if s["code"] == code)


def req(rep, rid):
    return next(r for r in rep["requirements"] if r["id"] == rid)


def test_catalogue_matches_the_november_2023_model():
    doc = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    assert doc["version"] == "November 2023" and "Creative Commons Attribution 4.0" in doc["licence"]
    reqs = doc["requirements"]
    assert len({r["id"] for r in reqs}) == len(reqs)
    ml1 = {s["code"]: sum(1 for r in reqs if 1 in r["levels"] and r["id"].startswith(s["code"] + "-")) for s in doc["strategies"]}
    assert ml1 == {"PA": 9, "PO": 8, "MFA": 7, "RA": 7, "AC": 3, "OM": 4, "UH": 4, "RB": 6}
    assert all(r["levels"] == sorted(r["levels"]) and set(r["levels"]) <= {1, 2, 3} for r in reqs)


def test_claimable_level_and_states(tmp_path, pack):
    m = write_map(
        tmp_path,
        [
            ["RB-ML1-*", "aws/backup-plans.json", "", ""],
            ["RB-ML1-04", "aws/backup-restore-test.md", "", "quarterly restore test"],
            ["RB-ML2-*", "aws/backup-plans.json", "", ""],
            ["MFA-ML1-01", "m365/conditional-access-mfa.json", "supported", ""],
            ["MFA-ML1-07", "m365/conditional-access-mfa.json", "contradicted", "SMS still allowed"],
        ],
    )
    rc, rep = run_json(mod, [str(pack), "--map", str(m), *BASE])
    assert rc == 1  # most strategies are below ML1
    rb = strategy(rep, "RB")
    assert rb["claimable_level"] == 2 and rb["levels"]["ML1"]["supported"] == 6 and rb["levels"]["ML3"]["required"] == 11
    assert req(rep, "RB-ML1-04")["citations"] == ["[evidence: aws/backup-plans.json]", "[evidence: aws/backup-restore-test.md]"]
    assert req(rep, "MFA-ML1-01")["state"] == "supported"
    assert req(rep, "MFA-ML1-07")["state"] == "contradicted" and strategy(rep, "MFA")["claimable_level"] == 0
    assert req(rep, "PA-ML1-01")["state"] == "not assessable"


def test_unusable_evidence_is_not_assessable(tmp_path):
    pack = make_pack(
        tmp_path,
        {"aws/a.json": ("{}", "2026-10-01T00:00:00Z"), "aws/b.json": ("{}", "2026-10-01T00:00:00Z"), "aws/old.json": ("{}", "2025-01-01T00:00:00Z")},
        tamper="aws/a.json",
        drop="aws/b.json",
    )
    m = write_map(
        tmp_path,
        [
            ["RB-ML1-01", "aws/a.json", "", ""],
            ["RB-ML1-02", "aws/b.json", "", ""],
            ["RB-ML1-03", "aws/old.json", "", ""],
            ["RB-ML1-05", "aws/not-listed.json", "", ""],
        ],
    )
    _, rep = run_json(mod, [str(pack), "--map", str(m), "--max-age-days", "180", *BASE])
    gaps = rep["unusable_evidence"]
    assert gaps["aws/a.json"] == "SHA-256 does not match the manifest"
    assert gaps["aws/b.json"] == "listed in the manifest but missing from the pack"
    assert gaps["aws/old.json"].startswith("collected more than 180 days")
    assert gaps["aws/not-listed.json"] == "not in the manifest"
    assert {req(rep, f"RB-ML1-0{i}")["state"] for i in (1, 2, 3, 5)} == {"not assessable"}


def test_target_met_exits_0_with_json_map(tmp_path, pack):
    doc = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    mapping = {r["id"]: ["aws/backup-plans.json"] for r in doc["requirements"] if 1 in r["levels"]}
    m = tmp_path / "map.json"
    m.write_text(json.dumps(mapping), encoding="utf-8")
    rc, rep = run_json(mod, [str(pack), "--map", str(m), *BASE])
    assert rc == 0
    # In the November 2023 model, Patch operating systems lists the same requirements at ML2 as at ML1.
    assert {s["code"]: s["claimable_level"] for s in rep["strategies"]} == {"PA": 1, "PO": 2, "MFA": 1, "RA": 1, "AC": 1, "OM": 1, "UH": 1, "RB": 1}
    rc, _ = run_json(mod, [str(pack), "--map", str(m), "--target", "2", *BASE])
    assert rc == 1


def test_candidates_are_listed_but_not_counted(tmp_path, pack):
    rc, rep = run_json(mod, [str(pack), *BASE])
    assert rc == 1
    assert "m365/conditional-access-mfa.json" in strategy(rep, "MFA")["candidates"]
    assert "aws/backup-plans.json" in strategy(rep, "RB")["candidates"]
    assert all(s["claimable_level"] == 0 for s in rep["strategies"])


def test_markdown_csv_out_and_redact(tmp_path, pack):
    m = write_map(tmp_path, [["RB-ML1-*", "aws/backup-plans.json", "", "owner jane.doe@example.com"]])
    out, sheet = tmp_path / "e8.md", tmp_path / "e8.csv"
    rc, printed, _ = run_main(mod, [str(pack), "--map", str(m), "--as-of", "2026-10-05", "--out", str(out), "--csv", str(sheet), "--redact"])
    md = out.read_text(encoding="utf-8")
    assert rc == 1 and printed == ""
    assert "| Regular backups | 6/6 | 6/8 | 5/11 | ML1 |" in md
    assert "November 2023" in md and "Preparation for a human assessor" in md
    with sheet.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 153 and rows[0]["requirement"] == "PA-ML1-01"
    _, js, _ = run_main(mod, [str(pack), "--map", str(m), "--json", "--redact"])
    assert "jane.doe@example.com" not in js and "@redacted.invalid" in js


@pytest.mark.parametrize(
    "rows,extra",
    [
        ([["XX-ML1-01", "aws/backup-plans.json", "", ""]], []),
        ([["RB-ML1-01", "aws/backup-plans.json", "maybe", ""]], []),
        ([["RB-ML1-01", "", "", ""]], []),
        ([], ["--max-age-days", "-1"]),
        ([], ["--as-of", "yesterday"]),
    ],
)
def test_bad_input_exits_2(tmp_path, pack, rows, extra):
    m = write_map(tmp_path, rows)
    rc, _, err = run_main(mod, [str(pack), "--map", str(m), *extra])
    assert rc == 2 and err.startswith("error:")


def test_pack_without_manifest_exits_2_and_help(tmp_path):
    rc, _, err = run_main(mod, [str(tmp_path)])
    assert rc == 2 and "no manifest.json" in err
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "November 2023" in out and "Exit codes" in out and "--redact" in out and "not assessable" in out
