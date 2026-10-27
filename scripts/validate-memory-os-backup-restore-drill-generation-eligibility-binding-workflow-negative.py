#!/usr/bin/env python3
"""Fail-closed source and event/ref negative CI for reviewed drill generation binding."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-drill-generation-eligibility-binding.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "f5bf77c97a966804d4c216eca3874bf8fb08c4a4"
REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("self trigger", '      - "scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding-workflow-negative.py"\n', 2),
    ("checkout SHA", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", 2),
    ("setup SHA", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("publisher credentials", "          persist-credentials: true\n", 1),
    ("PR base", '          test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR SHA", '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 1),
    ("publisher branch", '          test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("publisher event", '          [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]\n', 1),
    ("publisher scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
    ("self execution", "\n          python scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding-workflow-negative.py\n", 2),
    ("retry self execution", "\n            python scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding-workflow-negative.py\n", 1),
    ("writer SHA", '          EXPECTED_SOURCE_SHA="${GITHUB_SHA:-}"\n', 1),
    ("writer SHA format", '          [[ "$EXPECTED_SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]\n', 1),
    ("PR SHA source", '          expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("PR HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("publisher HEAD", '          test "$(git rev-parse HEAD)" = "$EXPECTED_SOURCE_SHA"\n', 1),
    ("write scope", "      contents: write\n", 1),
    ("retry latest", "            git reset --hard origin/so\n", 1),
)


def validate(source: str, *, check_blob: bool = True) -> None:
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit("drill generation binding CI source drift: " + label)
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("drill generation binding CI complete workflow source drift")


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
            raise SystemExit("drill generation binding CI runtime branch guard drift: " + label)
    print("PASS: drill generation binding CI PR/push branch guard runtime (6 cases)")


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
        ("PR SHA format", REQUIRED[7][1], '          test -n "$expected"\n'),
        ("publisher branch", REQUIRED[8][1], ""),
        ("publisher event", REQUIRED[9][1], ""),
        ("publisher scope", REQUIRED[10][1], "    if: github.event_name != 'pull_request'\n"),
        ("self execution", REQUIRED[11][1], ""),
        ("retry self execution", REQUIRED[12][1], ""),
        ("writer SHA", REQUIRED[13][1], '          EXPECTED_SOURCE_SHA="${{ github.sha }}"\n'),
        ("writer SHA format", REQUIRED[14][1], ""),
        ("PR SHA", REQUIRED[15][1], '          expected="${GITHUB_SHA:-}"\n'),
        ("PR HEAD", REQUIRED[16][1], ""),
        ("publisher HEAD", REQUIRED[17][1], ""),
        ("write scope", REQUIRED[18][1], "      contents: read\n"),
        ("retry latest", REQUIRED[19][1], ""),
        ("inserted Action", "      - name: Capture exact semantic binding authority source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact semantic binding authority source\n"),
        ("inserted shell", "      - name: Capture exact semantic binding authority source\n", "      - run: echo unreviewed\n      - name: Capture exact semantic binding authority source\n"),
    )
    blob_only = {"inserted Action", "inserted shell"}
    if len(cases) != 22 or sum(label in blob_only for label, _, _ in cases) != 2:
        raise SystemExit("drill generation binding CI negative inventory drift")
    for label, old, new in cases:
        if old not in source:
            raise SystemExit("drill generation binding CI negative fixture missing: " + label)
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("drill generation binding CI negative fixture unchanged: " + label)
        try:
            validate(mutated, check_blob=label in blob_only)
        except SystemExit:
            continue
        raise SystemExit("drill generation binding CI accepted unreviewed mutation: " + label)
    print(f"PASS: drill generation binding CI workflow source admission ({len(cases) - 2} semantic anchor + 2 blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
