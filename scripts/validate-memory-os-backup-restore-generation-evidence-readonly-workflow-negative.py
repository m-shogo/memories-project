#!/usr/bin/env python3
"""Fail-closed whole-source and runtime negatives for generation evidence readonly CI."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-evidence-readonly.yml"
EXTERNAL_PERMISSION_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-permission-negative.py"
REVIEWED_WORKFLOW_BLOB_SHA = "4f3974d40145a61176ea4de7f302568cbf6c782f"

TRIGGER_PATHS = (
    ".github/workflows/backup-restore-generation-evidence-readonly.yml",
    ".github/workflows/backup-restore-generation-evidence.yml",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-permission-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-readonly-workflow-negative.py",
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/production-operability-status.json",
)
REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR checkout", "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR event", "          if [[ \"${GITHUB_EVENT_NAME:-}\" == \"pull_request\" ]]; then\n", 1),
    ("PR head", "            pr_head=\"${{ github.event.pull_request.head.sha }}\"\n", 1),
    ("PR SHA format", "            [[ \"$pr_head\" =~ ^[0-9a-f]{40}$ ]]\n", 1),
    ("push/dispatch branch", "            test \"${GITHUB_REF:-}\" = \"refs/heads/so\"\n", 2),
    ("unreviewed event", "          else\n            echo \"Unreviewed generation readonly CI event\" >&2\n            exit 1\n          fi\n", 1),
    ("expected SHA format", "          [[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]\n", 1),
    ("HEAD identity", "          test \"$(git rev-parse HEAD)\" = \"$expected\"\n", 1),
    ("clean source", "          test -z \"$(git status --porcelain)\"\n", 2),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", "            test \"${PR_BASE_REF:-}\" = \"so\"\n", 1),
    ("self-trigger", "      - \"scripts/validate-memory-os-backup-restore-generation-evidence-readonly-workflow-negative.py\"\n", 2),
    ("self-execution", "          python scripts/validate-memory-os-backup-restore-generation-evidence-readonly-workflow-negative.py\n", 1),
    ("read-only token", "permissions:\n  contents: read\n", 1),
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Pin generation recovery evidence CI trigger paths in PR and push separately."""
    if len(trigger_paths) != 17 or len(set(trigger_paths)) != 17:
        raise SystemExit("generation evidence readonly trigger inventory drift")
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("generation evidence readonly trigger marker drift")
    pr_block = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push_block = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    expected = ['      - "' + path + '"' for path in trigger_paths]
    for event, block in (("pull_request", pr_block), ("push", push_block)):
        actual = [line for line in block.splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
        if actual != expected:
            raise SystemExit("generation evidence readonly " + event + " exact trigger inventory drift")


def prove_trigger_reachability_negatives(source: str) -> None:
    """Prove one-event path removals and shortened inventories fail semantically."""
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    for event in ("pull_request", "push"):
        for path in TRIGGER_PATHS:
            token = '      - "' + path + '"\n'
            if source.count(token) != 2:
                raise SystemExit("generation evidence readonly trigger negative anchor drift: " + path)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("generation evidence readonly trigger negative accepted: " + event + " " + path)
    # A complete-source digest rejects additions, but these mutations prove
    # that the event-specific semantic guard also rejects extra or duplicate paths.
    for event, marker in (
        ("pull_request", "  pull_request:\n    branches: [so]\n    paths:\n"),
        ("push", push_marker),
    ):
        for label, injected in (
            ("unreviewed path", '      - "unreviewed/**"\n'),
            ("duplicate path", '      - "' + TRIGGER_PATHS[0] + '"\n'),
        ):
            if source.count(marker) != 1:
                raise SystemExit("generation evidence readonly addition fixture marker drift")
            mutated = source.replace(marker, marker + injected, 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("generation evidence readonly extra trigger accepted: " + event + " " + label)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("generation evidence readonly shortened trigger inventory accepted")
    print(f"PASS: generation evidence readonly PR/push trigger reachability ({len(TRIGGER_PATHS) * 2} semantic removal negatives; 1 shortened inventory negative)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    for label, token, count in REQUIRED:
        if source.count(token) != count:
            raise SystemExit("generation evidence readonly source drift: " + label)
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if check_blob and hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
        raise SystemExit("generation evidence readonly complete source drift")


def require_external_reviewed_binding(source: str) -> None:
    """Reject stale independent generation permission CI workflow digests."""
    matches = re.findall(
        r'^REVIEWED_READONLY_WORKFLOW_BLOB_SHA = "([0-9a-f]{40})"$',
        source,
        flags=re.MULTILINE,
    )
    if matches != [REVIEWED_WORKFLOW_BLOB_SHA]:
        raise SystemExit("generation evidence readonly external permission digest drift")


def prove_branch_guards_runtime() -> None:
    cases = (
        ("PR so", REQUIRED[14][1].strip(), "PR_BASE_REF", "so", True),
        ("PR main", REQUIRED[14][1].strip(), "PR_BASE_REF", "main", False),
        ("PR missing", REQUIRED[14][1].strip(), "PR_BASE_REF", "", False),
        ("push so", REQUIRED[7][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", REQUIRED[7][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", REQUIRED[7][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("generation evidence readonly branch runtime drift: " + label)
    print("PASS: generation evidence readonly PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    external = EXTERNAL_PERMISSION_VALIDATOR.read_text(encoding="utf-8")
    require_external_reviewed_binding(external)
    mutated_external = external.replace(REVIEWED_WORKFLOW_BLOB_SHA, "0" * 40, 1)
    if mutated_external == external:
        raise SystemExit("generation evidence readonly external binding fixture drift")
    try:
        require_external_reviewed_binding(mutated_external)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation evidence readonly accepted stale external digest")
    prove_branch_guards_runtime()
    cases = (
        ("checkout SHA", REQUIRED[0][1], "      - uses: actions/checkout@v4\n"),
        ("setup SHA", REQUIRED[1][1], "      - uses: actions/setup-python@v5\n"),
        ("no credentials", REQUIRED[2][1], ""),
        ("PR checkout", REQUIRED[3][1], "          ref: ${{ github.sha }}\n"),
        ("PR event", REQUIRED[4][1], ""),
        ("PR head", REQUIRED[5][1], "            pr_head=\"${GITHUB_SHA:-}\"\n"),
        ("PR SHA format", REQUIRED[6][1], "            test -n \"$pr_head\"\n"),
        ("push/dispatch branch", REQUIRED[7][1], ""),
        ("unreviewed event", REQUIRED[8][1], ""),
        ("expected SHA format", REQUIRED[9][1], "          test -n \"$expected\"\n"),
        ("HEAD identity", REQUIRED[10][1], ""),
        ("clean source", REQUIRED[11][1], ""),
        ("PR target", REQUIRED[12][1], "  pull_request:\n    branches: [main]\n    paths:\n"),
        ("PR base environment", REQUIRED[13][1], ""),
        ("PR base assertion", REQUIRED[14][1], "            test -n \"${PR_BASE_REF:-}\"\n"),
        ("self-trigger", REQUIRED[15][1], ""),
        ("self-execution", REQUIRED[16][1], ""),
        ("read-only token", REQUIRED[17][1], "permissions:\n  contents: write\n"),
        ("injected shell command", "          python scripts/validate-memory-os-backup-restore-generation-evidence.py\n", "          echo UNREVIEWED\n          python scripts/validate-memory-os-backup-restore-generation-evidence.py\n"),
        ("injected executable action", "      - name: Prove generation evidence authorities are byte and mode immutable\n", "      - uses: unreviewed/action@v1\n      - name: Prove generation evidence authorities are byte and mode immutable\n"),
        ("removed push self-trigger", "      - \"scripts/validate-memory-os-backup-restore-generation-evidence-readonly-workflow-negative.py\"\n", ""),
    )
    # Preserve the distinction between independently proven REQUIRED anchors
    # and the two anchor-preserving executable injections bound by Git blob.
    digest_only = frozenset({"injected shell command", "injected executable action"})
    if len(cases) != 21:
        raise SystemExit("generation evidence readonly mutation inventory drift")
    semantic_count = 0
    blob_only_count = 0
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit("generation evidence readonly negative anchor missing: " + label)
        mutated = source.replace(old, replacement, 1)
        if mutated == source:
            raise SystemExit("generation evidence readonly mutation unchanged: " + label)
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in REQUIRED)
        if semantic == (label in digest_only):
            raise SystemExit("generation evidence readonly mutation classification drift: " + label)
        semantic_count += int(semantic)
        blob_only_count += int(not semantic)
        try:
            validate(mutated, check_blob=not semantic)
        except SystemExit:
            continue
        raise SystemExit("generation evidence readonly accepted forbidden mutation: " + label)
    if (semantic_count, blob_only_count) != (19, 2):
        raise SystemExit("generation evidence readonly semantic/blob mutation coverage drift")
    print(f"PASS: generation evidence readonly workflow source admission ({semantic_count} semantic; {blob_only_count} blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
