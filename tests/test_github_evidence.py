"""Tests for github-change-control-evidence/scripts/github_evidence.py on recorded gh exports."""
import json
import shutil

from conftest import AS_OF, FIXTURES, load_script, run_json, run_main

mod = load_script("github-change-control-evidence", "github_evidence.py")
GH = FIXTURES / "github"
CONFIG = GH / "config.yaml"


def rows(folder, *extra):
    rc, out = run_json(mod, [str(folder), "--as-of", AS_OF, "--json", *extra])
    return rc, out, {r["check"]: r for r in out["rows"]}


def test_protected_repository_is_supported_everywhere():
    rc, out, r = rows(GH / "protected", "--config", str(CONFIG))
    assert rc == 0
    assert out["summary"] == {"supported": 14, "contradicted": 0, "not assessable": 0}
    assert out["repository"] == "example-org/payments-api"
    for row in r.values():
        assert row["citations"] and all(c["file"] and c["field"] for c in row["citations"])


def test_weak_repository_planted_problems_are_contradicted():
    _, _, r = rows(GH / "weak", "--config", str(CONFIG))
    expected = {"GH-REQUIRED-REVIEWS", "GH-ADMINS-INCLUDED", "GH-STATUS-CHECKS", "GH-FORCE-PUSH-BLOCKED", "GH-PR-APPROVED",
                "GH-CODEOWNERS", "GH-SIGNED-COMMITS", "GH-DEPENDABOT-ALERTS", "GH-DEPENDABOT-UPDATES", "GH-SECRET-SCANNING",
                "GH-PUSH-PROTECTION", "GH-OPEN-VULN-ALERTS", "GH-OPEN-SECRET-ALERTS"}
    assert {k for k, v in r.items() if v["state"] == "contradicted"} == expected
    assert r["GH-BRANCH-PROTECTION"]["state"] == "supported"


def test_pr_population_names_the_unapproved_pull_requests():
    _, out, r = rows(GH / "weak", "--config", str(CONFIG))
    value = r["GH-PR-APPROVED"]["citations"][0]["value"]
    assert "2 of 3" in value and "#202" in value and "#203" in value and "#201" not in value
    assert out["population"]["merged_pull_requests"] == 3 and out["population"]["without_independent_approval"] == 2


def test_period_excludes_pull_requests_merged_before_it():
    _, out, r = rows(GH / "protected", "--config", str(CONFIG))
    assert out["population"]["merged_pull_requests"] == 3
    _, out, r = rows(GH / "protected")  # no period: the unreviewed June pull request counts
    assert r["GH-PR-APPROVED"]["state"] == "contradicted" and "#90" in r["GH-PR-APPROVED"]["citations"][0]["value"]


def test_self_approval_does_not_count(tmp_path):
    shutil.copytree(GH / "protected", tmp_path / "gh")
    prs = [{"number": 1, "author": {"login": "dev-alice"}, "mergedAt": "2026-08-01T10:00:00Z",
            "reviews": [{"author": {"login": "dev-alice"}, "state": "APPROVED"}]}]
    (tmp_path / "gh" / "pulls-merged.json").write_text(json.dumps(prs))
    _, _, r = rows(tmp_path / "gh")
    assert r["GH-PR-APPROVED"]["state"] == "contradicted"


def test_free_plan_403s_are_not_assessable_not_failures():
    _, _, r = rows(GH / "free-plan", "--config", str(CONFIG))
    for check in ("GH-BRANCH-PROTECTION", "GH-REQUIRED-REVIEWS", "GH-STATUS-CHECKS", "GH-FORCE-PUSH-BLOCKED", "GH-DEPENDABOT-ALERTS",
                  "GH-DEPENDABOT-UPDATES", "GH-SECRET-SCANNING", "GH-PUSH-PROTECTION", "GH-OPEN-VULN-ALERTS"):
        assert r[check]["state"] == "not assessable", check
    assert "refused" in r["GH-BRANCH-PROTECTION"]["gaps"][0]
    assert not any(row["state"] == "contradicted" for row in r.values())


def test_ruleset_only_branch_counts_as_protected():
    _, _, r = rows(GH / "ruleset-only")
    assert r["GH-BRANCH-PROTECTION"]["state"] == "supported"
    assert r["GH-REQUIRED-REVIEWS"]["state"] == "supported"
    assert r["GH-REQUIRED-REVIEWS"]["citations"][0]["value"] == 2
    assert r["GH-FORCE-PUSH-BLOCKED"]["state"] == "supported"
    assert r["GH-STATUS-CHECKS"]["state"] == "contradicted"
    assert r["GH-ADMINS-INCLUDED"]["state"] == "not assessable"


