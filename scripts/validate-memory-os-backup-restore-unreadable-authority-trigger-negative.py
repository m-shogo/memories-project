#!/usr/bin/env python3
"""Prove unreadable-authority readonly CI reaches every executed validator."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-unreadable-authority-readonly.yml"
SELF = "scripts/validate-memory-os-backup-restore-unreadable-authority-trigger-negative.py"
PROTECTED = (
    "scripts/validate-memory-os-*-load-negative.py",
    "scripts/validate-memory-os-*-writer-authority-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-writer-authority.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-transport-negative.py",
    SELF,
)
TRIGGER_PATHS = (
    ".github/workflows/backup-restore-unreadable-authority-readonly.yml",
    ".github/workflows/backup-restore-unreadable-authority-negative.yml",
    "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/production-operability-status.json",
    "scripts/validate-memory-os-*-load-negative.py",
    "scripts/validate-memory-os-*-writer-authority-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-writer-authority.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-transport-negative.py",
    "scripts/validate-memory-os-backup-restore-unreadable-authority-trigger-negative.py",
)
PR_MARKER = "  pull_request:\n    paths:\n"
PUSH_MARKER = "  push:\n    branches: [so]\n    paths:\n"
PERMISSIONS_MARKER = "\npermissions:\n"


def validate(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    if len(trigger_paths) != 16 or len(set(trigger_paths)) != 16:
        raise SystemExit("unreadable readonly trigger inventory shortened or duplicated")
    for marker in (PR_MARKER, PUSH_MARKER, PERMISSIONS_MARKER):
        if source.count(marker) != 1:
            raise SystemExit(f"unreadable readonly trigger marker drift: {marker.strip()}")
    pr = source.split(PR_MARKER, 1)[1].split(PUSH_MARKER, 1)[0]
    push = source.split(PUSH_MARKER, 1)[1].split(PERMISSIONS_MARKER, 1)[0]
    executed = re.findall(r"^          python (scripts/[A-Za-z0-9_-]+\.py)$", source, re.MULTILINE)
    if len(executed) != 11 or len(set(executed)) != 11 or SELF not in executed:
        raise SystemExit("unreadable readonly executable inventory drift")
    for event, block in (("pull_request", pr), ("push", push)):
        # Reject any unrecognized executable YAML line, including unquoted paths.
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        expected = tuple(f'      - "{path}"' for path in trigger_paths)
        if actual != expected:
            raise SystemExit(f"unreadable readonly {event} trigger inventory drift")
        paths = trigger_paths
        for path in trigger_paths:
            token = f'      - "{path}"\n'
            if block.count(token) != 1:
                raise SystemExit(f"unreadable readonly {event} missing or duplicate trigger: {path}")
        for executed_script in executed:
            if not any(fnmatch.fnmatchcase(executed_script, path) for path in paths):
                raise SystemExit(f"unreadable readonly {event} cannot reach executed script: {executed_script}")


SOURCE_REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup-python SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR checkout", "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR event", '          if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then\n', 1),
    ("PR head", '            expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("SHA format", '            [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("push event", '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then\n', 1),
    ("branch", '            test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("unreviewed event", '          else\n            echo "Unreviewed unreadable-authority readonly event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("runner invocation", '          python scripts/validate-memory-os-backup-restore-unreadable-authority-trigger-negative.py\n', 1),
)


def validate_source_admission(source: str) -> None:
    for label, token, expected in SOURCE_REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"unreadable readonly source admission drift: {label}")


def prove_source_admission_negatives(source: str) -> None:
    cases = (
        ("checkout SHA", SOURCE_REQUIRED[0][1], "      - uses: actions/checkout@v4\n"),
        ("setup-python SHA", SOURCE_REQUIRED[1][1], "      - uses: actions/setup-python@v5\n"),
        ("persist credentials", SOURCE_REQUIRED[2][1], ""),
        ("PR source checkout", SOURCE_REQUIRED[3][1], "          ref: ${{ github.sha }}\n"),
        ("PR event admission", SOURCE_REQUIRED[4][1], ""),
        ("PR head SHA", SOURCE_REQUIRED[5][1], '            expected="${GITHUB_SHA:-}"\n'),
        ("SHA format", SOURCE_REQUIRED[6][1], '            test -n "$expected"\n'),
        ("push event whitelist", SOURCE_REQUIRED[7][1], ""),
        ("push branch", SOURCE_REQUIRED[8][1], ""),
        ("unreviewed event rejection", SOURCE_REQUIRED[9][1], ""),
        ("source HEAD", SOURCE_REQUIRED[10][1], ""),
        ("clean source", SOURCE_REQUIRED[11][1], ""),
        ("runner invocation", SOURCE_REQUIRED[12][1], ""),
    )
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"unreadable readonly source negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate_source_admission(mutated)
        except SystemExit:
            continue
        raise SystemExit(f"unreadable readonly source admission accepted mutation: {label}")
    print(f"PASS: unreadable readonly source admission ({len(cases)} negatives)")




def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    for event in ("pull_request", "push"):
        for path in TRIGGER_PATHS:
            token = f'      - "{path}"\n'
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(PUSH_MARKER, 1)
                mutated = prefix + PUSH_MARKER + suffix.replace(token, "", 1)
            try:
                validate(mutated)
            except SystemExit:
                continue
            raise SystemExit(f"unreadable readonly accepted missing {event} trigger: {path}")
    # Check both events independently; no whole-file digest is involved.
    for event in ("pull_request", "push"):
        for label, inserted in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", f'      - "{TRIGGER_PATHS[0]}"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", f"      - {TRIGGER_PATHS[0]}\n"),
        ):
            token = f'      - "{TRIGGER_PATHS[0]}"\n'
            prefix, suffix = source.split(PUSH_MARKER, 1)
            if event == "pull_request":
                mutated = prefix.replace(token, inserted + token, 1) + PUSH_MARKER + suffix
            else:
                mutated = prefix + PUSH_MARKER + suffix.replace(token, inserted + token, 1)
            if mutated == source:
                raise SystemExit(f"unreadable readonly trigger addition fixture missing: {event} {label}")
            try:
                validate(mutated)
            except SystemExit:
                continue
            raise SystemExit(f"unreadable readonly accepted {event} trigger addition: {label}")
    print("PASS: unreadable readonly trigger additions (8 semantic event-specific negatives)")
    try:
        validate(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("unreadable readonly shortened trigger inventory accepted")
    print(f"PASS: unreadable readonly trigger reachability ({len(TRIGGER_PATHS) * 2} event-specific removal negatives; 1 shortened inventory negative; 11 executable scripts)")
    validate_source_admission(source)
    prove_source_admission_negatives(source)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
