#!/usr/bin/env python3
"""Fail-closed source-admission negatives for human promotion-review readonly CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-promotion-review-readonly.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "3f87571068b519994fe67ef2a816fd71caefafed"

TRIGGER_PATHS = (
    ".github/workflows/backup-restore-promotion-review-readonly.yml",
    ".github/workflows/backup-restore-promotion-review.yml",
    ".github/workflows/backup-restore-promotion-review-source-order.yml",
    "scripts/validate-memory-os-backup-restore-promotion-review-source-order.py",
    "scripts/validate-memory-os-backup-restore-promotion-review.py",
    "scripts/validate-memory-os-backup-restore-promotion-review-negative.py",
    "scripts/register-memory-os-backup-restore-promotion-review.py",
    "scripts/validate-memory-os-backup-restore-promotion-review-reconcile-negative.py",
    "scripts/reconcile-memory-os-backup-restore-promotion-review.py",
    "scripts/validate-memory-os-backup-restore-promotion-review-readonly-workflow-negative.py",
    "contracts/operations/backup-restore-promotion-review-contract.v1.json",
    "contracts/operations/backup-restore-promotion-review-registry.v1.json",
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-drill-request-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/operability-admission-inventory.v1.json",
    "contracts/operations/production-operability-status.json",
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
    ("unreviewed event", '          else\n            echo "Unreviewed promotion-review readonly event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("self-trigger", "      - 'scripts/validate-memory-os-backup-restore-promotion-review-readonly-workflow-negative.py'\n", 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-promotion-review-readonly-workflow-negative.py\n', 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", '            test "${PR_BASE_REF:-}" = "so"\n', 1),
    ("writer self-trigger", "      - 'scripts/register-memory-os-backup-restore-promotion-review.py'\n", 2),
    ("root read-only permission", "permissions:\n  contents: read\n", 1),
    ("no contents write permission", "contents: write", 0),
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Pin promotion-review source triggers in both CI events independently."""
    if len(trigger_paths) != 22 or len(set(trigger_paths)) != 22:
        raise SystemExit("promotion-review readonly trigger inventory drift")
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (push_marker, pr_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("promotion-review readonly trigger marker drift")
    push_block = source.split(push_marker, 1)[1].split(pr_marker, 1)[0]
    pr_block = source.split(pr_marker, 1)[1].split(dispatch_marker, 1)[0]
    expected = ["      - '" + path + "'" for path in trigger_paths]
    for event, block in (("push", push_block), ("pull_request", pr_block)):
        actual = [line for line in block.splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
        if actual != expected:
            raise SystemExit("promotion-review readonly " + event + " exact trigger inventory drift")


def prove_trigger_reachability_negatives(source: str) -> None:
    """Reject one-event-only path removals and a shortened validator inventory."""
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    for event in ("push", "pull_request"):
        for path in TRIGGER_PATHS:
            token = "      - '" + path + "'\n"
            if source.count(token) != 2:
                raise SystemExit("promotion-review readonly trigger negative anchor drift: " + path)
            if event == "push":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(pr_marker, 1)
                mutated = prefix + pr_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("promotion-review readonly trigger negative accepted: " + event + " " + path)
    # Event-specific additions and duplicates must fail without digest admission.
    for event, marker in (
        ("push", "  push:\n    branches: [so]\n    paths:\n"),
        ("pull_request", pr_marker),
    ):
        for label, injected in (
            ("quoted unreviewed path", "      - 'unreviewed/**'\n"),
            ("quoted duplicate path", "      - '" + TRIGGER_PATHS[0] + "'\n"),
            ("unquoted unreviewed path", "      - unreviewed/**\n"),
            ("unquoted duplicate path", "      - " + TRIGGER_PATHS[0] + "\n"),
        ):
            if source.count(marker) != 1:
                raise SystemExit("promotion-review readonly addition fixture marker drift")
            mutated = source.replace(marker, marker + injected, 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("promotion-review readonly extra trigger accepted: " + event + " " + label)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("promotion-review readonly shortened trigger inventory accepted")
    print(f"PASS: promotion-review readonly PR/push trigger reachability ({len(TRIGGER_PATHS) * 2} semantic removal negatives; 8 event-specific addition negatives; 1 shortened inventory negative)")



def validate_yaml_authority(source: str) -> None:
    """Pin human promotion-review readonly CI event/root/permission YAML authority."""
    name = "name: Backup Restore Promotion Review Readonly"
    push = "  push:\n    branches: [so]\n    paths:\n"
    pr = "  pull_request:\n    branches: [so]\n    paths:\n"
    paths = "".join("      - '" + item + "'\n" for item in TRIGGER_PATHS)
    header = name + "\n\non:\n" + push + paths + pr + paths + "  workflow_dispatch:\n"
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != header):
        raise SystemExit("promotion-review readonly exact event header drift")
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [name, "on:", "permissions:", "jobs:"]:
        raise SystemExit("promotion-review readonly root YAML key shadow drift")
    leaves = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            leaves.append(line)
    if leaves != ["  contents: read"]:
        raise SystemExit("promotion-review readonly permission leaf shadow drift")
    # No job-scoped permission escalation is approved: this job inherits root read.
    if source.count("\njobs:\n") != 1:
        raise SystemExit("promotion-review readonly job mapping shadow drift")
    job_body = source.split("\njobs:\n", 1)[1]
    job_headers = [line for line in job_body.splitlines()
                   if line.startswith("  ") and not line.startswith("   ")
                   and line.strip() and not line.lstrip().startswith("#")]
    if job_headers != ["  validate:"]:
        raise SystemExit("promotion-review readonly job mapping shadow drift")
    job_keys = [line for line in job_body.splitlines()
                if line.startswith("    ") and not line.startswith("     ")
                and line.strip() and not line.lstrip().startswith("#")]
    if job_keys != ["    runs-on: ubuntu-latest", "    timeout-minutes: 10", "    steps:"]:
        raise SystemExit("promotion-review readonly job authority shadow drift")


def prove_yaml_authority_negatives(source: str) -> None:
    """Require fourteen exact-diagnostic YAML shadow rejections without blob fallback."""
    validate_yaml_authority(source)
    event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if event == source:
        raise SystemExit("promotion-review readonly YAML event fixture anchor drift")
    cases = [("extra event", event, "exact event header drift")]
    for label, suffix in (
        ("spaced on", "on :\n  issues:\n"),
        ("quoted on", "'on':\n  issues:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("quoted permissions", "'permissions':\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
        ("quoted jobs", "'jobs': {}\n"),
    ):
        cases.append((label, source + "\n" + suffix, "root YAML key shadow drift"))
    marker = "\npermissions:\n  contents: read\n"
    if source.count(marker) != 1:
        raise SystemExit("promotion-review readonly YAML permission fixture anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(marker, marker + leaf, 1),
                      "permission leaf shadow drift"))
    for label, suffix in (
        ("spaced validate job", "  validate : {}\n"),
        ("quoted validate job", "  'validate': {}\n"),
    ):
        cases.append((label, source.rstrip("\n") + "\n" + suffix,
                      "job mapping shadow drift"))
    for label, injected in (
        ("plain job write permission", "    permissions:\n      contents: write\n"),
        ("spaced job write permission", "    permissions :\n      contents: write\n"),
        ("quoted job write permission", "    'permissions':\n      contents: write\n"),
    ):
        marker = "  validate:\n"
        if source.count(marker) != 1:
            raise SystemExit("promotion-review readonly job permission fixture anchor drift")
        cases.append((label, source.replace(marker, marker + injected, 1),
                      "job authority shadow drift"))
    if len(cases) != 14:
        raise SystemExit("promotion-review readonly YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("promotion-review readonly unchanged YAML fixture: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "promotion-review readonly " + diagnostic
            if str(exc) != expected:
                raise SystemExit("promotion-review readonly wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("promotion-review readonly accepted YAML mutation: " + label)
    print("PASS: promotion-review readonly YAML event/root/permission authority (14 exact-diagnostic negatives)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_yaml_authority(source)
    validate_trigger_reachability(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"promotion-review readonly workflow source boundary drift: {label}")
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if check_blob and hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
        raise SystemExit("readonly workflow complete Git source drift")


def prove_branch_guards_runtime() -> None:
    """Run the exact reviewed branch predicates with disposable synthetic refs."""
    cases = (
        ("PR so", REQUIRED[16][1].strip(), "PR_BASE_REF", "so", True),
        ("PR main", REQUIRED[16][1].strip(), "PR_BASE_REF", "main", False),
        ("PR missing", REQUIRED[16][1].strip(), "PR_BASE_REF", "", False),
        ("push so", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", REQUIRED[8][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for name, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(
            ["bash", "-e", "-c", command], env=env, capture_output=True, check=False
        )
        if (result.returncode == 0) != expected:
            raise SystemExit("promotion-review readonly branch runtime guard drift: " + name)
    print("PASS: promotion-review readonly PR/push branch guard runtime (6 cases)")


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
        ("PR target branch", REQUIRED[14][1], "  pull_request:\n    branches: [main]\n    paths:\n"),
        ("PR base environment", REQUIRED[15][1], ""),
        ("PR base assertion", REQUIRED[16][1], '            test -n "${PR_BASE_REF:-}"\n'),
        ("injected shell command", "          set -euo pipefail\n", "          set -euo pipefail\n          echo UNREVIEWED\n"),
        ("injected action", "      - name: Assert exact clean promotion-review source\n", "      - uses: unreviewed/action@v1\n      - name: Assert exact clean promotion-review source\n"),
        ("removed PR self-trigger", "      - \x27scripts/validate-memory-os-backup-restore-promotion-review-readonly-workflow-negative.py\x27\n", ""),
        ("removed writer trigger", REQUIRED[17][1], ""),
        ("root permission escalation", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("job permission escalation", "jobs:\n  validate:\n", "jobs:\n  validate:\n    permissions:\n      contents: write\n"),
    )
    # Only the two anchor-preserving executable injections may rely on the full Git blob.
    digest_only = frozenset({"injected shell command", "injected action"})
    if len(cases) != 23:
        raise SystemExit("promotion-review readonly mutation inventory drift")
    semantic_count = 0
    blob_only_count = 0
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"promotion-review readonly negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        if mutated == source:
            raise SystemExit(f"promotion-review readonly mutation unchanged: {label}")
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in REQUIRED)
        if semantic == (label in digest_only):
            raise SystemExit("promotion-review readonly mutation classification drift: " + label)
        semantic_count += int(semantic)
        blob_only_count += int(not semantic)
        try:
            validate(mutated, check_blob=not semantic)
        except SystemExit:
            continue
        raise SystemExit(f"promotion-review readonly accepted forbidden mutation: {label}")
    if (semantic_count, blob_only_count) != (21, 2):
        raise SystemExit("promotion-review readonly semantic/blob mutation coverage drift")
    print(f"PASS: promotion-review readonly workflow source admission ({semantic_count} semantic; {blob_only_count} blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
