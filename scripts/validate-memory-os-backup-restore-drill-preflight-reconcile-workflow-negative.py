#!/usr/bin/env python3
"""Fail-closed source-admission negatives for semantic preflight reconcile CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-drill-preflight-reconcile-negative.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "2ee5dd443a19a4a8f01113bdbc5ced4fbd4bdc60"
REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup-python SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR checkout", "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR event", '          if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then\n', 1),
    ("PR head", '            expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("SHA format", '            [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("event whitelist", '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n', 1),
    ("branch", '            test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("unreviewed event", '          else\n            echo "Unreviewed semantic preflight reconcile negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py\n', 1),
    ("PR base ref", '            test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR target filter", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
)


def validate(source: str, *, check_blob: bool = True) -> None:
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"semantic preflight reconcile workflow source boundary drift: {label}")


    if not source.rstrip().endswith('          test -z "$(git status --porcelain)"'):
        raise SystemExit("semantic preflight reconcile workflow source boundary drift: final read-only terminator")
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("semantic preflight reconcile complete workflow source drift")


def prove_branch_guards_runtime() -> None:
    """Execute reviewed branch predicates against disposable synthetic refs."""
    cases = (
        ("PR so", REQUIRED[14][1].strip(), "GITHUB_BASE_REF", "so", True),
        ("PR main", REQUIRED[14][1].strip(), "GITHUB_BASE_REF", "main", False),
        ("PR missing", REQUIRED[14][1].strip(), "GITHUB_BASE_REF", "", False),
        ("push so", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("semantic preflight reconcile runtime branch guard drift: " + label)
    print("PASS: semantic preflight reconcile PR/push branch guard runtime (6 cases)")


def prove_sha_guard_runtime() -> None:
    """Execute the shared PR and push/dispatch 40-hex predicate on synthetic input."""
    cases = (
        ("lowercase SHA", "a" * 40, True),
        ("numeric SHA", "0" * 40, True),
        ("short SHA", "a" * 39, False),
        ("long SHA", "a" * 41, False),
        ("uppercase SHA", "A" * 40, False),
        ("nonhex SHA", "g" * 40, False),
        ("missing SHA", "", False),
        ("literal substitution", "$(echo unexpected)", False),
    )
    command = 'expected="${PROBE_SHA:-}"\n' + REQUIRED[6][1].strip()
    for label, value, accepted in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}
        result = subprocess.run(
            ["bash", "-e", "-c", command], env=env, capture_output=True, check=False
        )
        if (result.returncode == 0) != accepted:
            raise SystemExit("semantic preflight reconcile SHA guard drift: " + label)
    print(f"PASS: semantic preflight reconcile shared PR/push SHA runtime ({len(cases)} cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_branch_guards_runtime()
    prove_sha_guard_runtime()
    cases = (
        ("checkout SHA", REQUIRED[0][1], "      - uses: actions/checkout@v4\n"),
        ("setup-python SHA", REQUIRED[1][1], "      - uses: actions/setup-python@v5\n"),
        ("persist credentials", REQUIRED[2][1], ""),
        ("PR source checkout", REQUIRED[3][1], "          ref: ${{ github.sha }}\n"),
        ("PR event admission", REQUIRED[4][1], ""),
        ("PR head SHA", REQUIRED[5][1], '            expected="${GITHUB_SHA:-}"\n'),
        ("SHA format", REQUIRED[6][1], '            test -n "$expected"\n'),
        ("event whitelist", REQUIRED[7][1], ""),
        ("push/dispatch branch", REQUIRED[8][1], ""),
        ("unreviewed event rejection", REQUIRED[9][1], ""),
        ("source HEAD", REQUIRED[10][1], ""),
        ("clean source", REQUIRED[11][1], ""),
        ("self-trigger", REQUIRED[12][1], ""),
        ("self-execution", REQUIRED[13][1], ""),
    )
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"semantic preflight reconcile negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit(f"semantic preflight reconcile accepted forbidden mutation: {label}")
    sha_token = REQUIRED[6][1]
    second_sha = source.rfind(sha_token)
    if second_sha == source.find(sha_token):
        raise SystemExit("semantic preflight reconcile second SHA predicate missing")
    mutated_second_sha = (
        source[:second_sha] + '            test -n "$expected"\n' +
        source[second_sha + len(sha_token):]
    )
    try:
        validate(mutated_second_sha)
    except SystemExit:
        pass
    else:
        raise SystemExit("semantic preflight reconcile accepted weakened second SHA predicate")
    # The canonical workflow may or may not end in a newline; both are valid.
    validate(source.rstrip("\n") + "\n", check_blob=False)
    try:
        validate(source + '\n          echo "unreviewed final command"\n')
    except SystemExit:
        pass
    else:
        raise SystemExit("semantic preflight reconcile accepted appended final command")
    for label, old, replacement in (
        ("PR base ref", REQUIRED[14][1], ""),
        ("PR target filter", REQUIRED[15][1], "  pull_request:\n    paths:\n"),
    ):
        if old not in source:
            raise SystemExit("semantic preflight reconcile PR branch negative anchor missing: " + label)
        try:
            validate(source.replace(old, replacement, 1))
        except SystemExit:
            continue
        raise SystemExit("semantic preflight reconcile accepted forbidden PR branch mutation: " + label)
    for label, old, replacement in (
        ("inserted executable step", "      - name: Prove preflight partial-publication rollback\n", "      - run: echo unreviewed\n      - name: Prove preflight partial-publication rollback\n"),
        ("extra command before final read-only step", "          git diff --exit-code\n", "          git diff --exit-code\n          echo unreviewed\n"),
    ):
        if old not in source:
            raise SystemExit("semantic preflight reconcile whole-source negative anchor missing: " + label)
        try:
            validate(source.replace(old, replacement, 1))
        except SystemExit:
            continue
        raise SystemExit("semantic preflight reconcile accepted forbidden whole-source mutation: " + label)
    print(f"PASS: semantic preflight reconcile workflow source admission ({len(cases) + 6} negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
