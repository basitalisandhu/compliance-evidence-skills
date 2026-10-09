#!/usr/bin/env python3
"""compliance-evidence: one command for the compliance-evidence skill scripts.

    compliance-evidence <subcommand> [args]       run one skill script with the given arguments
    compliance-evidence <subcommand> --help       that script's own help
    compliance-evidence --help                    list the subcommands

Each subcommand runs plugins/compliance-evidence/skills/<skill>/scripts/<script>.py unchanged, in a child process with
the same Python, stdin, stdout, stderr and exit code. Standard library only. This is the entrypoint of the
container image ghcr.io/basitalisandhu/compliance-evidence-skills.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__version__ = "0.3.0"

PROG = "compliance-evidence"
ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "compliance-evidence" / "skills"

# subcommand: (skill directory, script, one-line summary)
COMMANDS: dict[str, tuple[str, str, str]] = {
    "pack": (
        "evidence-pack-builder",
        "evidence_pack.py",
        "Build, verify and age-check an evidence pack with SHA-256 manifests",
    ),
    "map": (
        "control-map-from-exports",
        "control_map.py",
        "Map a pack's exports to ISO 27001 or SOC 2 identifiers with a mapping file",
    ),
    "github": (
        "github-change-control-evidence",
        "github_evidence.py",
        "Change and vulnerability management evidence rows from saved GitHub exports",
    ),
    "aws": (
        "aws-identity-and-logging-evidence",
        "aws_evidence.py",
        "Logging, identity and backup evidence rows from saved aws CLI output",
    ),
    "narrative": (
        "auditor-narrative-drafter",
        "narrative.py",
        "Draft cited control narratives from a control map",
    ),
    "narrative-lint": (
        "auditor-narrative-drafter",
        "narrative_lint.py",
        "Reject uncited, over-certain or copied wording in a narrative",
    ),
    "questionnaire": (
        "security-questionnaire-drafter",
        "questionnaire.py",
        "Draft cited security questionnaire answers from a pack and policies",
    ),
    "e8": (
        "essential-eight-evidence-map",
        "e8_map.py",
        "Map a pack to the Essential Eight and the level each strategy can claim",
    ),
}


def script_path(name: str) -> Path:
    skill, script, _ = COMMANDS[name]
    return SKILLS / skill / "scripts" / script


def usage() -> str:
    width = max(len(n) for n in COMMANDS)
    lines = [
        f"usage: {PROG} <subcommand> [args]",
        "",
        f"Runs one of the compliance-evidence skill scripts. Use '{PROG} <subcommand> --help' for its options.",
        "Every result is supported, contradicted or not assessable; every output is preparation for a human",
        "assessor, not an audit opinion or attestation.",
        "",
        "subcommands:",
    ]
    lines += [f"  {n.ljust(width)}  {h} ({script})" for n, (_, script, h) in COMMANDS.items()]
    lines += ["", "options:", "  -h, --help     show this help and exit", "  --version      show the version and exit"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(usage(), file=sys.stderr)
        return 2
    first, rest = args[0], args[1:]
    if first in ("-h", "--help", "help") and not rest:
        print(usage())
        return 0
    if first == "help":
        first, rest = rest[0], ["--help"]
    if first == "--version":
        print(f"{PROG} {__version__}")
        return 0
    if first not in COMMANDS:
        print(f"{PROG}: unknown subcommand {first!r}\n\n{usage()}", file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, str(script_path(first)), *rest])


if __name__ == "__main__":
    sys.exit(main())
