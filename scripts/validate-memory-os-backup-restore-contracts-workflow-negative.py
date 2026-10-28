#!/usr/bin/env python3
"""Fail-closed whole-source and runtime negatives for backup restore contracts CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-contracts.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "5313bc823e23d848ac50fdbbc6e53b713a7503a3"
TRIGGER_PATHS = (
    ".github/workflows/backup-restore-contracts.yml",
    ".github/workflows/local-logical-restore.yml",
    ".github/workflows/reconcile-backup-restore.yml",
    "contracts/operations/backup-restore-contract.v1.json",
    "contracts/operations/backup-restore-admission-chain-contract.v1.json",
    "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/local-logical-restore-contract.v1.json",
    "contracts/operations/migration-lifecycle-contract.v1.json",
    "contracts/operations/operability-admission-inventory.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/evidence/backup-restore/**",
    "docs/runbooks/memory-os-backup-restore.md",
    "infra/postgresql/security/**",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/run-memory-os-local-logical-restore.sh",
    "scripts/validate-memory-os-local-logical-restore.py",
    "scripts/reconcile-memory-os-local-logical-restore.py",
    "scripts/validate-memory-os-backup-restore.py",
    "scripts/validate-memory-os-backup-restore-blockers-negative.py",
    "scripts/validate-memory-os-backup-restore-blocker-authority-negative.py",
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-review-source-order.py",
    "scripts/validate-memory-os-backup-restore-promotion-review.py",
    "scripts/validate-memory-os-backup-restore-ephemeral-lock-authority-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-independent-review.py",
    "scripts/validate-memory-os-backup-restore-generation-independent-review-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py",
    "scripts/validate-memory-os-backup-restore-admission-chain.py",
    "scripts/validate-memory-os-backup-restore-admission-chain-authority-negative.py",
    "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-writer-authority.py",
    "scripts/reconcile-memory-os-backup-restore.py",
    "scripts/reconcile-memory-os-backup-authority.py",
    "scripts/reconcile-memory-os-backup-semantic-overlay.py",
    "scripts/reconcile-memory-os-backup-coherent-authority.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-backup-restore-contracts-workflow-negative.py",
)
REQUIRED = (
    ("checkout SHA", "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup SHA", "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("checkout ref", "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", "            test \"${PR_BASE_REF:-}\" = \"so\"\n", 1),
    ("PR event", "          if [[ \"${GITHUB_EVENT_NAME:-}\" == \"pull_request\" ]]; then\n", 1),
    ("PR head", "            expected=\"${{ github.event.pull_request.head.sha }}\"\n", 1),
    ("push/dispatch event", "          elif [[ \"${GITHUB_EVENT_NAME:-}\" == \"push\" || \"${GITHUB_EVENT_NAME:-}\" == \"workflow_dispatch\" ]]; then\n", 1),
    ("push/dispatch branch", "            test \"${GITHUB_REF:-}\" = \"refs/heads/so\"\n", 1),
    ("SHA format", "          [[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]\n", 1),
    ("HEAD identity", "          test \"$(git rev-parse HEAD)\" = \"$expected\"\n", 1),
    ("clean source", "          test -z \"$(git status --porcelain)\"", 2),
    ("self-trigger", "      - \"scripts/validate-memory-os-backup-restore-contracts-workflow-negative.py\"\n", 2),
    ("self-execution", "        run: python scripts/validate-memory-os-backup-restore-contracts-workflow-negative.py\n", 1),
    ("read-only token", "permissions:\n  contents: read\n", 1),
    ("unreviewed event", "          else\n            echo \"Unreviewed backup restore contracts CI event\" >&2\n            exit 1\n          fi\n", 1),
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Require every reviewed backup/restore contracts CI path in both events."""
    if len(trigger_paths) != 49 or len(set(trigger_paths)) != 49:
        raise SystemExit("backup restore contracts CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("backup restore contracts CI trigger marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    for event, block in (("pull_request", pr), ("push", push)):
        # Fail closed on unquoted/unknown YAML entries instead of filtering them away.
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        expected = tuple(f'      - "{item}"' for item in trigger_paths)
        if actual != expected:
            raise SystemExit("backup restore contracts CI " + event + " trigger inventory drift")
        for item in trigger_paths:
            if block.count('      - "' + item + '"' + chr(10)) != 1:
                raise SystemExit("backup restore contracts CI " + event + " trigger path drift: " + item)


def prove_trigger_reachability_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for item in TRIGGER_PATHS:
            token = '      - "' + item + '"' + chr(10)
            if source.count(token) != 2:
                raise SystemExit("backup restore contracts CI trigger mutation anchor drift: " + item)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("backup restore contracts CI accepted missing " + event + " trigger: " + item)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("backup restore contracts CI shortened trigger inventory accepted")
    print("PASS: backup restore contracts CI event-specific trigger reachability (98 removals; 1 shortened inventory negative)")
    # Both PR and push must independently reject quoted and unquoted additions.
    for event in ("pull_request", "push"):
        for label, inserted in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", f'      - "{TRIGGER_PATHS[0]}"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", f"      - {TRIGGER_PATHS[0]}\n"),
        ):
            token = f'      - "{TRIGGER_PATHS[0]}"\n'
            prefix, suffix = source.split(push_marker, 1)
            if event == "pull_request":
                mutated = prefix.replace(token, inserted + token, 1) + push_marker + suffix
            else:
                mutated = prefix + push_marker + suffix.replace(token, inserted + token, 1)
            if mutated == source:
                raise SystemExit(f"backup restore contracts CI addition fixture missing: {event} {label}")
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit(f"backup restore contracts CI accepted {event} addition: {label}")
    print("PASS: backup restore contracts CI trigger additions (8 event-specific semantic negatives)")



def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    for label, token, count in REQUIRED:
        if source.count(token) != count:
            raise SystemExit("backup restore contracts CI source drift: " + label)
    if check_blob:
        payload = source.encode("utf-8")
        blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
            raise SystemExit("backup restore contracts CI complete source drift")


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
            raise SystemExit("backup restore contracts CI runtime branch drift: " + label)
    print("PASS: backup restore contracts CI PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_branch_guards_runtime()
    cases = (
        ("checkout SHA", REQUIRED[0][1], "        uses: actions/checkout@v4\n"),
        ("setup SHA", REQUIRED[1][1], "        uses: actions/setup-python@v5\n"),
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
        ("injected executable action", "      - name: Compile validators and check shell\n", "      - uses: unreviewed/action@v1\n      - name: Compile validators and check shell\n"),
        ("removed PR self-trigger", "      - \"scripts/validate-memory-os-backup-restore-contracts-workflow-negative.py\"\n", ""),
    )
    blob_only = {"injected shell command", "injected executable action"}
    if len(cases) != 21 or sum(label in blob_only for label, _, _ in cases) != 2:
        raise SystemExit("backup restore contracts CI negative inventory drift")
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit("backup restore contracts CI negative anchor missing: " + label)
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated, check_blob=label in blob_only)
        except SystemExit:
            continue
        raise SystemExit("backup restore contracts CI accepted forbidden mutation: " + label)
    print(f"PASS: backup restore contracts CI source admission ({len(cases) - 2} semantic anchor + 2 blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
