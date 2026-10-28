#!/usr/bin/env python3
"""Fail-closed source-admission negatives for admission-chain reconcile CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-admission-chain-reconcile-negative.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "c8d7cf9ed1bd9a41416cb6b43b11379c2dc766d5"

TRIGGER_PATHS = (
    ".github/workflows/backup-restore-admission-chain-reconcile-negative.yml",
    "scripts/reconcile-memory-os-backup-restore-admission-chain.py",
    "scripts/request-memory-os-backup-restore-drill.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/validate-memory-os-backup-restore-generation-independent-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py",
    "scripts/validate-memory-os-backup-restore-review-source-order.py",
    "scripts/validate-memory-os-backup-restore-admission-chain.py",
    "scripts/validate-memory-os-backup-restore-admission-chain-reconcile-negative.py",
    "scripts/validate-memory-os-backup-restore-admission-chain-reconcile-workflow-negative.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/backup-restore-admission-chain-contract.v1.json",
    "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/evidence/backup-restore/**",
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
    ("unreviewed event", '          else\n            echo "Unreviewed admission-chain reconcile-negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-admission-chain-reconcile-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-admission-chain-reconcile-workflow-negative.py\n', 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", '            test "${PR_BASE_REF:-}" = "so"\n', 1),
)



def validate_trigger_reachability(
    source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS
) -> None:
    """Pin every reviewed admission-chain reconcile CI path under PR and push."""
    if len(trigger_paths) != 24 or len(set(trigger_paths)) != 24:
        raise SystemExit("admission-chain reconcile CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("admission-chain reconcile CI trigger marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        expected = tuple(f'      - "{item}"' for item in trigger_paths)
        if actual != expected:
            raise SystemExit("admission-chain reconcile CI " + event + " trigger inventory drift")
        for item in trigger_paths:
            if block.count('      - "' + item + '"' + chr(10)) != 1:
                raise SystemExit("admission-chain reconcile CI " + event + " trigger path drift: " + item)


def prove_trigger_reachability_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for item in TRIGGER_PATHS:
            token = '      - "' + item + '"' + chr(10)
            if source.count(token) != 2:
                raise SystemExit("admission-chain reconcile CI trigger mutation anchor drift: " + item)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("admission-chain reconcile CI accepted missing " + event + " trigger: " + item)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("admission-chain reconcile CI shortened trigger inventory accepted")
    print("PASS: admission-chain reconcile CI event-specific triggers (48 removals; 1 shortened inventory negative)")
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
                raise SystemExit(f"admission-chain reconcile CI addition fixture missing: {event} {label}")
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit(f"admission-chain reconcile CI accepted {event} addition: {label}")
    print("PASS: admission-chain reconcile CI trigger additions (8 event-specific semantic negatives)")





def validate_yaml_authority(source: str) -> None:
    """Pin effective admission-chain reconcile event/root/permission YAML semantics."""
    name = "name: Backup Restore Admission Chain Reconcile Negative"
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    paths = "".join('      - "' + item + '"\n' for item in TRIGGER_PATHS)
    expected_header = (
        name + "\n\non:\n" + pr_marker + paths
        + push_marker + paths + "  workflow_dispatch:\n"
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("admission-chain reconcile CI exact event header drift")
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [name, "on:", "permissions:", "jobs:"]:
        raise SystemExit("admission-chain reconcile CI root YAML key shadow drift")
    leaves = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            leaves.append(line)
    if leaves != ["  contents: read"]:
        raise SystemExit("admission-chain reconcile CI permission leaf shadow drift")
    body = source.split("\njobs:\n", 1)[1]
    job_rows = [
        line for line in body.splitlines()
        if line.startswith("  ") and not line.startswith("   ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_rows != ["  negative:"]:
        raise SystemExit("admission-chain reconcile CI job mapping shadow drift")
    job_keys = [
        line for line in body.splitlines()
        if line.startswith("    ") and not line.startswith("     ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_keys != [
        "    runs-on: ubuntu-latest", "    timeout-minutes: 5", "    steps:",
    ]:
        raise SystemExit("admission-chain reconcile CI job key/permission shadow drift")


def prove_yaml_authority_negatives(source: str) -> None:
    """Require intended diagnostics for 18 digest-independent YAML negatives."""
    validate_yaml_authority(source)
    event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if event == source:
        raise SystemExit("admission-chain reconcile CI YAML event fixture anchor drift")
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
        raise SystemExit("admission-chain reconcile CI YAML permission fixture anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(marker, marker + leaf, 1),
                      "permission leaf shadow drift"))
    for label, suffix in (
        ("duplicate job", "  negative: {}\n"),
        ("spaced job", "  negative : {}\n"),
        ("quoted job", "  'negative': {}\n"),
    ):
        cases.append((label, source.rstrip("\n") + "\n" + suffix,
                      "job mapping shadow drift"))
    runs_on = "    runs-on: ubuntu-latest\n"
    if source.count(runs_on) != 1:
        raise SystemExit("admission-chain reconcile CI job fixture anchor drift")
    for label, leaf in (
        ("job permission", "    permissions:\n      contents: write\n"),
        ("spaced job permission", "    permissions :\n      contents: write\n"),
        ("quoted job permission", "    'permissions':\n      contents: write\n"),
        ("job bypass", "    if: false\n"),
        ("job timeout shadow", "    timeout-minutes : 0\n"),
        ("job continuation shadow", "    continue-on-error: true\n"),
    ):
        cases.append((label, source.replace(runs_on, runs_on + leaf, 1),
                      "job key/permission shadow drift"))
    if len(cases) != 18:
        raise SystemExit("admission-chain reconcile CI YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("admission-chain reconcile CI unchanged YAML fixture: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "admission-chain reconcile CI " + diagnostic
            if str(exc) != expected:
                raise SystemExit("admission-chain reconcile CI wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("admission-chain reconcile CI accepted YAML mutation: " + label)
    print("PASS: admission-chain reconcile CI YAML event/root/permission authority (18 exact-diagnostic negatives)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_yaml_authority(source)
    validate_trigger_reachability(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"reconcile workflow source boundary drift: {label}")
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if check_blob and hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
        raise SystemExit("admission-chain reconcile complete workflow source drift")


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
            raise SystemExit("admission-chain reconcile runtime branch guard drift: " + label)
    print("PASS: admission-chain reconcile PR/push branch guard runtime (6 cases)")


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
        ("injected shell", "          python scripts/validate-memory-os-backup-restore-admission-chain-reconcile-workflow-negative.py\n", "          echo UNREVIEWED\n          python scripts/validate-memory-os-backup-restore-admission-chain-reconcile-workflow-negative.py\n"),
        ("injected action", "      - name: Prove transactional generation recovery reconciliation\n", "      - uses: unreviewed/action@v1\n      - name: Prove transactional generation recovery reconciliation\n"),
        ("removed PR self-trigger", '      - "scripts/validate-memory-os-backup-restore-admission-chain-reconcile-workflow-negative.py"\n', ""),
    )
    if len(cases) != 20:
        raise SystemExit("admission-chain reconcile negative inventory drift")
    semantic_count = 0
    blob_only_count = 0
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"reconcile workflow negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        if mutated == source:
            raise SystemExit(f"reconcile workflow mutation unchanged: {label}")
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in REQUIRED)
        semantic_count += int(semantic)
        blob_only_count += int(not semantic)
        try:
            validate(mutated, check_blob=not semantic)
        except SystemExit:
            continue
        raise SystemExit(f"reconcile workflow accepted forbidden mutation: {label}")
    if (semantic_count, blob_only_count) != (len(cases) - 2, 2):
        raise SystemExit("admission-chain reconcile semantic/blob mutation coverage drift")
    print(f"PASS: admission-chain reconcile workflow source admission ({semantic_count} semantic; {blob_only_count} blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
