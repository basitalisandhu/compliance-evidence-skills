"""Checks that cover every skill: identical helper copies, no network code, --help, the shared helpers and the
reference files (identifiers and paraphrases only, empty forbidden-phrases lists)."""
import re

import pytest
from conftest import SKILLS, STARTER_MAP, load_script, run_main

SCRIPTS = {
    "evidence-pack-builder": ["evidence_pack.py"],
    "control-map-from-exports": ["control_map.py"],
    "github-change-control-evidence": ["github_evidence.py"],
    "aws-identity-and-logging-evidence": ["aws_evidence.py"],
    "auditor-narrative-drafter": ["narrative.py", "narrative_lint.py"],
}
ev = load_script("evidence-pack-builder", "_evidence.py")


@pytest.mark.parametrize("helper", ["_evidence.py", "_miniyaml.py"])
def test_helper_copies_are_identical(helper):
    copies = {skill: (SKILLS / skill / "scripts" / helper).read_text(encoding="utf-8") for skill in SCRIPTS}
    assert len(set(copies.values())) == 1, f"{helper} differs between skills: copy one version to every skill that carries it"


@pytest.mark.parametrize("skill", sorted(SCRIPTS))
def test_scripts_have_no_network_or_subprocess_code(skill):
    for path in (SKILLS / skill / "scripts").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+(socket|subprocess|urllib|http|requests|ssl|ftplib|smtplib)\b", text, re.M), path
        assert "os.environ" not in text and "getenv" not in text, f"{path} reads the environment"


@pytest.mark.parametrize("skill,script", [(k, s) for k, v in sorted(SCRIPTS.items()) for s in v])
def test_help_names_json_redact_and_exit_codes(skill, script):
    mod = load_script(skill, script)
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0
    assert "--redact" in out and "--json" in out and "Exit codes" in out


def test_evidence_row_refuses_supported_without_citation():
    with pytest.raises(ValueError):
        ev.evidence_row("X", {}, ev.SUPPORTED, "claim")
    with pytest.raises(ValueError):
        ev.evidence_row("X", {}, ev.CONTRADICTED, "claim", [{"file": "a.json", "field": ""}])
    with pytest.raises(ValueError):
        ev.evidence_row("X", {}, "passed", "claim", [ev.citation("a.json", "f", 1)])
    row = ev.evidence_row("X", {}, ev.NOT_ASSESSABLE, "claim", gaps=["file missing"])
    assert row["state"] == "not assessable" and row["citations"] == []


def test_only_three_states_exist():
    assert ev.STATES == ("supported", "contradicted", "not assessable")


def test_worst_state_order():
    assert ev.worst_state([ev.SUPPORTED, ev.NOT_ASSESSABLE]) == ev.NOT_ASSESSABLE
    assert ev.worst_state([ev.SUPPORTED, ev.CONTRADICTED, ev.NOT_ASSESSABLE]) == ev.CONTRADICTED
    assert ev.worst_state([ev.SUPPORTED, ev.SUPPORTED]) == ev.SUPPORTED
    assert ev.worst_state([]) == ev.NOT_ASSESSABLE


def test_error_body_recognises_github_and_graph_errors():
    gh = {"message": "Upgrade to GitHub Pro", "documentation_url": "https://docs.github.com/rest", "status": "403"}
    assert ev.error_body(gh) == {"status": "403", "message": "Upgrade to GitHub Pro"}
    assert ev.is_denied(ev.error_body(gh))
    graph = {"error": {"code": "Authorization_RequestDenied", "message": "Insufficient privileges"}}
    assert ev.is_denied(ev.error_body(graph))
    not_protected = {"message": "Branch not protected", "documentation_url": "x", "status": "404"}
    assert ev.error_body(not_protected) and not ev.is_denied(ev.error_body(not_protected))
    assert ev.error_body({"message": "hello", "url": "x", "required_status_checks": {}}) is None
    assert ev.error_body([1, 2]) is None


def test_resolve_path_fans_out_over_lists():
    data = {"trailList": [{"Name": "a", "Tags": ["x"]}, {"Name": "b"}]}
    assert ev.resolve_path(data, "trailList[].Name") == [("trailList[0].Name", "a"), ("trailList[1].Name", "b")]
    assert ev.resolve_path([{"u": 1}], "[]") == [("[0]", {"u": 1})]
    assert ev.resolve_path(data, "missing.field") == []
    assert ev.resolve_path({"a": {"b": 2}}, "a.b") == [("a.b", 2)]


def test_redact_tokenises_emails_arns_and_names():
    data = {"a": "collected by jane.doe@example.com", "b": "arn:aws:iam::123456789012:user/legacy-sync",
            "c": ["dev-alice approved #101"], "keep": "arn:aws:iam::123456789012:root"}
    out = ev.redact(data, {"dev-alice"})
    assert "jane.doe" not in out["a"] and out["a"].endswith("@redacted.invalid")
    assert "legacy-sync" not in out["b"] and out["b"].startswith("arn:aws:iam::123456789012:user/user-")
    assert "dev-alice" not in out["c"][0]
    assert out["keep"] == data["keep"]
    assert ev.redact(data, {"dev-alice"}) == out


def test_parse_dt_and_days_between():
    assert ev.parse_dt("2026-01-10T08:00:00.1234567Z").isoformat() == "2026-01-10T08:00:00.123456+00:00"
    assert ev.parse_dt("2026-02-01T09:00:00+00:00").day == 1
    assert ev.parse_dt("N/A") is None and ev.parse_dt("") is None
    assert ev.days_between("2026-10-01T00:00:00Z", ev.as_of_datetime("2026-10-05")) == 4
    with pytest.raises(ev.InputError):
        ev.as_of_datetime("yesterday")


def test_cell_keeps_untrusted_text_in_its_cell():
    assert ev.cell("a|b\nc`d") == "a\\|b c'd"


def test_sha256_file(tmp_path):
    p = tmp_path / "x.txt"
    p.write_bytes(b"abc")
    assert ev.sha256_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_disclaimer_says_preparation_not_opinion():
    text = ev.DISCLAIMER.lower()
    assert "preparation for a human assessor" in text and "not an audit opinion" in text and "attestation" in text


def test_starter_map_controls_appear_in_the_identifier_files():
    cm = load_script("control-map-from-exports", "control_map.py")
    mapping = cm.load_map(str(STARTER_MAP))
    refs = SKILLS / "control-map-from-exports" / "references"
    for fw, fname in (("iso27001", "iso27001-identifiers.md"), ("soc2", "soc2-identifiers.md")):
        table = (refs / fname).read_text(encoding="utf-8")
        for cid, topic in mapping["controls"][fw].items():
            assert f"| {cid} | {topic} |" in table, f"{cid} paraphrase differs between the starter map and {fname}"


@pytest.mark.parametrize("path", sorted(str(p) for p in SKILLS.glob("*/references/*.md")))
def test_reference_files_ship_no_forbidden_phrases_and_short_paraphrases(path):
    text = open(path, encoding="utf-8").read()
    assert not re.search(r"^phrase:", text, re.M)
    for m in re.finditer(r"^\| ((?:A|CC)\d*(?:\.\d+)+) \| ([^|]+) \|", text, re.M):
        assert len(m.group(2).split()) <= 20, m.group(1)
