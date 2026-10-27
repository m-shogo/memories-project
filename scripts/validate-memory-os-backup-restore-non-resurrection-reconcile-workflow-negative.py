#!/usr/bin/env python3
"""Fail-closed source-admission negatives for typed non-resurrection reconcile CI."""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-non-resurrection-reconcile-negative.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "ea00ec141cbde9c2822a51d755142a2665a072c8"
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
    ("unreviewed event", '          else\n            echo "Unreviewed typed non-resurrection reconcile negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-non-resurrection-reconcile-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-non-resurrection-reconcile-workflow-negative.py\n', 1),
    ("PR base ref", '            test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR target filter", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("material delta review trigger", '      - "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py"\n', 2),
)


def validate(source: str, *, check_blob: bool = True) -> None:
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"typed non-resurrection reconcile workflow source boundary drift: {label}")


    if not source.rstrip().endswith('          test -z "$(git status --porcelain)"'):
        raise SystemExit("typed non-resurrection reconcile workflow source boundary drift: final read-only terminator")
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("typed non-resurrection reconcile workflow complete source blob drift")


def prove_branch_guards_runtime() -> None:
    """Execute the reviewed shell predicates against disposable synthetic refs."""
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
            raise SystemExit("typed non-resurrection reconcile runtime branch guard drift: " + label)
    print("PASS: typed non-resurrection reconcile PR/push branch guard runtime (6 cases)")


RECONCILE_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-non-resurrection-reconcile-negative.py"
PRIVATE_ROLLBACK_NEGATIVES = (
    ("prove_rollback_attempts_all_restores", "typed non-resurrection rollback incomplete"),
    ("prove_primary_and_rollback_failures_are_preserved",
     "typed non-resurrection reconcile failed; rollback incomplete"),
    ("prove_second_replace_rollback",
     "typed non-resurrection reconcile failed; rollback completed"),
    ("prove_post_write_aggregate_rollback",
     "typed non-resurrection reconcile failed; rollback completed"),
)


def require_private_rollback_negative_reachable(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise SystemExit("typed rollback negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    main = functions.get("main")
    if main is None:
        raise SystemExit("typed rollback negative main missing")
    for function_name, expected in PRIVATE_ROLLBACK_NEGATIVES:
        target = functions.get(function_name)
        if target is None:
            raise SystemExit("typed private rollback negative missing: " + function_name)
        calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == function_name]
        if len(calls) != 1:
            raise SystemExit("typed private rollback negative invocation drift: " + function_name)
        strings = {node.value for node in ast.walk(target)
                   if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        if expected not in strings:
            raise SystemExit("typed private rollback failure class missing: " + function_name)


def prove_private_rollback_negative_deletion_rejected() -> None:
    source = RECONCILE_NEGATIVE.read_text(encoding="utf-8")
    require_private_rollback_negative_reachable(source)
    for function_name, _expected in PRIVATE_ROLLBACK_NEGATIVES:
        anchor = f"    {function_name}()\n"
        if source.count(anchor) != 1:
            raise SystemExit("typed private rollback negative deletion anchor drift")
        mutated = source.replace(anchor, "    pass\n", 1)
        try:
            require_private_rollback_negative_reachable(mutated)
        except SystemExit:
            pass
        else:
            raise SystemExit("typed private rollback negative deletion accepted: " + function_name)
    print("PASS: typed private rollback class negatives and invocation deletion rejected")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_branch_guards_runtime()
    prove_private_rollback_negative_deletion_rejected()
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
        ("material delta review trigger", REQUIRED[16][1], ""),
    )
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"typed non-resurrection reconcile negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated, check_blob=False)
        except SystemExit:
            continue
        raise SystemExit(f"typed non-resurrection reconcile accepted forbidden mutation: {label}")
    # The canonical workflow may or may not end in a newline; both are valid.
    validate(source.rstrip("\n") + "\n", check_blob=False)
    try:
        validate(source + '\n          echo "unreviewed final command"\n')
    except SystemExit:
        pass
    else:
        raise SystemExit("typed non-resurrection reconcile accepted appended final command")
    for label, old, replacement in (
        ("PR base ref", REQUIRED[14][1], ""),
        ("PR target filter", REQUIRED[15][1], "  pull_request:\n    paths:\n"),
    ):
        if old not in source:
            raise SystemExit("typed non-resurrection reconcile PR branch negative anchor missing: " + label)
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated, check_blob=False)
        except SystemExit:
            continue
        raise SystemExit("typed non-resurrection reconcile accepted forbidden PR branch mutation: " + label)
    # Whole-source binding rejects otherwise anchor-preserving workflow changes.
    for label, mutated in (
        ("extra executable step", source.replace(
            "      - name: Prove transactional typed non-resurrection reconciliation\n",
            "      - run: echo unreviewed\n      - name: Prove transactional typed non-resurrection reconciliation\n", 1)),
    ):
        if mutated == source:
            raise SystemExit("typed non-resurrection reconcile source digest negative anchor missing: " + label)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit("typed non-resurrection reconcile accepted whole-source mutation: " + label)
    print(f"PASS: typed non-resurrection reconcile workflow source admission ({len(cases) + 2} semantic anchor negatives; 2 complete-source/terminator negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
