#!/usr/bin/env python3
"""Fail-closed executable-source and event/ref negatives for semantic eligibility CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-equivalent-environment-eligibility.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "72aa5578692cbfa70d6c69b56495539d9244c629"
REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("self trigger", '      - "scripts/validate-memory-os-production-equivalent-environment-eligibility-workflow-negative.py"\n', 2),
    ("checkout SHA", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", 2),
    ("setup SHA", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("publisher credentials", "          persist-credentials: true\n", 1),
    ("PR base", '          test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR SHA format", '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("publisher branch", '          test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("publisher event", '          [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]\n', 1),
    ("publisher scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
    ("self execution", "          python scripts/validate-memory-os-production-equivalent-environment-eligibility-workflow-negative.py\n", 2),
    ("retry self execution", "            python scripts/validate-memory-os-production-equivalent-environment-eligibility-workflow-negative.py\n", 1),
    ("writer SHA", '          expected="${GITHUB_SHA:-}"\n', 1),
    ("PR SHA", '          expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("HEAD check", '          test "$(git rev-parse HEAD)" = "$expected"\n', 2),
    ("write scope", "      contents: write\n", 1),
    ("retry latest", "            git reset --hard origin/so\n", 1),
)


def validate(source: str) -> None:
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit("semantic eligibility CI workflow source drift: " + label)
    payload = source.encode("utf-8")
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
        raise SystemExit("semantic eligibility CI complete workflow source drift")


def prove_branch_guards_runtime() -> None:
    pr = REQUIRED[6][1].strip()
    push = REQUIRED[8][1].strip()
    cases = (
        ("PR so", pr, "GITHUB_BASE_REF", "so", True),
        ("PR main", pr, "GITHUB_BASE_REF", "main", False),
        ("PR missing", pr, "GITHUB_BASE_REF", "", False),
        ("push so", push, "GITHUB_REF", "refs/heads/so", True),
        ("push main", push, "GITHUB_REF", "refs/heads/main", False),
        ("push tag", push, "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("semantic eligibility CI runtime branch guard drift: " + label)
    print("PASS: semantic eligibility CI PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_branch_guards_runtime()
    cases = (
        ("PR target", REQUIRED[0][1], "  pull_request:\n    paths:\n"),
        ("self trigger", REQUIRED[1][1], ""),
        ("checkout floating", REQUIRED[2][1], "uses: actions/checkout@v4"),
        ("setup floating", REQUIRED[3][1], "uses: actions/setup-python@v5"),
        ("PR credentials", REQUIRED[4][1], "          persist-credentials: true\n"),
        ("writer credentials", REQUIRED[5][1], ""),
        ("PR base", REQUIRED[6][1], ""),
        ("SHA format", REQUIRED[7][1], '          test -n "$expected"\n'),
        ("publisher branch", REQUIRED[8][1], ""),
        ("publisher event", REQUIRED[9][1], ""),
        ("publisher scope", REQUIRED[10][1], "    if: github.event_name != 'pull_request'\n"),
        ("self execution", REQUIRED[11][1], ""),
        ("retry self execution", REQUIRED[12][1], ""),
        ("writer SHA", REQUIRED[13][1], '          expected="${{ github.sha }}"\n'),
        ("PR SHA", REQUIRED[14][1], '          expected="${GITHUB_SHA:-}"\n'),
        ("HEAD check", REQUIRED[15][1], ""),
        ("write scope", REQUIRED[16][1], "      contents: read\n"),
        ("retry latest", REQUIRED[17][1], ""),
        ("inserted Action", "      - name: Capture exact semantic eligibility source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact semantic eligibility source\n"),
        ("inserted shell", "      - name: Capture exact semantic eligibility source\n", "      - run: echo unreviewed\n      - name: Capture exact semantic eligibility source\n"),
    )
    for label, old, new in cases:
        if old not in source:
            raise SystemExit("semantic eligibility CI negative fixture missing: " + label)
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("semantic eligibility CI negative fixture unchanged: " + label)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit("semantic eligibility CI accepted unreviewed mutation: " + label)
    print(f"PASS: semantic eligibility CI workflow source admission ({len(cases)} negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
