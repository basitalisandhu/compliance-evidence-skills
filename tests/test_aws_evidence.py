"""Tests for aws-identity-and-logging-evidence/scripts/aws_evidence.py on saved aws CLI output."""
import json
import shutil

from conftest import AS_OF, FIXTURES, load_script, run_json, run_main

mod = load_script("aws-identity-and-logging-evidence", "aws_evidence.py")
AWS = FIXTURES / "aws"
CONFIG = AWS / "config.yaml"


def rows(folder, *extra):
    rc, out = run_json(mod, [str(folder), "--as-of", AS_OF, "--json", *extra])
    return rc, out, {r["check"]: r for r in out["rows"]}


def test_good_account_is_supported_everywhere():
    rc, out, r = rows(AWS / "good", "--config", str(CONFIG))
    assert rc == 0
    assert out["summary"] == {"supported": 12, "contradicted": 0, "not assessable": 0}
    assert out["regions"] == ["eu-west-1", "us-east-1"]
    assert all(row["citations"] for row in r.values())


def test_gaps_account_planted_problems():
    _, _, r = rows(AWS / "gaps", "--config", str(CONFIG))
    for check in ("AWS-CT-VALIDATION", "AWS-CT-LOGGING", "AWS-ROOT-MFA", "AWS-ROOT-ACCESS-KEYS", "AWS-CONSOLE-MFA",
                  "AWS-ACCESS-KEY-AGE", "AWS-PASSWORD-POLICY", "AWS-GUARDDUTY", "AWS-CONFIG-RECORDER", "AWS-S3-ACCOUNT-PAB"):
        assert r[check]["state"] == "contradicted", check
    assert r["AWS-CT-MULTI-REGION"]["state"] == "supported"


def test_console_users_without_mfa_are_named():
    _, _, r = rows(AWS / "gaps")
    value = r["AWS-CONSOLE-MFA"]["citations"][0]["value"]
    assert value.startswith("1 of 2") and "jane.doe" in value and "ops-admin" not in value


def test_old_keys_include_root_and_the_service_user():
    _, _, r = rows(AWS / "gaps")
    value = r["AWS-ACCESS-KEY-AGE"]["citations"][0]["value"]
    assert "legacy-sync key 1 (245 days)" in value and "<root_account> key 1" in value


def test_no_such_entity_cites_the_err_file():
    _, _, r = rows(AWS / "gaps")
    cite = r["AWS-PASSWORD-POLICY"]["citations"][0]
    assert cite["file"] == "password-policy.err" and "NoSuchEntity" in cite["value"]


def test_access_denied_region_is_a_gap_not_a_pass():
    _, _, r = rows(AWS / "gaps")
    gd = r["AWS-GUARDDUTY"]
    assert gd["state"] == "contradicted"  # us-east-1 has no detector
    assert any("ap-southeast-2" in g and "not allowed" in g for g in gd["gaps"])


def test_access_denied_alone_is_not_assessable(tmp_path):
    shutil.copytree(AWS / "gaps", tmp_path / "a")
    shutil.rmtree(tmp_path / "a" / "regions" / "us-east-1")
    _, _, r = rows(tmp_path / "a")
    assert r["AWS-GUARDDUTY"]["state"] == "not assessable"


def test_backup_without_plans_is_never_contradicted():
    _, _, r = rows(AWS / "gaps")
    row = r["AWS-BACKUP-PLANS"]
    assert row["state"] == "not assessable"
    assert any("another way" in g for g in row["gaps"])


def test_regions_in_scope_without_exports_are_gaps(tmp_path, write):
    cfg = write("c.yaml", "regions: [us-east-1, eu-west-1, ap-northeast-1]\n")
    _, _, r = rows(AWS / "good", "--config", str(cfg))
    assert r["AWS-GUARDDUTY"]["state"] == "not assessable"
    assert any("ap-northeast-1" in g for g in r["AWS-GUARDDUTY"]["gaps"])


def test_single_region_layout_in_the_folder_root(tmp_path):
    work = tmp_path / "a"
    shutil.copytree(AWS / "good", work)
    for f in (work / "regions" / "us-east-1").iterdir():
        shutil.move(str(f), work / f.name)
    shutil.rmtree(work / "regions")
    _, out, r = rows(work)
    assert out["regions"] == ["(folder root)"]
    assert r["AWS-GUARDDUTY"]["state"] == "supported" and r["AWS-BACKUP-PLANS"]["state"] == "supported"


def test_missing_trail_status_is_not_assessable(tmp_path):
    shutil.copytree(AWS / "good", tmp_path / "a")
    (tmp_path / "a" / "cloudtrail-status-org-trail.json").unlink()
    _, _, r = rows(tmp_path / "a")
    assert r["AWS-CT-LOGGING"]["state"] == "not assessable"


def test_root_falls_back_to_the_credential_report(tmp_path):
    shutil.copytree(AWS / "gaps", tmp_path / "a")
    (tmp_path / "a" / "account-summary.json").unlink()
    _, _, r = rows(tmp_path / "a")
    assert r["AWS-ROOT-MFA"]["state"] == "contradicted"
    assert r["AWS-ROOT-MFA"]["citations"][0]["file"] == "credential-report.csv"
    assert r["AWS-ROOT-ACCESS-KEYS"]["state"] == "contradicted"


def test_key_age_threshold_from_config(write):
    cfg = write("c.yaml", "max_key_age_days: 365\n")
    _, _, r = rows(AWS / "gaps", "--config", str(cfg))
    assert "1 of 2 active keys" in r["AWS-ACCESS-KEY-AGE"]["citations"][0]["value"]


def test_redact_removes_iam_user_names_and_arn_principals():
    rc, out = run_json(mod, [str(AWS / "gaps"), "--as-of", AS_OF, "--json", "--redact"])
    text = json.dumps(out)
    assert rc == 0 and "jane.doe" not in text and "legacy-sync" not in text and "audit-reader" not in text
    assert "123456789012" in text  # the account under assessment stays visible


def test_unknown_config_key_is_bad_input(write):
    rc, _, err = run_main(mod, [str(AWS / "good"), "--config", str(write("c.yaml", "max_key_age: 90\n"))])
    assert rc == 2 and "unknown config keys" in err


def test_markdown_has_disclaimer():
    rc, out, _ = run_main(mod, [str(AWS / "good"), "--as-of", AS_OF])
    assert rc == 0 and "Preparation for a human assessor" in out and "| supported | AWS-ROOT-MFA |" in out