def test_branch_not_protected_without_rules_export_is_not_assessable(tmp_path):
    shutil.copytree(GH / "ruleset-only", tmp_path / "gh")
    (tmp_path / "gh" / "rules.json").unlink()
    _, _, r = rows(tmp_path / "gh")
    assert r["GH-BRANCH-PROTECTION"]["state"] == "not assessable"
    (tmp_path / "gh" / "rules.json").write_text("[]")
    _, _, r = rows(tmp_path / "gh")
    assert r["GH-BRANCH-PROTECTION"]["state"] == "contradicted"
    assert r["GH-REQUIRED-REVIEWS"]["state"] == "contradicted"


def test_slurped_alert_pages_are_flattened(tmp_path):
    shutil.copytree(GH / "weak", tmp_path / "gh")
    alerts = json.loads((GH / "weak" / "dependabot-alerts.json").read_text())
    (tmp_path / "gh" / "dependabot-alerts.json").write_text(json.dumps([alerts[:1], alerts[1:]]))
    _, _, r = rows(tmp_path / "gh")
    assert "1 overdue of 2 open" in r["GH-OPEN-VULN-ALERTS"]["citations"][0]["value"]


def test_limit_sized_export_gets_a_gap(tmp_path):
    shutil.copytree(GH / "protected", tmp_path / "gh")
    pr = {"number": 1, "author": {"login": "a"}, "mergedAt": "2026-08-01T10:00:00Z", "reviews": [{"author": {"login": "b"}, "state": "APPROVED"}]}
    (tmp_path / "gh" / "pulls-merged.json").write_text(json.dumps([dict(pr, number=i) for i in range(30)]))
    _, _, r = rows(tmp_path / "gh")
    assert r["GH-PR-APPROVED"]["state"] == "supported" and "exactly 30 entries" in r["GH-PR-APPROVED"]["gaps"][0]


def test_config_thresholds_change_the_result(tmp_path, write):
    cfg = write("c.yaml", "min_signed_ratio: 0.5\nmin_reviews: 2\n")
    _, _, r = rows(GH / "weak", "--config", str(cfg))
    assert r["GH-SIGNED-COMMITS"]["state"] == "supported"
    _, _, r = rows(GH / "protected", "--config", str(cfg))
    assert r["GH-REQUIRED-REVIEWS"]["state"] == "contradicted"


def test_cite_prefix_matches_pack_paths():
    _, _, r = rows(GH / "protected", "--cite-prefix", "github/")
    assert r["GH-CODEOWNERS"]["citations"][0]["file"] == "github/codeowners.json"


def test_redact_removes_logins_and_emails():
    rc, out = run_json(mod, [str(GH / "weak"), "--as-of", AS_OF, "--json", "--redact"])
    text = json.dumps(out)
    assert rc == 0 and out["redacted"]
    assert "dev-dave" not in text and "dev-erin" not in text and "@example.com" not in text


def test_missing_files_are_not_assessable(tmp_path):
    (tmp_path / "gh").mkdir()
    _, out, r = rows(tmp_path / "gh")
    assert out["summary"]["not assessable"] == 14
    assert "not exported" in r["GH-CODEOWNERS"]["gaps"][0]


def test_bad_input_exits_2(tmp_path):
    rc, _, err = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2 and "not a folder" in err
    shutil.copytree(GH / "protected", tmp_path / "gh")
    (tmp_path / "gh" / "pulls-merged.json").write_text("{not json")
    rc, _, err = run_main(mod, [str(tmp_path / "gh")])
    assert rc == 2 and "invalid JSON" in err


def test_markdown_and_fail_on():
    rc, out, _ = run_main(mod, [str(GH / "weak"), "--as-of", AS_OF, "--fail-on", "contradicted"])
    assert rc == 1 and "Preparation for a human assessor" in out and "| contradicted | GH-CODEOWNERS |" in out
    rc, _, _ = run_main(mod, [str(GH / "protected"), "--as-of", AS_OF, "--config", str(CONFIG), "--fail-on", "not-assessable"])
    assert rc == 0
