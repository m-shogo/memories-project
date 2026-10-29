#!/usr/bin/env python3
"""Conservative read-only pre-write workflow trigger blast-radius audit.

This is an over-approximation of direct push/PR path matching, NOT an
authorization to write or proof of transitive workflow-call reachability.
A risky result must block autonomous unreviewed writes until scoped.
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import sys
from pathlib import Path

MAX_REVIEWED_DIRECT_FANOUT = 12
KNOWN_EXTERNAL_BLOCKED_WORKFLOWS = {
    ".github/workflows/reconcile-upload-route-authority.yml",
    ".github/workflows/reconcile-upload-route-authority-pr.yml",
}


class AuditFailure(RuntimeError):
    pass


def workflow_matches_path(source: str, relative: str) -> bool:
    """Conservatively match direct push/PR events; ambiguous filters are risky."""
    # GitHub accepts quoted YAML event keys and inline scalar/map triggers.
    # Missing these forms would undercount prewrite fanout, not just overestimate.
    source = re.sub(r"""(?m)^(['"])on\1:""", "on:", source)
    source = re.sub(r"""(?m)^  (['"])(push|pull_request)\1:""", r"  \2:", source)
    inline = re.search(r"(?m)^on:[ \t]*([^\r\n]+)", source)
    if inline and re.search(r"\b(?:push|pull_request)\b", inline.group(1)):
        return True
    if re.search(r"(?m)^on:\s*\[[^\]]*\b(?:push|pull_request)\b", source):
        return True
    section = re.search(
        r"(?ms)^on:\s*\n(.*?)(?=^[A-Za-z_][\w-]*:|\Z)", source
    )
    if section is None:
        return bool(re.search(r"(?m)^  (?:push|pull_request):", source))
    block = section.group(1)
    for event in ("push", "pull_request"):
        match = re.search(
            r"(?ms)^  " + event + r":\s*\n(.*?)(?=^  [A-Za-z_][\w-]*:|\Z)",
            block,
        )
        if match is None:
            if re.search(r"(?m)^  " + event + r":", block):
                return True
            continue
        event_body = match.group(1)
        if "    paths-ignore:" in event_body or "    paths:" not in event_body:
            return True
        paths = re.search(
            r"(?ms)^    paths:\s*\n((?:^      - .*(?:\n|\Z))+)",
            event_body,
        )
        if paths is None:
            return True
        for row in paths.group(1).splitlines():
            pattern = row.strip()[2:].strip()
            if pattern.startswith(("'", '"')) and pattern.endswith(pattern[0]):
                pattern = pattern[1:-1]
            if pattern.startswith("!"):
                # Ignoring exclusions overestimates rather than misses risk.
                continue
            # fnmatch can match "/" with "*"; this deliberate overestimate
            # is safer than claiming exact GitHub minimatch equivalence.
            if fnmatch.fnmatchcase(relative, pattern):
                return True
    return False


def validate_relative_path(relative: str) -> None:
    if (not relative or relative.startswith("/") or "\\" in relative
            or any(part in ("", ".", "..") for part in relative.split("/"))):
        raise AuditFailure("prewrite path must be a safe repository-relative path")


def matching_workflows(repo_root: Path, relative: str) -> list[str]:
    validate_relative_path(relative)
    directory = repo_root / ".github/workflows"
    if directory.is_symlink() or not directory.is_dir():
        raise AuditFailure("workflow directory missing or symlinked")
    matches: list[str] = []
    for workflow in sorted((*directory.glob("*.yml"), *directory.glob("*.yaml"))):
        if workflow.is_symlink() or not workflow.is_file():
            raise AuditFailure("workflow path missing or symlinked")
        source = workflow.read_text(encoding="utf-8")
        if workflow_matches_path(source, relative):
            matches.append(workflow.relative_to(repo_root).as_posix())
    return matches


def classify(matches: list[str]) -> str:
    if set(matches) & KNOWN_EXTERNAL_BLOCKED_WORKFLOWS:
        return "BLOCKED_KNOWN_EXTERNAL_DEPENDENCY"
    if len(matches) > MAX_REVIEWED_DIRECT_FANOUT:
        return "BLOCKED_HIGH_FANOUT"
    return "BOUNDED_DIRECT_MATCH_ONLY"


def self_test(repo_root: Path) -> None:
    cases = (
        ("exact", 'on:\n  push:\n    paths:\n      - "scripts/a.py"\n', "scripts/a.py", True),
        ("glob", 'on:\n  pull_request:\n    paths:\n      - "scripts/validate-memory-os-rate-limit*.py"\n',
         "scripts/validate-memory-os-rate-limit-operations.py", True),
        ("unrelated", 'on:\n  push:\n    paths:\n      - "docs/**"\n', "scripts/a.py", False),
        ("unfiltered", 'on:\n  push:\n    branches:\n      - so\n', "scripts/a.py", True),
        ("paths-ignore", 'on:\n  push:\n    paths-ignore:\n      - "docs/**"\n', "scripts/a.py", True),
        ("dispatch", 'on:\n  workflow_dispatch:\n', "scripts/a.py", False),
        ("inline", 'on: [push, workflow_dispatch]\n', "scripts/a.py", True),
        ("quoted-on-block", "'on':\n  push:\n    paths:\n      - 'scripts/a.py'\n",
         "scripts/a.py", True),
        ("quoted-on-inline", '"on": [push, workflow_dispatch]\n',
         "scripts/a.py", True),
        ("scalar-push", "on: push\n", "scripts/a.py", True),
        ("inline-map", "on: {pull_request: {paths: ['scripts/a.py']}}\n",
         "scripts/a.py", True),
        ("scalar-dispatch", "on: workflow_dispatch\n", "scripts/a.py", False),
        ("quoted-push-event", "on:\n  'push':\n    paths:\n      - scripts/a.py\n",
         "scripts/a.py", True),
        ("quoted-pr-event", 'on:\n  "pull_request":\n    paths:\n      - scripts/a.py\n',
         "scripts/a.py", True),
    )
    for name, source, path, expected in cases:
        if workflow_matches_path(source, path) is not expected:
            raise AuditFailure("prewrite fanout negative/positive failed: " + name)
    if classify([".github/workflows/w" + str(i) + ".yml"
                 for i in range(MAX_REVIEWED_DIRECT_FANOUT + 1)]) != "BLOCKED_HIGH_FANOUT":
        raise AuditFailure("high-fanout threshold negative failed")
    if classify([".github/workflows/reconcile-upload-route-authority.yml"]) != (
            "BLOCKED_KNOWN_EXTERNAL_DEPENDENCY"):
        raise AuditFailure("known MinIO-coupled trigger negative failed")
    high = matching_workflows(repo_root, "scripts/validate-memory-os-operability.py")
    rate = matching_workflows(
        repo_root, "scripts/validate-memory-os-rate-limit-operations-source-negative.py"
    )
    # A high-fanout path can also match the known MinIO-blocked workflow.
    # Preserve the higher-priority external blocker without hiding fanout.
    if len(high) <= MAX_REVIEWED_DIRECT_FANOUT:
        raise AuditFailure("known operability validator fanout not detected")
    if classify(high) not in ("BLOCKED_HIGH_FANOUT", "BLOCKED_KNOWN_EXTERNAL_DEPENDENCY"):
        raise AuditFailure("known operability validator risk classification missing")
    if not (set(rate) & KNOWN_EXTERNAL_BLOCKED_WORKFLOWS):
        raise AuditFailure("known upload-route MinIO trigger coupling not detected")
    print(
        "prewrite fanout audit PASS: " + str(len(cases) + 2)
        + " synthetic cases; operability direct matches="
        + str(len(high)) + "; rate-limit direct matches=" + str(len(rate))
        + "; known MinIO coupling flagged; no workflow executed"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--path")
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test(args.repo_root)
            return 0
        matches = matching_workflows(args.repo_root, args.path)
        risk = classify(matches)
        print("prewrite direct path audit: " + args.path)
        print("risk: " + risk + "; matched workflow count: " + str(len(matches)))
        for workflow in matches:
            print("- " + workflow)
        if risk != "BOUNDED_DIRECT_MATCH_ONLY":
            print("Do not write until independent scoped review changes the precondition.")
            return 2
        print("Direct matching alone is not permission or transitive closure proof.")
        return 0
    except (OSError, UnicodeError, AuditFailure) as exc:
        print("PREWRITE TRIGGER AUDIT FAILED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
