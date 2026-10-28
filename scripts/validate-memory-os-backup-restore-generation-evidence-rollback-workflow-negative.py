#!/usr/bin/env python3
"""Fail-closed source-admission negatives for generation rollback diagnostics CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-evidence-rollback-diagnostics-negative.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "79ad7da92fc35fdec16f69e9b7b432ba669ad886"

TRIGGER_PATHS = (
    ".github/workflows/backup-restore-generation-evidence-rollback-diagnostics-negative.yml",
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/reconcile-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-generation-binding.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-rollback-diagnostics-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-rollback-workflow-negative.py",
)
REQUIRED = (
    ("checkout SHA", "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup-python SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR checkout", "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR event", '          if [[ "${GITHUB_EVENT_NAME:-}" == "pull_request" ]]; then\n', 1),
    ("PR head", '            expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("SHA format", '            [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("event whitelist", '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n', 1),
    ("branch", '            test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("unreviewed event", '          else\n            echo "Unreviewed generation rollback diagnostics negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-generation-evidence-rollback-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-generation-evidence-rollback-workflow-negative.py\n', 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", '            test "${PR_BASE_REF:-}" = "so"\n', 1),
    ("read-only token", "permissions:\n  contents: read\n", 1),
    ("no job write token", "      contents: write\n", 0),
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Pin rollback diagnostics CI event-specific paths including list-style push branch."""
    if len(trigger_paths) != 16 or len(set(trigger_paths)) != 16:
        raise SystemExit("generation rollback diagnostics trigger inventory drift")
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("generation rollback diagnostics trigger marker drift")
    pr_block = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push_block = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    expected = ['      - "' + path + '"' for path in trigger_paths]
    for event, block in (("pull_request", pr_block), ("push", push_block)):
        actual = [line for line in block.splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
        if actual != expected:
            raise SystemExit("generation rollback diagnostics " + event + " exact trigger inventory drift")


def validate_yaml_authority(source: str) -> None:
    """Pin rollback CI event, root mapping and read-only permission leaf independently."""
    paths = "".join('      - "' + path + '"\n' for path in TRIGGER_PATHS)
    expected_header = (
        "name: Backup Restore Generation Evidence Rollback Diagnostics Negative\n\non:\n"
        + "  pull_request:\n    branches: [so]\n    paths:\n" + paths
        + "  push:\n    branches:\n      - so\n    paths:\n" + paths
        + "  workflow_dispatch:\n"
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("generation rollback diagnostics exact event header drift")
    roots = [
        row for row in source.splitlines()
        if row.strip() and not row[0].isspace()
        and not row.lstrip().startswith("#")
    ]
    if roots != [
        "name: Backup Restore Generation Evidence Rollback Diagnostics Negative",
        "on:", "permissions:", "jobs:",
    ]:
        raise SystemExit("generation rollback diagnostics root YAML key shadow drift")
    leaves = []
    for row in source.split("\npermissions:\n", 1)[1].splitlines():
        if row.strip() and not row[0].isspace():
            break
        if row.strip() and not row.lstrip().startswith("#"):
            leaves.append(row)
    if leaves != ["  contents: read"]:
        raise SystemExit("generation rollback diagnostics permission leaf shadow drift")
    body = source.split("\n" + "jobs:\n", 1)[1]
    job_rows = [
        line for line in body.splitlines()
        if line.startswith("  ") and not line.startswith("   ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_rows != ["  validate:"]:
        raise SystemExit("generation rollback diagnostics job mapping shadow drift")
    job_keys = [
        line for line in body.splitlines()
        if line.startswith("    ") and not line.startswith("     ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_keys != ["    runs-on: ubuntu-latest", "    steps:"]:
        raise SystemExit("generation rollback diagnostics job key/permission shadow drift")


def prove_yaml_authority_negatives(source: str) -> None:
    validate_yaml_authority(source)
    extra_event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if extra_event == source:
        raise SystemExit("generation rollback diagnostics event negative anchor drift")
    cases = [("extra event", extra_event, "exact event header drift")]
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
        raise SystemExit("generation rollback diagnostics permission negative anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(anchor, anchor + leaf, 1),
                      "permission leaf shadow drift"))
    for label, suffix in (
        ("duplicate job", "  validate: {}\n"),
        ("spaced job", "  validate : {}\n"),
        ("quoted job", "  'validate': {}\n"),
    ):
        cases.append((label, source.rstrip("\n") + "\n" + suffix,
                      "job mapping shadow drift"))
    runs_on = "    runs-on: ubuntu-latest\n"
    if source.count(runs_on) != 1:
        raise SystemExit("generation rollback diagnostics job permission fixture anchor drift")
    for label, leaf in (
        ("job permission", "    permissions:\n      contents: write\n"),
        ("spaced job permission", "    permissions :\n      contents: write\n"),
        ("quoted job permission", "    'permissions':\n      contents: write\n"),
    ):
        cases.append((label, source.replace(runs_on, runs_on + leaf, 1),
                      "job key/permission shadow drift"))
    if len(cases) != 15:
        raise SystemExit("generation rollback diagnostics YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("generation rollback diagnostics unchanged YAML negative: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "generation rollback diagnostics " + diagnostic
            if str(exc) != expected:
                raise SystemExit("generation rollback diagnostics wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("generation rollback diagnostics accepted YAML mutation: " + label)
    print("PASS: generation rollback diagnostics YAML event/root/job/permission authority (15 exact-diagnostic negatives)")



def prove_trigger_reachability_negatives(source: str) -> None:
    """Prove event-specific removal and shortened inventory rejection without digest."""
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for path in TRIGGER_PATHS:
            token = '      - "' + path + '"\n'
            if source.count(token) != 2:
                raise SystemExit("generation rollback diagnostics trigger negative anchor drift: " + path)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("generation rollback diagnostics trigger negative accepted: " + event + " " + path)
    # Prove additions and duplicates fail without the complete-workflow digest.
    for event, marker in (
        ("pull_request", "  pull_request:\n    branches: [so]\n    paths:\n"),
        ("push", push_marker),
    ):
        for label, injected in (
            ("quoted unreviewed path", '      - "unreviewed/**"\n'),
            ("quoted duplicate path", '      - "' + TRIGGER_PATHS[0] + '"\n'),
            ("unquoted unreviewed path", "      - unreviewed/**\n"),
            ("unquoted duplicate path", "      - " + TRIGGER_PATHS[0] + "\n"),
        ):
            if source.count(marker) != 1:
                raise SystemExit("generation rollback diagnostics addition fixture marker drift")
            mutated = source.replace(marker, marker + injected, 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("generation rollback diagnostics extra trigger accepted: " + event + " " + label)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("generation rollback diagnostics shortened trigger inventory accepted")
    print(f"PASS: generation rollback diagnostics PR/push trigger reachability ({len(TRIGGER_PATHS) * 2} semantic removal negatives; 8 event-specific addition negatives; 1 shortened inventory negative)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    validate_yaml_authority(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"generation rollback diagnostics workflow source boundary drift: {label}")
    if check_blob:
        payload = source.encode("utf-8")
        blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
            raise SystemExit("generation rollback diagnostics complete workflow source drift")


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
            raise SystemExit("generation rollback diagnostics runtime branch guard drift: " + label)
    print("PASS: generation rollback diagnostics PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_yaml_authority_negatives(source)
    prove_branch_guards_runtime()
    cases = (
        ("checkout SHA", REQUIRED[0][1], "        uses: actions/checkout@v4\n"),
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
        ("read-only token", REQUIRED[17][1], "permissions:\n  contents: write\n"),
        ("injected shell", "          python scripts/validate-memory-os-backup-restore-generation-evidence-rollback-workflow-negative.py\n", "          echo UNREVIEWED\n          python scripts/validate-memory-os-backup-restore-generation-evidence-rollback-workflow-negative.py\n"),
        ("injected action", "      - name: Compile generation evidence rollback diagnostics negative\n", "      - uses: unreviewed/action@v1\n      - name: Compile generation evidence rollback diagnostics negative\n"),
        ("removed PR self-trigger", '      - "scripts/validate-memory-os-backup-restore-generation-evidence-rollback-workflow-negative.py"\n', ""),
    )
    blob_only = {"injected shell", "injected action"}
    if len(cases) != 21 or sum(label in blob_only for label, _, _ in cases) != 2:
        raise SystemExit("generation rollback diagnostics negative inventory drift")
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"generation rollback diagnostics negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in REQUIRED)
        if semantic == (label in blob_only):
            raise SystemExit("generation rollback diagnostics mutation classification drift: " + label)
        try:
            validate(mutated, check_blob=label in blob_only)
        except SystemExit:
            continue
        raise SystemExit(f"generation rollback diagnostics accepted forbidden mutation: {label}")
    print(f"PASS: generation rollback diagnostics workflow source admission ({len(cases) - 2} semantic anchor + 2 blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
