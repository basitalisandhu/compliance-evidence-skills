"""Tests for auditor-narrative-drafter/scripts/narrative_lint.py: each rule, the planted bad narrative and clean text."""
from conftest import FIXTURES, SKILLS, load_script, run_json, run_main

mod = load_script("auditor-narrative-drafter", "narrative_lint.py")
CMAP = FIXTURES / "narrative" / "control-map.json"
BAD = FIXTURES / "narrative" / "bad-narrative.md"
HEAD = "# Narrative\n\n> Preparation for a human assessor, not an audit opinion or attestation.\n\n"


def lint_text(write, body, *extra):
    p = write("n.md", HEAD + body)
    rc, out = run_json(mod, [str(p), str(CMAP), "--json", *extra])
    return rc, [(x["rule"], x["line"]) for x in out["problems"]]


def rules(problems):
    return sorted({r for r, _ in problems})


def test_planted_bad_narrative_hits_every_rule():
    rc, out = run_json(mod, [str(BAD), str(CMAP), "--json"])
    assert rc == 1
    found = {(p["rule"], p["line"]) for p in out["problems"]}
    assert ("UNCITED-CLAIM", 9) in found
    assert ("STATE-MISMATCH", 15) in found
    assert ("CERTAINTY", 21) in found and sum(1 for r, _ in found if r == "CERTAINTY") == 1
    assert [p["message"] for p in out["problems"] if p["rule"] == "CERTAINTY"] == [
        "forbidden certainty wording 'fully compliant'", "forbidden certainty wording '100%'"]
    assert ("UNKNOWN-CITATION", 22) in found
    assert ("UNKNOWN-CONTROL", 24) in found


def test_clean_cited_text_passes(write):
    rc, problems = lint_text(write, "## A.8.15\n\nTopic (paraphrase): Logging is enforced.\n\n"
                                    "The trail status records IsLogging as `true` [evidence: aws/cloudtrail-status-org-trail.json#IsLogging]. "
                                    "Taken together, the cited exports support the mapped checks "
                                    "[evidence: aws/cloudtrail-trails.json#trailList[]].\n")
    assert rc == 0 and problems == []


def test_known_citation_under_the_wrong_control_is_reported(write):
    body = "## A.8.12\n\nThe export records `true` [evidence: aws/cloudtrail-status-org-trail.json#IsLogging].\n"
    rc, problems = lint_text(write, body)
    assert rc == 1 and problems == [("WRONG-CONTROL-CITATION", 7)]
    rc, problems = lint_text(write, body.replace("A.8.12", "A.8.15"))
    assert rc == 0 and problems == []


def test_unknown_citation_is_not_reported_twice(write):
    _, problems = lint_text(write, "## A.8.15\n\nObserved [evidence: missing.json#field].\n")
    assert rules(problems) == ["UNKNOWN-CITATION"]


def test_uncited_outcome_claim(write):
    rc, problems = lint_text(write, "## A.8.32\n\nAll changes are reviewed and the control is operating.\n")
    assert rc == 1 and rules(problems) == ["UNCITED-CLAIM"]


def test_not_assessable_sentences_need_no_citation(write):
    rc, problems = lint_text(write, "## A.8.16\n\nThis topic is not assessable from the exports in this pack alone.\n")
    assert rc == 0 and problems == []


def test_unknown_citation(write):
    rc, problems = lint_text(write, "## A.8.15\n\nThe trail is logging [evidence: aws/other.json#IsLogging].\n")
    assert rules(problems) == ["UNKNOWN-CITATION"]


def test_state_mismatch_both_ways(write):
    _, problems = lint_text(write, "## A.8.16\n\nThe exports support this [evidence: aws/cloudtrail-status-org-trail.json#IsLogging].\n")
    assert rules(problems) == ["STATE-MISMATCH", "WRONG-CONTROL-CITATION"]
    _, problems = lint_text(write, "## A.8.15\n\nThe export contradicts this [evidence: aws/cloudtrail-status-org-trail.json#IsLogging].\n")
    assert rules(problems) == ["STATE-MISMATCH"]
    _, problems = lint_text(write, "## A.8.12\n\nThe exports do not support this "
                                   "[evidence: github/repo.json#security_and_analysis.secret_scanning.status].\n")
    assert problems == []


def test_certainty_words_outside_code_only(write):
    _, problems = lint_text(write, "## A.8.15\n\nLogging is guaranteed [evidence: aws/cloudtrail-status-org-trail.json#IsLogging].\n")
    assert rules(problems) == ["CERTAINTY"]
    _, problems = lint_text(write, "## A.8.15\n\nThe export records `12 of 12 (100%)` [evidence: aws/cloudtrail-status-org-trail.json#IsLogging].\n")
    assert problems == []


def test_missing_disclaimer(write):
    p = write("n.md", "# Narrative\n\nNothing to see.\n")
    rc, out = run_json(mod, [str(p), str(CMAP), "--json"])
    assert rc == 1 and [x["rule"] for x in out["problems"]] == ["NO-DISCLAIMER"]


def test_copied_text_needs_a_listed_phrase_and_a_long_line(write):
    phrases = write("phrases.md", "# local list\n\nphrase: an example distinctive clause from a licensed copy\n")
    long_line = ("Our narrative says that " + "we keep " * 8 + "an example distinctive clause from a licensed copy "
                 "and more words to pass the limit.")
    _, problems = lint_text(write, "## A.8.16\n\n" + long_line + " This is not assessable.\n", "--phrases", str(phrases))
    assert "COPIED-TEXT" in rules(problems)
    _, problems = lint_text(write, "## A.8.16\n\nAn example distinctive clause from a licensed copy, not assessable.\n",
                            "--phrases", str(phrases))
    assert "COPIED-TEXT" not in rules(problems)


def test_default_phrase_list_ships_empty():
    assert mod.load_phrases([str(SKILLS / "auditor-narrative-drafter" / "references" / "forbidden-phrases.md")]) == []
    for name in ("iso27001-identifiers.md", "soc2-identifiers.md"):
        assert mod.load_phrases([str(SKILLS / "control-map-from-exports" / "references" / name)]) == []


def test_code_blocks_are_ignored(write):
    rc, problems = lint_text(write, "```text\nThis is fully compliant and enforced.\n```\n")
    assert rc == 0 and problems == []


def test_markdown_report_and_bad_input(tmp_path):
    rc, out, _ = run_main(mod, [str(BAD), str(CMAP)])
    assert rc == 1 and "| UNCITED-CLAIM |" in out
    rc, _, err = run_main(mod, [str(tmp_path / "missing.md"), str(CMAP)])
    assert rc == 2 and "cannot read" in err
