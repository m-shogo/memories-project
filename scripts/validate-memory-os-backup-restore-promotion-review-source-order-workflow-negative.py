#!/usr/bin/env python3
"""Fail-closed whole-source and runtime negatives for human promotion source-order CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-promotion-review-source-order.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "90cee6d05601f051fb2cca3dc68b1f0aae71e939"

TRIGGER_PATHS = (
    "scripts/validate-memory-os-backup-restore-promotion-review-source-order.py",
    "scripts/register-memory-os-backup-restore-promotion-review.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-promotion-review.py",
    "scripts/validate-memory-os-backup-restore-promotion-review-negative.py",
    "contracts/operations/backup-restore-promotion-review-contract.v1.json",
    "contracts/operations/backup-restore-promotion-review-registry.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/operability-admission-inventory.v1.json",
    "docs/evidence/backup-restore/**",
    ".github/workflows/backup-restore-promotion-review-source-order.yml",
    "scripts/validate-memory-os-backup-restore-promotion-review-source-order-workflow-negative.py",
)
REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("checkout ref", "          ref: ${{ github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", "            test \"${PR_BASE_REF:-}\" = \"so\"\n", 1),
    ("PR event", "          if [[ \"${GITHUB_EVENT_NAME:-}\" == \"pull_request\" ]]; then\n", 1),
    ("PR head", "            expected=\"${{ github.event.pull_request.head.sha }}\"\n", 1),
    ("push/dispatch event", "          elif [[ \"${GITHUB_EVENT_NAME:-}\" == \"push\" || \"${GITHUB_EVENT_NAME:-}\" == \"workflow_dispatch\" ]]; then\n", 1),
    ("push/dispatch branch", "            test \"${GITHUB_REF:-}\" = \"refs/heads/so\"\n", 1),
    ("SHA format", "          [[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]\n", 1),
    ("HEAD identity", "          test \"$(git rev-parse HEAD)\" = \"$expected\"\n", 1),
    ("clean source", "          test -z \"$(git status --porcelain)\"\n", 2),
    ("self-trigger", "      - 'scripts/validate-memory-os-backup-restore-promotion-review-source-order-workflow-negative.py'\n", 2),
    ("self-execution", "        run: python scripts/validate-memory-os-backup-restore-promotion-review-source-order-workflow-negative.py\n", 1),
    ("read-only token", "permissions:\n  contents: read\n", 1),
    ("unreviewed event", "          else\n            echo \"Unreviewed promotion source-order CI event\" >&2\n            exit 1\n          fi\n", 1),
    ("no contents write permission", "contents: write", 0),
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Pin every reviewed source trigger separately for PR and push."""
    if len(trigger_paths) != 13 or len(set(trigger_paths)) != 13:
        raise SystemExit("promotion source-order CI trigger inventory drift")
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (push_marker, pr_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("promotion source-order CI trigger marker drift")
    push_block = source.split(push_marker, 1)[1].split(pr_marker, 1)[0]
    pr_block = source.split(pr_marker, 1)[1].split(dispatch_marker, 1)[0]
    for event, block in (("push", push_block), ("pull_request", pr_block)):
        for path in trigger_paths:
            token = "      - '" + path + "'\n"
            if block.count(token) != 1:
                raise SystemExit("promotion source-order CI " + event + " trigger drift: " + path)


def prove_trigger_reachability_negatives(source: str) -> None:
    """Remove each event's path independently and prove semantic rejection."""
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    for event in ("push", "pull_request"):
        for path in TRIGGER_PATHS:
            token = "      - '" + path + "'\n"
            if source.count(token) != 2:
                raise SystemExit("promotion source-order CI trigger negative anchor drift: " + path)
            if event == "push":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(pr_marker, 1)
                mutated = prefix + pr_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("promotion source-order CI trigger negative accepted: " + event + " " + path)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("promotion source-order CI shortened trigger inventory accepted")
    print(f"PASS: promotion source-order CI PR/push trigger reachability ({len(TRIGGER_PATHS) * 2} semantic removal negatives; 1 shortened inventory negative)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    for label, token, count in REQUIRED:
        if source.count(token) != count:
            raise SystemExit("promotion source-order CI source drift: " + label)
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if check_blob and hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
        raise SystemExit("promotion source-order CI complete source drift")


def prove_branch_guards_runtime() -> None:
    cases = (
        ("PR so", REQUIRED[6][1].strip(), "PR_BASE_REF", "so", True),
        ("PR main", REQUIRED[6][1].strip(), "PR_BASE_REF", "main", False),
        ("PR missing", REQUIRED[6][1].strip(), "PR_BASE_REF", "", False),
        ("push so", REQUIRED[10][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", REQUIRED[10][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", REQUIRED[10][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("promotion source-order CI runtime branch drift: " + label)
    print("PASS: promotion source-order CI PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_branch_guards_runtime()
    cases = (
        ("checkout SHA", REQUIRED[0][1], "      - uses: actions/checkout@v4\n"),
        ("setup SHA", REQUIRED[1][1], "      - uses: actions/setup-python@v5\n"),
        ("no credentials", REQUIRED[2][1], ""),
        ("checkout ref", REQUIRED[3][1], "          ref: ${{ github.sha }}\n"),
        ("PR target", REQUIRED[4][1], "  pull_request:\n    branches: [main]\n    paths:\n"),
        ("PR base environment", REQUIRED[5][1], ""),
        ("PR base assertion", REQUIRED[6][1], "            test -n \"${PR_BASE_REF:-}\"\n"),
        ("PR event", REQUIRED[7][1], ""),
        ("PR head", REQUIRED[8][1], "            expected=\"${GITHUB_SHA:-}\"\n"),
        ("push/dispatch event", REQUIRED[9][1], ""),
        ("push/dispatch branch", REQUIRED[10][1], ""),
        ("SHA format", REQUIRED[11][1], "          test -n \"$expected\"\n"),
        ("HEAD identity", REQUIRED[12][1], ""),
        ("clean source", REQUIRED[13][1], ""),
        ("self-trigger", REQUIRED[14][1], ""),
        ("self-execution", REQUIRED[15][1], ""),
        ("read-only token", REQUIRED[16][1], "permissions:\n  contents: write\n"),
        ("unreviewed event", REQUIRED[17][1], ""),
        ("injected shell command", "          python -m py_compile \\\n", "          echo UNREVIEWED\n          python -m py_compile \\\n"),
        ("injected executable action", "      - name: Compile chronology and promotion validators\n", "      - uses: unreviewed/action@v1\n      - name: Compile chronology and promotion validators\n"),
        ("removed PR self-trigger", "      - 'scripts/validate-memory-os-backup-restore-promotion-review-source-order-workflow-negative.py'\n", ""),
        ("job permission escalation", "jobs:\n  validate:\n", "jobs:\n  validate:\n    permissions:\n      contents: write\n"),
    )
    if len(cases) != 22:
        raise SystemExit("promotion source-order CI mutation inventory drift")
    digest_only = frozenset({"injected shell command", "injected executable action"})
    semantic_count = 0
    blob_only_count = 0
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit("promotion source-order CI negative anchor missing: " + label)
        mutated = source.replace(old, replacement, 1)
        if mutated == source:
            raise SystemExit("promotion source-order CI mutation unchanged: " + label)
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in REQUIRED)
        if semantic == (label in digest_only):
            raise SystemExit("promotion source-order CI mutation classification drift: " + label)
        semantic_count += int(semantic)
        blob_only_count += int(not semantic)
        try:
            validate(mutated, check_blob=not semantic)
        except SystemExit:
            continue
        raise SystemExit("promotion source-order CI accepted forbidden mutation: " + label)
    if (semantic_count, blob_only_count) != (20, 2):
        raise SystemExit("promotion source-order CI semantic/blob mutation coverage drift")
    print(f"PASS: promotion source-order CI source admission ({semantic_count} semantic; {blob_only_count} blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
