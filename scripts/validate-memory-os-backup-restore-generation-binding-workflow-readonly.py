#!/usr/bin/env python3
"""Run the generation-binding read-only suite and prove canonical authority modes are immutable."""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITIES = (
    ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    ROOT / "contracts/operations/recovery-objectives-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    ROOT / "contracts/operations/operability-admission-inventory.v1.json",
    ROOT / "contracts/operations/production-operability-status.json",
)
SUITE = (
    ROOT / "scripts/validate-memory-os-recovery-objectives.py",
    ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-registry-aggregate-negative.py",
    ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py",
    ROOT / "scripts/validate-memory-os-backup-restore-generation-binding-negative.py",
    ROOT / "scripts/validate-memory-os-backup-restore-generation-status-authority-negative.py",
    ROOT / "scripts/reconcile-memory-os-backup-restore-generation-status.py",
    ROOT / "scripts/validate-memory-os-backup-restore.py",
    ROOT / "scripts/validate-memory-os-operability.py",
)


WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-binding-readonly.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "ee7b89b2efd9f5fc8b223c185e0e156b07a699f9"
TRIGGER_SCRIPTS = (Path(__file__).resolve(), *SUITE)
TRIGGER_PATHS = (
    ".github/workflows/backup-restore-generation-binding-readonly.yml",
    "scripts/validate-memory-os-backup-restore-generation-binding-workflow-readonly.py",
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-registry-aggregate-negative.py",
    "scripts/validate-memory-os-backup-restore.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-backup-restore-generation-binding.py",
    "scripts/validate-memory-os-backup-restore-generation-binding-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-status-authority-negative.py",
    "scripts/reconcile-memory-os-backup-restore-generation-status.py",
    "contracts/operations/**",
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Require both independent CI events to include every executed script."""
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit(f"generation-binding readonly trigger marker drift: {marker.strip()}")
    pr_block = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push_block = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    if len(trigger_paths) != 12 or len(set(trigger_paths)) != 12:
        raise SystemExit("generation-binding readonly trigger inventory shortened or duplicated")
    for event, block in (("pull_request", pr_block), ("push", push_block)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        expected = tuple(f'      - "{path}"' for path in trigger_paths)
        if actual != expected:
            raise SystemExit(f"generation-binding readonly {event} trigger inventory drift")
        for path in TRIGGER_SCRIPTS:
            token = f'      - "{path.relative_to(ROOT).as_posix()}"\n'
            if block.count(token) != 1:
                raise SystemExit(
                    f"generation-binding readonly {event} trigger missing or duplicate: {path.relative_to(ROOT)}"
                )


def prove_trigger_reachability_negatives(source: str) -> None:
    """Remove each protected path from each event independently; require rejection."""
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    for event in ("pull_request", "push"):
        for path in TRIGGER_SCRIPTS:
            token = f'      - "{path.relative_to(ROOT).as_posix()}"\n'
            if source.count(token) != 2:
                raise SystemExit(f"generation-binding trigger negative anchor drift: {path}")
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit(f"generation-binding trigger negative accepted: {event} {path}")
    print(f"PASS: generation-binding readonly trigger reachability ({len(TRIGGER_SCRIPTS) * 2} removal negatives)")
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
                raise SystemExit(f"generation-binding readonly missing addition fixture: {event} {label}")
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit(f"generation-binding readonly accepted {event} trigger addition: {label}")
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("generation-binding readonly shortened trigger inventory accepted")
    print("PASS: generation-binding readonly trigger additions (8 event-specific semantic negatives; 1 shortened inventory negative)")





SOURCE_REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup-python SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR checkout", "          ref: ${{ github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR event", '          if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then\n', 1),
    ("PR head", '            expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("SHA format", '            [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("event whitelist", '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n', 1),
    ("branch", '            test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("unreviewed event", '          else\n            echo "Unreviewed generation-binding readonly event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("runner invocation", '          python scripts/validate-memory-os-backup-restore-generation-binding-workflow-readonly.py\n', 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", '            test "${PR_BASE_REF:-}" = "so"\n', 1),
    ("root read-only permission", "permissions:\n  contents: read\n", 1),
    ("no contents write permission", "contents: write", 0),
)


def validate_source_admission(source: str, *, check_blob: bool = True) -> None:
    for label, token, expected in SOURCE_REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"generation-binding readonly source admission drift: {label}")
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if check_blob and hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
        raise SystemExit("generation-binding readonly complete workflow source drift")


def prove_source_admission_negatives(source: str) -> None:
    cases = (
        ("checkout SHA", SOURCE_REQUIRED[0][1], "      - uses: actions/checkout@v4\n"),
        ("setup-python SHA", SOURCE_REQUIRED[1][1], "      - uses: actions/setup-python@v5\n"),
        ("persist credentials", SOURCE_REQUIRED[2][1], ""),
        ("PR source checkout", SOURCE_REQUIRED[3][1], "          ref: ${{ github.sha }}\n"),
        ("PR event admission", SOURCE_REQUIRED[4][1], ""),
        ("PR head SHA", SOURCE_REQUIRED[5][1], '            expected="${GITHUB_SHA:-}"\n'),
        ("SHA format", SOURCE_REQUIRED[6][1], '            test -n "$expected"\n'),
        ("event whitelist", SOURCE_REQUIRED[7][1], ""),
        ("push/dispatch branch", SOURCE_REQUIRED[8][1], ""),
        ("unreviewed event rejection", SOURCE_REQUIRED[9][1], ""),
        ("source HEAD", SOURCE_REQUIRED[10][1], ""),
        ("clean source", SOURCE_REQUIRED[11][1], ""),
        ("runner invocation", SOURCE_REQUIRED[12][1], ""),
        ("PR target branch", SOURCE_REQUIRED[13][1], "  pull_request:\n    branches: [main]\n    paths:\n"),
        ("PR base environment", SOURCE_REQUIRED[14][1], ""),
        ("PR base assertion", SOURCE_REQUIRED[15][1], '            test -n "${PR_BASE_REF:-}"\n'),
        ("injected shell command", "          python scripts/validate-memory-os-backup-restore-generation-binding-workflow-readonly.py\n", "          echo UNREVIEWED\n          python scripts/validate-memory-os-backup-restore-generation-binding-workflow-readonly.py\n"),
        ("injected action", "      - name: Prove generation binding authorities remain read-only\n", "      - uses: unreviewed/action@v1\n      - name: Prove generation binding authorities remain read-only\n"),
        ("root permission escalation", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("job permission escalation", "jobs:\n  validate:\n", "jobs:\n  validate:\n    permissions:\n      contents: write\n"),
    )
    if len(cases) != 20:
        raise SystemExit("generation-binding readonly negative inventory drift")
    digest_only = frozenset({"injected shell command", "injected action"})
    semantic_count = 0
    blob_only_count = 0
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"generation-binding source negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        if mutated == source:
            raise SystemExit(f"generation-binding source mutation unchanged: {label}")
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in SOURCE_REQUIRED)
        if semantic == (label in digest_only):
            raise SystemExit("generation-binding readonly mutation classification drift: " + label)
        semantic_count += int(semantic)
        blob_only_count += int(not semantic)
        try:
            validate_source_admission(mutated, check_blob=not semantic)
        except SystemExit:
            continue
        raise SystemExit(f"generation-binding source admission accepted mutation: {label}")
    if (semantic_count, blob_only_count) != (18, 2):
        raise SystemExit("generation-binding readonly semantic/blob mutation coverage drift")
    print(f"PASS: generation-binding readonly source admission ({semantic_count} semantic; {blob_only_count} blob-only negatives)")




def prove_branch_guards_runtime() -> None:
    """Execute reviewed readonly branch predicates with disposable refs."""
    cases = (
        ("PR so", SOURCE_REQUIRED[15][1].strip(), "PR_BASE_REF", "so", True),
        ("PR main", SOURCE_REQUIRED[15][1].strip(), "PR_BASE_REF", "main", False),
        ("PR missing", SOURCE_REQUIRED[15][1].strip(), "PR_BASE_REF", "", False),
        ("push so", SOURCE_REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", SOURCE_REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", SOURCE_REQUIRED[8][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("generation-binding readonly runtime branch guard drift: " + label)
    print("PASS: generation-binding readonly PR/push branch guard runtime (6 cases)")


def snapshot() -> dict[Path, tuple[bytes, int]]:
    result: dict[Path, tuple[bytes, int]] = {}
    for path in AUTHORITIES:
        if not path.is_file():
            raise SystemExit(f"missing canonical authority: {path.relative_to(ROOT)}")
        result[path] = (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
    return result


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate_trigger_reachability(source)
    prove_trigger_reachability_negatives(source)
    validate_source_admission(source)
    prove_branch_guards_runtime()
    prove_source_admission_negatives(source)
    before = snapshot()
    for script in SUITE:
        subprocess.run(["python", str(script)], cwd=ROOT, check=True)
    after = snapshot()
    for path, (before_bytes, before_mode) in before.items():
        after_bytes, after_mode = after[path]
        if after_bytes != before_bytes:
            raise SystemExit(f"canonical authority bytes mutated: {path.relative_to(ROOT)}")
        if after_mode != before_mode:
            raise SystemExit(
                f"canonical authority mode mutated: {path.relative_to(ROOT)} "
                f"{before_mode:o}->{after_mode:o}"
            )
    print(f"PASS read-only: generation-binding suite preserved bytes/modes for {len(AUTHORITIES)} canonical authorities")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
