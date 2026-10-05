"""Tests for control-map-from-exports/scripts/control_map.py with the starter map and hand-written maps."""
import json

import pytest
from conftest import AS_OF, FIXTURES, STARTER_MAP, load_script, run_json, run_main

mod = load_script("control-map-from-exports", "control_map.py")
TAMPERED = FIXTURES / "evidence-pack" / "tampered-pack"


def cmap(pack, framework="iso27001", *extra, map_path=STARTER_MAP):
    rc, out = run_json(mod, [str(pack), "--framework", framework, "--map", str(map_path), "--as-of", AS_OF, "--json", *extra])
    return rc, out


def by_id(report):
    return {c["id"]: c for c in report["controls"]}


def test_starter_map_states_on_the_mixed_exports(pack):
    rc, out = cmap(pack)
    assert rc == 0
    c = by_id(out)
    assert c["A.8.15"]["state"] == "supported"
    assert c["A.8.32"]["state"] == "supported"
    assert c["A.8.12"]["state"] == "contradicted"   # planted: push protection disabled
    assert c["A.5.17"]["state"] == "contradicted"   # planted: 8-character password policy
    assert c["A.8.5"]["state"] == "contradicted"    # planted: legacy-auth block only in report-only mode
    assert c["A.8.16"]["state"] == "not assessable"  # GuardDuty export absent
    assert c["A.8.13"]["state"] == "not assessable"  # no AWS Backup plan: a gap, not a contradiction
    assert c["A.5.1"]["state"] == "not assessable" and c["A.5.1"]["checks"] == []


def test_supported_and_contradicted_controls_always_cite_file_field_and_hash(pack):
    _, out = cmap(pack)
    for c in out["controls"]:
        if c["state"] != "not assessable":
            assert c["citations"], c["id"]
            for cite in c["citations"]:
                assert cite["file"] and cite["field"] and len(cite["sha256"]) == 64


def test_any_of_supports_through_conditional_access_when_security_defaults_are_off(pack):
    _, out = cmap(pack)
    a85 = by_id(out)["A.8.5"]
    mfa = next(ch for ch in a85["checks"] if ch["id"] == "m365-mfa-everyone")
    assert mfa["state"] == "supported"
    assert mfa["citations"][0]["file"] == "m365/conditional-access-policies.json"
    legacy = next(ch for ch in a85["checks"] if ch["id"] == "m365-legacy-auth-blocked")
    assert legacy["state"] == "contradicted"


def test_soc2_framework_uses_soc2_identifiers(pack):
    rc, out = cmap(pack, "soc2")
    assert rc == 0 and out["framework"] == "soc2"
    c = by_id(out)
    assert set(c) == {"CC1.4", "CC6.1", "CC6.2", "CC6.3", "CC6.6", "CC6.8", "CC7.1", "CC7.2", "CC8.1", "A1.2"}
    assert c["CC8.1"]["state"] == "supported" and c["CC6.1"]["state"] == "contradicted"
    assert c["CC6.2"]["state"] == "not assessable"


def test_tampered_file_is_not_assessable_never_supported():
    _, out = cmap(TAMPERED)
    a517 = by_id(out)["A.5.17"]
    pw = next(ch for ch in a517["checks"] if ch["id"] == "aws-password-policy-length")
    assert pw["state"] == "not assessable"
    assert "SHA-256 does not match" in pw["gaps"][0]


def test_unmapped_files_are_listed(pack):
    _, out = cmap(pack)
    assert out["unmapped_files"] == ["github/dependabot-alerts.json"]


def test_max_age_days_makes_old_evidence_not_assessable(pack):
    _, out = cmap(pack, "iso27001", "--max-age-days", "2")
    assert all(c["state"] == "not assessable" for c in out["controls"])
    assert any("over the 2-day limit" in g for c in out["controls"] for g in c["gaps"])


def test_fail_on_contradicted_exits_1(pack):
    rc, _, _ = run_main(mod, [str(pack), "--framework", "iso27001", "--map", str(STARTER_MAP), "--fail-on", "contradicted"])
    assert rc == 1


def test_markdown_carries_the_disclaimer_and_rule(pack):
    rc, out, _ = run_main(mod, [str(pack), "--framework", "iso27001", "--map", str(STARTER_MAP), "--as-of", AS_OF])
    assert rc == 0
    assert "Preparation for a human assessor" in out and "supported only when every mapped check" in out
    assert "| A.8.16 | Systems are watched for unusual or hostile activity | not assessable |" in out


