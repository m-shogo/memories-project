#!/usr/bin/env python3
"""Fail-closed source and event/ref negatives for strict preflight eligibility consistency."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-preflight-generation-eligibility-consistency.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "4eb6040b3c5ba7508a716605aeea2dc9e05c49c1"
REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("self trigger", '      - "scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency-workflow-negative.py"\n', 2),
    ("checkout SHA", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", 2),
    ("setup SHA", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("publisher credentials", "          persist-credentials: true\n", 1),
    ("PR base", '          test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("SHA format", '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("publisher branch", '          test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("publisher event", '          [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]\n', 1),
    ("publisher scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
    ("self execution", "\n          python scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency-workflow-negative.py\n", 2),
    ("writer SHA", '          expected="${GITHUB_SHA:-}"\n', 1),
    ("PR SHA", '          expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("HEAD check", '          test "$(git rev-parse HEAD)" = "$expected"\n', 2),
    ("write scope", "      contents: write\n", 1),
    ("stale-source CAS", '\n          if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then\n', 2),
    ("nested stale-source CAS", '\n            if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then\n', 2),
)


def validate(source: str, *, check_blob: bool = True) -> None:
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit("preflight eligibility consistency CI source drift: " + label)
    payload = source.encode("utf-8")
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if check_blob and hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
        raise SystemExit("preflight eligibility consistency CI complete workflow source drift")


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
            raise SystemExit("preflight eligibility consistency CI runtime branch guard drift: " + label)
    print("PASS: preflight eligibility consistency CI PR/push branch guard runtime (6 cases)")


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
        ("writer SHA", REQUIRED[12][1], '          expected="${{ github.sha }}"\n'),
        ("PR SHA", REQUIRED[13][1], '          expected="${GITHUB_SHA:-}"\n'),
        ("HEAD check", REQUIRED[14][1], ""),
        ("write scope", REQUIRED[15][1], "      contents: read\n"),
        ("stale-source CAS", REQUIRED[16][1], ""),
        ("nested stale-source CAS", REQUIRED[17][1], ""),
        ("inserted Action", "      - name: Capture exact consistency authority source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact consistency authority source\n"),
        ("inserted shell", "      - name: Capture exact consistency authority source\n", "      - run: echo unreviewed\n      - name: Capture exact consistency authority source\n"),
    )
    semantic_count = 0
    blob_only_count = 0
    for label, old, new in cases:
        if old not in source:
            raise SystemExit("preflight eligibility consistency CI negative fixture missing: " + label)
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("preflight eligibility consistency CI negative fixture unchanged: " + label)
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in REQUIRED)
        semantic_count += int(semantic)
        blob_only_count += int(not semantic)
        try:
            validate(mutated, check_blob=not semantic)
        except SystemExit:
            continue
        raise SystemExit("preflight eligibility consistency CI accepted unreviewed mutation: " + label)
    if (semantic_count, blob_only_count) != (len(cases) - 2, 2):
        raise SystemExit("preflight eligibility consistency semantic/blob mutation coverage drift")
    print(f"PASS: preflight eligibility consistency CI workflow source admission ({semantic_count} semantic; {blob_only_count} blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
