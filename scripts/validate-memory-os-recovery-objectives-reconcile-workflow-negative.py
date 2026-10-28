#!/usr/bin/env python3
"""Fail-closed source-admission negatives for recovery objective reconcile CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/recovery-objectives-reconcile-negative.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "961682b5235ac5a88ae29fb95a0ed3f5abd3d862"
TRIGGER_PATHS = (
    ".github/workflows/recovery-objectives-reconcile-negative.yml",
    "scripts/reconcile-memory-os-recovery-objectives.py",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/register-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-recovery-objectives-negative.py",
    "scripts/validate-memory-os-recovery-objectives-reconcile-negative.py",
    "scripts/validate-memory-os-recovery-objectives-reconcile-workflow-negative.py",
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/production-operability-status.json",
)
PR_MARKER = "  pull_request:\n    branches: [so]\n    paths:\n"
PUSH_MARKER = "  push:\n    branches:\n      - so\n    paths:\n"
DISPATCH_MARKER = "  workflow_dispatch:\n"
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
    ("unreviewed event", '          else\n            echo "Unreviewed recovery objective reconcile negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-recovery-objectives-reconcile-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-recovery-objectives-reconcile-workflow-negative.py\n', 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", '            test "${PR_BASE_REF:-}" = "so"\n', 1),
)


def validate_trigger_reachability(
    source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS
) -> None:
    """Admit only the exact reviewed, ordered PR and push path inventories."""
    if any(source.count(marker) != 1 for marker in (PR_MARKER, PUSH_MARKER, DISPATCH_MARKER)):
        raise SystemExit("recovery objective reconcile CI event marker drift")
    if not (source.index(PR_MARKER) < source.index(PUSH_MARKER) < source.index(DISPATCH_MARKER)):
        raise SystemExit("recovery objective reconcile CI event order drift")
    pr = source.split(PR_MARKER, 1)[1].split(PUSH_MARKER, 1)[0]
    push = source.split(PUSH_MARKER, 1)[1].split(DISPATCH_MARKER, 1)[0]
    expected = tuple(f'      - "{path}"' for path in trigger_paths)
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if actual != expected:
            raise SystemExit(f"recovery objective reconcile CI {event} trigger inventory drift")


def validate(
    source: str, *, check_blob: bool = True,
    trigger_paths: tuple[str, ...] = TRIGGER_PATHS,
) -> None:
    validate_trigger_reachability(source, trigger_paths=trigger_paths)
    validate_yaml_authority(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"recovery objective reconcile workflow source boundary drift: {label}")
    if check_blob:
        payload = source.encode("utf-8")
        blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
            raise SystemExit("recovery objective reconcile complete workflow source drift")


def validate_yaml_authority(source: str) -> None:
    """Pin recovery objective reconcile event/root/permission semantics independently."""
    paths = "".join('      - "' + path + '"\n' for path in TRIGGER_PATHS)
    expected_header = (
        "name: Recovery Objectives Reconcile Negative\n\non:\n"
        + PR_MARKER + paths + PUSH_MARKER + paths + DISPATCH_MARKER
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("recovery objective reconcile CI exact event header drift")
    roots = [
        row for row in source.splitlines()
        if row.strip() and not row[0].isspace()
        and not row.lstrip().startswith("#")
    ]
    if roots != [
        "name: Recovery Objectives Reconcile Negative",
        "on:", "permissions:", "jobs:",
    ]:
        raise SystemExit("recovery objective reconcile CI root YAML key shadow drift")
    leaves = []
    for row in source.split("\npermissions:\n", 1)[1].splitlines():
        if row.strip() and not row[0].isspace():
            break
        if row.strip() and not row.lstrip().startswith("#"):
            leaves.append(row)
    if leaves != ["  contents: read"]:
        raise SystemExit("recovery objective reconcile CI permission leaf shadow drift")


def prove_yaml_authority_negatives(source: str) -> None:
    validate_yaml_authority(source)
    extra = source.replace("on:\n", "on:\n  issues:\n", 1)
    if extra == source:
        raise SystemExit("recovery objective reconcile CI event fixture anchor drift")
    cases = [("extra event", extra, "exact event header drift")]
    for label, suffix in (
        ("spaced on", "on :\n  issues:\n"),
        ("quoted on", "'on':\n  issues:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("quoted permissions", "'permissions':\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
        ("quoted jobs", "'jobs': {}\n"),
    ):
        cases.append((label, source + "\n" + suffix, "root YAML key shadow drift"))
    anchor = "\npermissions:\n  contents: read\n"
    if source.count(anchor) != 1:
        raise SystemExit("recovery objective reconcile CI permission fixture anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(anchor, anchor + leaf, 1),
                      "permission leaf shadow drift"))
    if len(cases) != 9:
        raise SystemExit("recovery objective reconcile CI YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("recovery objective reconcile CI unchanged YAML negative: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "recovery objective reconcile CI " + diagnostic
            if str(exc) != expected:
                raise SystemExit("recovery objective reconcile CI wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("recovery objective reconcile CI accepted YAML mutation: " + label)
    print("PASS: recovery objective reconcile CI YAML event/root/permission authority (9 exact-diagnostic negatives)")



def prove_trigger_reachability_negatives(source: str) -> None:
    """Prove event-specific removals, additions and inventory shortening without a blob check."""
    anchor = f'      - "{TRIGGER_PATHS[0]}"\n'
    for event in ("pull_request", "push"):
        prefix, suffix = source.split(PUSH_MARKER, 1)
        for path in TRIGGER_PATHS:
            token = f'      - "{path}"\n'
            mutated = (
                prefix.replace(token, "", 1) + PUSH_MARKER + suffix
                if event == "pull_request"
                else prefix + PUSH_MARKER + suffix.replace(token, "", 1)
            )
            if mutated == source:
                raise SystemExit(f"recovery objective reconcile CI removal fixture missing: {event} {path}")
            try:
                validate(mutated, check_blob=False)
            except SystemExit:
                pass
            else:
                raise SystemExit(f"recovery objective reconcile CI accepted {event} trigger removal: {path}")
        for label, injected in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", anchor),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", f"      - {TRIGGER_PATHS[0]}\n"),
        ):
            mutated = (
                prefix.replace(anchor, injected + anchor, 1) + PUSH_MARKER + suffix
                if event == "pull_request"
                else prefix + PUSH_MARKER + suffix.replace(anchor, injected + anchor, 1)
            )
            if mutated == source:
                raise SystemExit(f"recovery objective reconcile CI addition fixture missing: {event} {label}")
            try:
                validate(mutated, check_blob=False)
            except SystemExit:
                pass
            else:
                raise SystemExit(f"recovery objective reconcile CI accepted {event} trigger addition: {label}")
    try:
        validate(source, check_blob=False, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("recovery objective reconcile CI shortened trigger inventory accepted")
    print("PASS: recovery objective reconcile CI event triggers (22 removals; 8 additions; 1 shortened inventory)")


def prove_branch_guards_runtime() -> None:
    """Execute reviewed PR and push predicates with synthetic refs."""
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
            raise SystemExit("recovery objective reconcile runtime branch guard drift: " + label)
    print("PASS: recovery objective reconcile PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_yaml_authority_negatives(source)
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
        ("injected shell", "          python scripts/validate-memory-os-recovery-objectives-reconcile-workflow-negative.py\n", "          echo UNREVIEWED\n          python scripts/validate-memory-os-recovery-objectives-reconcile-workflow-negative.py\n"),
        ("injected action", "      - name: Prove transactional recovery-objective reconciliation\n", "      - uses: unreviewed/action@v1\n      - name: Prove transactional recovery-objective reconciliation\n"),
        ("removed PR self-trigger", '      - "scripts/validate-memory-os-recovery-objectives-reconcile-workflow-negative.py"\n', ""),
    )
    blob_only = {"injected shell", "injected action"}
    if len(cases) != 20 or sum(label in blob_only for label, _, _ in cases) != 2:
        raise SystemExit("recovery objective reconcile negative inventory drift")
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"recovery objective reconcile negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated, check_blob=label in blob_only)
        except SystemExit:
            continue
        raise SystemExit(f"recovery objective reconcile accepted forbidden mutation: {label}")
    print(f"PASS: recovery objective reconcile workflow source admission ({len(cases) - 2} semantic anchor + 2 blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
