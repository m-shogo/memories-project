#!/usr/bin/env python3
"""Fail-closed source-admission negatives for typed non-resurrection path CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-non-resurrection-path-negative.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "3ef2ff4b3682e312351c655c50bbda3595ce1bc6"

TRIGGER_PATHS = (
    ".github/workflows/backup-restore-non-resurrection-path-negative.yml",
    "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
    "scripts/register-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-contract-path-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-path-workflow-negative.py",
)
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
    ("unreviewed event", '          else\n            echo "Unreviewed typed non-resurrection path negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"', 3),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-non-resurrection-path-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-non-resurrection-path-workflow-negative.py\n', 1),
    ("PR base ref", '            test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR target filter", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
)



def validate_trigger_reachability(
    source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS
) -> None:
    """Pin every reviewed typed non-resurrection path CI trigger in each event."""
    if len(trigger_paths) != 10 or len(set(trigger_paths)) != 10:
        raise SystemExit("typed non-resurrection path CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("typed non-resurrection path CI trigger marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    for event, block in (("pull_request", pr), ("push", push)):
        # Reject all unknown executable YAML lines, including unquoted paths.
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        expected = tuple(f'      - "{item}"' for item in trigger_paths)
        if actual != expected:
            raise SystemExit("typed non-resurrection path CI " + event + " trigger inventory drift")
        for item in trigger_paths:
            if block.count('      - "' + item + '"' + chr(10)) != 1:
                raise SystemExit("typed non-resurrection path CI " + event + " trigger path drift: " + item)


def prove_trigger_reachability_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for item in TRIGGER_PATHS:
            token = '      - "' + item + '"' + chr(10)
            if source.count(token) != 2:
                raise SystemExit("typed non-resurrection path CI trigger mutation anchor drift: " + item)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("typed non-resurrection path CI accepted missing " + event + " trigger: " + item)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("typed non-resurrection path CI shortened trigger inventory accepted")
    for event in ("pull_request", "push"):
        first = '      - "' + TRIGGER_PATHS[0] + '"' + chr(10)
        prefix, suffix = source.split(push_marker, 1)
        for label, inserted in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", first),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", "      - " + TRIGGER_PATHS[0] + "\n"),
        ):
            mutated = (
                prefix.replace(first, inserted + first, 1) + push_marker + suffix
                if event == "pull_request"
                else prefix + push_marker + suffix.replace(first, inserted + first, 1)
            )
            if mutated == source:
                raise SystemExit("typed non-resurrection path CI addition fixture missing: " + event + " " + label)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("typed non-resurrection path CI accepted " + event + " trigger addition: " + label)
    print("PASS: typed non-resurrection path CI event-specific triggers (20 removals; 8 additions; 1 shortened inventory negative)")



def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"typed non-resurrection path workflow source boundary drift: {label}")


    if not source.rstrip().endswith('          test -z "$(git status --porcelain)"'):
        raise SystemExit("typed non-resurrection path workflow source boundary drift: final read-only terminator")
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("typed non-resurrection path workflow complete source blob drift")


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
            raise SystemExit("typed non-resurrection path runtime branch guard drift: " + label)
    print("PASS: typed non-resurrection path PR/push branch guard runtime (6 cases)")


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
    )
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"typed non-resurrection path negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit(f"typed non-resurrection path accepted forbidden mutation: {label}")
    # The canonical workflow may or may not end in a newline; both are valid.
    validate(source.rstrip("\n") + "\n", check_blob=False)
    try:
        validate(source + '\n          echo "unreviewed final command"\n')
    except SystemExit:
        pass
    else:
        raise SystemExit("typed non-resurrection path accepted appended final command")
    for label, old, replacement in (
        ("PR base ref", REQUIRED[14][1], ""),
        ("PR target filter", REQUIRED[15][1], "  pull_request:\n    paths:\n"),
    ):
        if old not in source:
            raise SystemExit("typed non-resurrection path PR branch negative anchor missing: " + label)
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit("typed non-resurrection path accepted forbidden PR branch mutation: " + label)
    # Whole-source binding rejects otherwise anchor-preserving workflow changes.
    for label, mutated in (
        ("extra executable step", source.replace(
            "      - name: Validate typed admission path negatives\n",
            "      - run: echo unreviewed\n      - name: Validate typed admission path negatives\n", 1)),
        ("missing domain trigger", source.replace(
            '      - "scripts/validate-memory-os-backup-restore-non-resurrection-contract-path-negative.py"\n',
            "", 1)),
    ):
        if mutated == source:
            raise SystemExit("typed non-resurrection path source digest negative anchor missing: " + label)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit("typed non-resurrection path accepted whole-source mutation: " + label)
    print(f"PASS: typed non-resurrection path workflow source admission ({len(cases) + 5} negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
