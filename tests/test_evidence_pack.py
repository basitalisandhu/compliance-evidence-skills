"""Tests for evidence-pack-builder/scripts/evidence_pack.py: build, sidecar, verify and expire."""
import json
import os
import shutil

from conftest import AS_OF, FIXTURES, load_script, run_json, run_main

mod = load_script("evidence-pack-builder", "evidence_pack.py")
EXPORTS = FIXTURES / "exports"
TAMPERED = FIXTURES / "evidence-pack" / "tampered-pack"


def manifest(pack):
    return json.loads((pack / "manifest.json").read_text())


def test_build_writes_manifest_and_markdown(pack):
    m = manifest(pack)
    assert m["schema"] == "compliance-evidence-pack/1"
    assert m["file_count"] == 17 and len(m["files"]) == 17
    assert (pack / "MANIFEST.md").read_text().startswith("# Evidence pack manifest")
    assert "evidence-sources.json" not in {f["path"] for f in m["files"]}, "the sidecar is provenance, not evidence"
    assert m["disclaimer"].startswith("Preparation for a human assessor")


def test_build_hashes_match_the_copied_files(pack):
    ev = load_script("evidence-pack-builder", "_evidence.py")
    for f in manifest(pack)["files"]:
        assert ev.sha256_file(pack / "evidence" / f["path"]) == f["sha256"]
        assert ev.sha256_file(EXPORTS / f["path"]) == f["sha256"]


def test_build_records_provenance_from_the_sidecar(pack):
    files = {f["path"]: f for f in manifest(pack)["files"]}
    bp = files["github/branch-protection.json"]
    assert bp["command"] == "gh api repos/example-org/payments-api/branches/main/protection"
    assert bp["collector"] == "jane.doe@example.com" and bp["source_system"] == "github"
    assert bp["collected_at"] == "2026-10-01T09:30:00Z" and bp["date_basis"] == "sidecar"
    assert files["github/pulls-merged.json"]["collected_at"] == "2026-10-01T09:35:00Z"


def test_build_lists_a_file_without_a_command_as_a_gap(pack):
    m = manifest(pack)
    intune = next(f for f in m["files"] if f["path"] == "m365/intune-compliance-policies.json")
    assert intune["command"] == "" and intune["source_system"] == "m365"
    assert any(g.startswith("m365/intune-compliance-policies.json: no export command") for g in m["gaps"])
    assert len(m["gaps"]) == 1


def test_build_prints_the_manifest_hash(tmp_path):
    rc, out = run_json(mod, ["build", str(EXPORTS), "--out", str(tmp_path / "p"), "--as-of", AS_OF, "--json"])
    assert rc == 0
    ev = load_script("evidence-pack-builder", "_evidence.py")
    assert out["manifest_sha256"] == ev.sha256_file(tmp_path / "p" / "manifest.json")


def test_build_refuses_a_non_empty_or_nested_output(tmp_path):
    (tmp_path / "busy").mkdir()
    (tmp_path / "busy" / "x").write_text("x")
    rc, _, err = run_main(mod, ["build", str(EXPORTS), "--out", str(tmp_path / "busy")])
    assert rc == 2 and "not empty" in err
    work = tmp_path / "exports"
    shutil.copytree(EXPORTS, work)
    rc, _, err = run_main(mod, ["build", str(work), "--out", str(work / "pack")])
    assert rc == 2 and "outside" in err


def test_build_rejects_unknown_sidecar_keys(tmp_path):
    work = tmp_path / "exports"
    shutil.copytree(EXPORTS, work)
    side = json.loads((work / "evidence-sources.json").read_text())
    side["files"]["github/repo.json"]["approved_by_auditor"] = True
    (work / "evidence-sources.json").write_text(json.dumps(side))
    rc, _, err = run_main(mod, ["build", str(work), "--out", str(tmp_path / "p")])
    assert rc == 2 and "approved_by_auditor" in err


def test_build_without_sidecar_dates_by_file_time_and_records_gaps(tmp_path):
    work = tmp_path / "exports"
    shutil.copytree(EXPORTS, work)
    (work / "evidence-sources.json").unlink()
    rc, _, _ = run_main(mod, ["build", str(work), "--out", str(tmp_path / "p")])
    assert rc == 0
    m = manifest(tmp_path / "p")
    assert all(f["date_basis"] == "file modification time" for f in m["files"])
    assert sum("no collector recorded" in g for g in m["gaps"]) == 17


def test_build_skips_symlinks(tmp_path):
    work = tmp_path / "exports"
    shutil.copytree(EXPORTS, work)
    os.symlink("/etc/hosts", work / "aws" / "outside.json")
    rc, _, _ = run_main(mod, ["build", str(work), "--out", str(tmp_path / "p")])
    assert rc == 0
    m = manifest(tmp_path / "p")
    assert "aws/outside.json" not in {f["path"] for f in m["files"]}
    assert any("symbolic link skipped" in g for g in m["gaps"])


