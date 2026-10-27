#!/usr/bin/env python3
"""Fail-closed source-admission negatives for admission linkage readonly CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/admission-authority-linkage-readonly.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "75c9b02517a27f273f47d72ac18bee6a272bcad8"

TRIGGER_PATHS = (
    ".github/workflows/admission-authority-linkage-readonly.yml",
    ".github/workflows/admission-authority-linkage.yml",
    "contracts/operations/requests/admission-authority-linkage.v1.json",
    "contracts/operations/*admission-contract.v1.json",
    "contracts/operations/release-baseline-registry-contract.v1.json",
    "contracts/operations/release-compatibility-pair-contract.v1.json",
    "contracts/operations/incident-human-tabletop-evidence-contract.v1.json",
    "contracts/operations/deletion-worker-host-failure-contract.v1.json",
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "contracts/operations/client-baseline-registry-contract.v1.json",
    "contracts/operations/observability-stack-deployment-contract.v1.json",
    "contracts/operations/production-shaped-failure-drill-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "scripts/validate-memory-os-admission-authority-linkage.py",
    "scripts/validate-memory-os-admission-authority-linkage-negative.py",
    "scripts/validate-memory-os-admission-authority-linkage-readonly-workflow-negative.py",
)
REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup-python SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR checkout", "          ref: ${{ github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR event", '          if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then\n', 1),
    ("PR head", '            expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("SHA format", '            [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("event whitelist", '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n', 1),
    ("branch", '            test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("unreviewed event", '          else\n            echo "Unreviewed admission linkage readonly event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-admission-authority-linkage-readonly-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-admission-authority-linkage-readonly-workflow-negative.py\n', 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", '            test "${PR_BASE_REF:-}" = "so"\n', 1),
    ("root read-only permission", "permissions:\n  contents: read\n", 1),
    ("no contents write permission", "contents: write", 0),
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Prove every reviewed executable and authority path reaches both CI events."""
    if len(trigger_paths) != 16 or len(set(trigger_paths)) != 16:
        raise SystemExit("admission linkage readonly trigger inventory drift")
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("admission linkage readonly trigger marker drift")
    pr_block = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push_block = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    for event, block in (("pull_request", pr_block), ("push", push_block)):
        for path in trigger_paths:
            token = '      - "' + path + '"\n'
            if block.count(token) != 1:
                raise SystemExit("admission linkage readonly " + event + " trigger drift: " + path)


def prove_trigger_reachability_negatives(source: str) -> None:
    """Delete one path in only one event, independently of the source digest."""
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    for event in ("pull_request", "push"):
        for path in TRIGGER_PATHS:
            token = '      - "' + path + '"\n'
            if source.count(token) != 2:
                raise SystemExit("admission linkage readonly trigger negative anchor drift: " + path)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("admission linkage readonly trigger negative accepted: " + event + " " + path)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("admission linkage readonly shortened trigger inventory accepted")
    print(f"PASS: admission linkage readonly PR/push trigger reachability ({len(TRIGGER_PATHS) * 2} semantic removal negatives; 1 shortened inventory negative)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"admission linkage readonly workflow source boundary drift: {label}")
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if check_blob and hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
        raise SystemExit("admission linkage readonly complete workflow source drift")


def prove_branch_guards_runtime() -> None:
    """Execute exact reviewed PR and push predicates under synthetic refs."""
    cases = (
        ("PR so", REQUIRED[16][1].strip(), "PR_BASE_REF", "so", True),
        ("PR main", REQUIRED[16][1].strip(), "PR_BASE_REF", "main", False),
        ("PR missing", REQUIRED[16][1].strip(), "PR_BASE_REF", "", False),
        ("push so", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("admission linkage readonly runtime branch guard drift: " + label)
    print("PASS: admission linkage readonly PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_branch_guards_runtime()
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
        ("PR target", REQUIRED[14][1], "  pull_request:\n    branches: [main]\n    paths:\n"),
        ("PR base environment", REQUIRED[15][1], ""),
        ("PR base assertion", REQUIRED[16][1], '            test -n "${PR_BASE_REF:-}"\n'),
        ("injected shell", "          python scripts/validate-memory-os-admission-authority-linkage-readonly-workflow-negative.py\n", "          echo UNREVIEWED\n          python scripts/validate-memory-os-admission-authority-linkage-readonly-workflow-negative.py\n"),
        ("injected action", "      - name: Validate linkage chain\n", "      - uses: unreviewed/action@v1\n      - name: Validate linkage chain\n"),
        ("removed PR self-trigger", '      - "scripts/validate-memory-os-admission-authority-linkage-readonly-workflow-negative.py"\n', ""),
        ("root permission escalation", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("job permission escalation", "jobs:\n  prove-readonly:\n", "jobs:\n  prove-readonly:\n    permissions:\n      contents: write\n"),
    )
    if len(cases) != 22:
        raise SystemExit("admission linkage readonly negative inventory drift")
    digest_only = frozenset({"injected shell", "injected action"})
    semantic_count = 0
    blob_only_count = 0
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"admission linkage readonly negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        if mutated == source:
            raise SystemExit(f"admission linkage readonly mutation unchanged: {label}")
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in REQUIRED)
        if semantic == (label in digest_only):
            raise SystemExit("admission linkage readonly mutation classification drift: " + label)
        semantic_count += int(semantic)
        blob_only_count += int(not semantic)
        try:
            validate(mutated, check_blob=not semantic)
        except SystemExit:
            continue
        raise SystemExit(f"admission linkage readonly accepted forbidden mutation: {label}")
    if (semantic_count, blob_only_count) != (20, 2):
        raise SystemExit("admission linkage readonly semantic/blob mutation coverage drift")
    print(f"PASS: admission linkage readonly workflow source admission ({semantic_count} semantic; {blob_only_count} blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