def test_out_file_is_written(pack, tmp_path):
    out_file = tmp_path / "cm.json"
    rc, _, _ = run_main(mod, [str(pack), "--framework", "iso27001", "--map", str(STARTER_MAP), "--out", str(out_file)])
    assert rc == 0 and json.loads(out_file.read_text(encoding="utf-8"))["framework"] == "iso27001"


def test_redact_tokenises_emails_in_citations(tmp_path, write):
    pk = _mini_pack(tmp_path, {"m365/owners.json": {"value": [{"mail": "owner@example.com"}]}})
    m = write("m.yaml", "controls:\n  iso27001: {A.5.18: \"Access is granted on purpose\"}\nchecks:\n"
                        "  - id: owners\n    iso27001: [A.5.18]\n    evidence: m365/owners.json\n    field: value[].mail\n"
                        "    expect: {exists: true}\n")
    _, out = run_json(mod, [str(pk), "--framework", "iso27001", "--map", str(m), "--json", "--redact"])
    assert "owner@example.com" not in json.dumps(out) and out["redacted"]


# ---- hand-written packs and maps --------------------------------------------------------------------------------

def _mini_pack(tmp_path, files: dict, raw: dict | None = None):
    pk = load_script("evidence-pack-builder", "evidence_pack.py")
    src = tmp_path / "src"
    for rel, data in files.items():
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding="utf-8")
    for rel, text in (raw or {}).items():
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    rc, _, err = run_main(pk, ["build", str(src), "--out", str(tmp_path / "pack")])
    assert rc == 0, err
    return tmp_path / "pack"


ONE_CHECK = """controls:
  iso27001:
    A.5.17: "Secrets handled with care"
checks:
  - id: pw
    iso27001: [A.5.17]
    evidence: aws/password-policy.json
    field: PasswordPolicy.MinimumPasswordLength
    expect: {gte: 14}
    absent_when: ["NoSuchEntity"]
"""


def test_err_file_with_absent_marker_is_contradicted(tmp_path, write):
    pk = _mini_pack(tmp_path, {}, {"aws/password-policy.json": "", "aws/password-policy.err":
                                   "An error occurred (NoSuchEntity) when calling the GetAccountPasswordPolicy operation"})
    _, out = run_json(mod, [str(pk), "--framework", "iso27001", "--map", str(write("m.yaml", ONE_CHECK)), "--json"])
    c = by_id(out)["A.5.17"]
    assert c["state"] == "contradicted" and c["citations"][0]["file"] == "aws/password-policy.err"


def test_err_file_with_access_denied_is_not_assessable(tmp_path, write):
    pk = _mini_pack(tmp_path, {}, {"aws/password-policy.json": "", "aws/password-policy.err":
                                   "An error occurred (AccessDenied) when calling the GetAccountPasswordPolicy operation"})
    _, out = run_json(mod, [str(pk), "--framework", "iso27001", "--map", str(write("m.yaml", ONE_CHECK)), "--json"])
    assert by_id(out)["A.5.17"]["state"] == "not assessable"


def test_github_403_body_is_not_assessable_even_with_absent_when(tmp_path, write):
    pk = _mini_pack(tmp_path, {"github/branch-protection.json": {"message": "Upgrade to GitHub Pro", "documentation_url": "x", "status": "403"}})
    m = write("m.yaml", 'controls:\n  iso27001: {A.8.32: "Reviewed changes"}\nchecks:\n  - id: bp\n    iso27001: [A.8.32]\n'
                        '    evidence: github/branch-protection.json\n    field: url\n    expect: {exists: true}\n'
                        '    absent_when: ["Upgrade"]\n')
    _, out = run_json(mod, [str(pk), "--framework", "iso27001", "--map", str(m), "--json"])
    c = by_id(out)["A.8.32"]
    assert c["state"] == "not assessable" and "could not see" in c["gaps"][0]