def test_build_empty_folder_is_bad_input(tmp_path):
    (tmp_path / "empty").mkdir()
    rc, _, err = run_main(mod, ["build", str(tmp_path / "empty"), "--out", str(tmp_path / "p")])
    assert rc == 2 and "no files" in err


def test_redacted_build_keeps_paths_and_hashes(tmp_path):
    rc, _, _ = run_main(mod, ["build", str(EXPORTS), "--out", str(tmp_path / "p"), "--redact"])
    assert rc == 0
    text = (tmp_path / "p" / "manifest.json").read_text()
    assert "jane.doe@example.com" not in text and "@redacted.invalid" in text
    rc, out = run_json(mod, ["verify", str(tmp_path / "p"), "--json"])
    assert rc == 0 and out["ok"]


def test_reference_mode_does_not_copy(tmp_path):
    rc, _, _ = run_main(mod, ["build", str(EXPORTS), "--out", str(tmp_path / "p"), "--mode", "reference"])
    assert rc == 0
    assert not (tmp_path / "p" / "evidence").exists()
    m = manifest(tmp_path / "p")
    assert m["mode"] == "reference" and m["source_root"] == str(EXPORTS.resolve())
    rc, out = run_json(mod, ["verify", str(tmp_path / "p"), "--json"])
    assert rc == 0 and out["checked"] == 17


def test_verify_clean_pack(pack):
    rc, out = run_json(mod, ["verify", str(pack), "--json"])
    assert rc == 0 and out["ok"] and out["problems"] == []


def test_verify_detects_the_planted_modified_file():
    rc, out = run_json(mod, ["verify", str(TAMPERED), "--json"])
    assert rc == 1 and not out["ok"]
    assert [(p["path"], p["status"]) for p in out["problems"]] == [("aws/password-policy.json", "modified")]


def test_verify_markdown_says_failed():
    rc, out, _ = run_main(mod, ["verify", str(TAMPERED)])
    assert rc == 1 and "MODIFIED" in out and "Result: FAILED" in out


def test_verify_detects_missing_and_unexpected_files(pack):
    (pack / "evidence" / "github" / "codeowners.json").unlink()
    (pack / "evidence" / "github" / "added-later.json").write_text("{}")
    rc, out = run_json(mod, ["verify", str(pack), "--json"])
    assert rc == 1
    assert {(p["path"], p["status"]) for p in out["problems"]} == {("github/codeowners.json", "missing"),
                                                                  ("github/added-later.json", "unexpected")}


def test_verify_checks_the_manifest_hash(pack):
    ev = load_script("evidence-pack-builder", "_evidence.py")
    good = ev.sha256_file(pack / "manifest.json")
    rc, out = run_json(mod, ["verify", str(pack), "--manifest-sha256", good, "--json"])
    assert rc == 0 and out["manifest_check"]["ok"]
    rc, out = run_json(mod, ["verify", str(pack), "--manifest-sha256", "0" * 64, "--json"])
    assert rc == 1 and not out["manifest_check"]["ok"]


def test_verify_rejects_a_folder_without_manifest(tmp_path):
    rc, _, err = run_main(mod, ["verify", str(tmp_path)])
    assert rc == 2 and "no manifest.json" in err


def test_expire_flags_old_evidence(pack):
    rc, out = run_json(mod, ["expire", str(pack), "--days", "30", "--as-of", AS_OF, "--json"])
    assert rc == 0 and out["flagged"] == []
    rc, out = run_json(mod, ["expire", str(pack), "--days", "30", "--as-of", "2026-12-01", "--json"])
    assert rc == 1
    flagged = {f["path"] for f in out["flagged"]}
    assert "github/repo.json" in flagged and all(f["age_days"] == 60 for f in out["files"] if f["path"] == "github/repo.json")


def test_expire_per_source_limit(pack):
    rc, out = run_json(mod, ["expire", str(pack), "--days", "365", "--max-age", "github=2", "--as-of", AS_OF, "--json"])
    assert rc == 1
    sources = {f["source_system"] for f in out["flagged"]}
    assert sources == {"github"}
    rc, _, err = run_main(mod, ["expire", str(pack), "--days", "30", "--max-age", "github"])
    assert rc == 2 and "SOURCE=DAYS" in err


def test_sidecar_skeleton_lists_every_file_and_refuses_to_overwrite(tmp_path):
    work = tmp_path / "exports"
    shutil.copytree(EXPORTS, work)
    (work / "evidence-sources.json").unlink()
    rc, _, _ = run_main(mod, ["sidecar", str(work)])
    assert rc == 0
    side = json.loads((work / "evidence-sources.json").read_text())
    assert len(side["files"]) == 17 and side["files"]["aws/password-policy.json"] == {"source_system": "aws", "command": ""}
    rc, _, err = run_main(mod, ["sidecar", str(work)])
    assert rc == 2 and "already exists" in err