def test_http_status_files(tmp_path, write):
    m = write("m.yaml", 'controls:\n  iso27001: {A.8.8: "Weaknesses fixed"}\nchecks:\n  - id: va\n    iso27001: [A.8.8]\n'
                        '    evidence: github/vulnerability-alerts.http\n    field: status\n    expect: {equals: 204}\n')
    for status, state in (("204 No Content", "supported"), ("404 Not Found", "contradicted"), ("403 Forbidden", "not assessable")):
        sub = tmp_path / status.split()[0]
        pk = _mini_pack(sub, {}, {"github/vulnerability-alerts.http": f"HTTP/2.0 {status}\nServer: example\n\n"})
        _, out = run_json(mod, [str(pk), "--framework", "iso27001", "--map", str(m), "--json"])
        assert by_id(out)["A.8.8"]["state"] == state, status


def test_csv_where_and_count(tmp_path, write):
    csv_text = "user,password_enabled,mfa_active\n<root_account>,not_supported,true\nalice,true,false\nbob,true,true\n"
    pk = _mini_pack(tmp_path, {}, {"aws/credential-report.csv": csv_text})
    m = write("m.yaml", 'controls:\n  iso27001: {A.8.5: "Strong sign-in"}\nchecks:\n  - id: mfa\n    iso27001: [A.8.5]\n'
                        '    evidence: aws/credential-report.csv\n    field: "[]"\n    where:\n      password_enabled: {equals: "true"}\n'
                        '      mfa_active: {equals: "false"}\n    expect: {count_lte: 0}\n')
    _, out = run_json(mod, [str(pk), "--framework", "iso27001", "--map", str(m), "--json"])
    c = by_id(out)["A.8.5"]
    assert c["state"] == "contradicted" and c["citations"][0]["value"].startswith("1 of 3 entries match")


def test_missing_field_is_not_assessable(tmp_path, write):
    pk = _mini_pack(tmp_path, {"aws/password-policy.json": {"Something": 1}})
    _, out = run_json(mod, [str(pk), "--framework", "iso27001", "--map", str(write("m.yaml", ONE_CHECK)), "--json"])
    c = by_id(out)["A.5.17"]
    assert c["state"] == "not assessable" and "not found in the export" in c["gaps"][0]


def test_boolean_is_not_a_number(tmp_path, write):
    pk = _mini_pack(tmp_path, {"a.json": {"flag": True}})
    m = write("m.yaml", 'controls:\n  iso27001: {A.8.9: "Settings recorded"}\nchecks:\n  - id: b\n    iso27001: [A.8.9]\n'
                        '    evidence: a.json\n    field: flag\n    expect: {equals: 1}\n')
    _, out = run_json(mod, [str(pk), "--framework", "iso27001", "--map", str(m), "--json"])
    assert by_id(out)["A.8.9"]["state"] == "contradicted"


def test_not_a_pack_is_bad_input(tmp_path):
    rc, _, err = run_main(mod, [str(tmp_path), "--framework", "iso27001", "--map", str(STARTER_MAP)])
    assert rc == 2 and "manifest.json" in err


@pytest.mark.parametrize("bad,message", [
    ('controls:\n  iso27001: {A.5.1: "' + "word " * 25 + '"}\nchecks: []\n', "over 20 words"),
    ('controls:\n  iso27001: {A.5.1: "Policies"}\nchecks:\n  - id: x\n    iso27001: [A.5.2]\n    evidence: a.json\n'
     '    field: f\n    expect: {gte: 1}\n', "has no paraphrase"),
    ('controls:\n  iso27001: {A.5.1: "Policies"}\nchecks:\n  - id: x\n    iso27001: [A.5.1]\n    evidence: a.json\n'
     '    field: f\n    expect: {roughly: 1}\n', "unknown operator"),
    ('controls:\n  iso27001: {A.5.1: "Policies"}\nchecks:\n  - id: x\n    iso27001: [A.5.1]\n    evidence: ../a.json\n'
     '    field: f\n    expect: {gte: 1}\n', "relative path"),
    ('controls:\n  nist: {X.1: "Other"}\nchecks: []\n', "controls must map"),
    ('controls:\n  iso27001: {A.5.1: "Policies"}\nchecks:\n  - id: x\n    iso27001: [A.5.1]\n    evidence: a.json\n'
     '    field: f\n    expect: {gte: 1}\n    on_fail: passed\n', "on_fail"),
])
def test_bad_maps_are_rejected(tmp_path, write, bad, message):
    pk = _mini_pack(tmp_path, {"a.json": {"f": 1}})
    rc, _, err = run_main(mod, [str(pk), "--framework", "iso27001", "--map", str(write("bad.yaml", bad))])
    assert rc == 2 and message in err
