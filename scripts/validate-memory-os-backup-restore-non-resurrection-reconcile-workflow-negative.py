#!/usr/bin/env python3
"""Fail-closed source-admission negatives for typed non-resurrection reconcile CI."""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-non-resurrection-reconcile-negative.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "ea00ec141cbde9c2822a51d755142a2665a072c8"
TRIGGER_PATHS = (
    ".github/workflows/backup-restore-non-resurrection-reconcile-negative.yml",
    "scripts/reconcile-memory-os-backup-non-resurrection-authority.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/validate-memory-os-backup-restore-review-source-order.py",
    "scripts/validate-memory-os-backup-restore-generation-independent-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-source-binding-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-load-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-transport-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-registry-aggregate-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-contract-path-negative.py",
    "scripts/validate-memory-os-local-apple-replay-restore.py",
    "scripts/validate-memory-os-local-coherent-recovery-set.py",
    "scripts/validate-memory-os-backup-non-resurrection-reconcile-negative.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-reconcile-workflow-negative.py",
    "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
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
    ("unreviewed event", '          else\n            echo "Unreviewed typed non-resurrection reconcile negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-non-resurrection-reconcile-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-non-resurrection-reconcile-workflow-negative.py\n', 1),
    ("PR base ref", '            test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR target filter", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("material delta review trigger", '      - "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py"\n', 2),
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Require reviewed typed non-resurrection reconcile CI paths in both events."""
    if len(trigger_paths) != 27 or len(set(trigger_paths)) != 27:
        raise SystemExit("typed non-resurrection reconcile CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("typed non-resurrection reconcile CI trigger marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    expected = ['      - "' + item + '"' for item in trigger_paths]
    for event, block in (("pull_request", pr), ("push", push)):
        actual = [line for line in block.splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
        if actual != expected:
            raise SystemExit("typed non-resurrection reconcile CI " + event + " exact trigger inventory drift")


def prove_trigger_reachability_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for item in TRIGGER_PATHS:
            token = '      - "' + item + '"' + chr(10)
            if source.count(token) != 2:
                raise SystemExit("typed non-resurrection reconcile CI trigger mutation anchor drift: " + item)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("typed non-resurrection reconcile CI accepted missing " + event + " trigger: " + item)
    # Unquoted YAML paths must not bypass a quoted-only semantic inventory.
    for event, marker in (
        ("pull_request", "  pull_request:\n    branches:\n      - so\n    paths:\n"),
        ("push", push_marker),
    ):
        for label, injected in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", '      - "' + TRIGGER_PATHS[0] + '"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", "      - " + TRIGGER_PATHS[0] + "\n"),
        ):
            if source.count(marker) != 1:
                raise SystemExit("typed non-resurrection reconcile CI unquoted fixture marker drift")
            mutated = source.replace(marker, marker + injected, 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("typed non-resurrection reconcile CI accepted " + event + " " + label)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("typed non-resurrection reconcile CI shortened trigger inventory accepted")
    print("PASS: typed non-resurrection reconcile CI event-specific trigger reachability (54 removals; 8 additions; 1 shortened inventory negative)")



def validate_yaml_authority(source: str) -> None:
    """Reject unreviewed typed non-resurrection reconcile CI YAML shadows."""
    name = "name: Backup Restore Non-Resurrection Reconcile Negative"
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    paths = "".join('      - "' + item + '"\n' for item in TRIGGER_PATHS)
    header = name + "\n\non:\n" + pr + paths + push + paths + "  workflow_dispatch:\n"
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != header):
        raise SystemExit("typed non-resurrection reconcile CI exact event header drift")
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [name, "on:", "permissions:", "jobs:"]:
        raise SystemExit("typed non-resurrection reconcile CI root YAML key shadow drift")
    leaves = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            leaves.append(line)
    if leaves != ["  contents: read"]:
        raise SystemExit("typed non-resurrection reconcile CI permission leaf shadow drift")
    body = source.split("\njobs:\n", 1)[1]
    job_headers = [
        line for line in body.splitlines()
        if line.startswith("  ") and not line.startswith("   ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_headers != ["  negative:"]:
        raise SystemExit("typed non-resurrection reconcile CI job mapping shadow drift")
    job_keys = [
        line for line in body.splitlines()
        if line.startswith("    ") and not line.startswith("     ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_keys != ["    runs-on: ubuntu-latest", "    timeout-minutes: 5", "    steps:"]:
        raise SystemExit("typed non-resurrection reconcile CI job key/permission shadow drift")


def prove_yaml_authority_negatives(source: str) -> None:
    """Require fifteen exact YAML event/root/job/permission diagnostics without blob fallback."""
    validate_yaml_authority(source)
    event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if event == source:
        raise SystemExit("typed non-resurrection reconcile CI YAML event fixture anchor drift")
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
        raise SystemExit("typed non-resurrection reconcile CI YAML permission fixture anchor drift")
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
    job_marker = "    runs-on: ubuntu-latest\n"
    if source.count(job_marker) != 1:
        raise SystemExit("typed non-resurrection reconcile CI job permission fixture anchor drift")
    for label, leaf in (
        ("job permission", "    permissions:\n      contents: write\n"),
        ("spaced job permission", "    permissions :\n      contents: write\n"),
        ("quoted job permission", "    'permissions':\n      contents: write\n"),
    ):
        cases.append((label, source.replace(job_marker, job_marker + leaf, 1),
                      "job key/permission shadow drift"))
    if len(cases) != 15:
        raise SystemExit("typed non-resurrection reconcile CI YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("typed non-resurrection reconcile CI unchanged YAML fixture: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "typed non-resurrection reconcile CI " + diagnostic
            if str(exc) != expected:
                raise SystemExit("typed non-resurrection reconcile CI wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("typed non-resurrection reconcile CI accepted YAML mutation: " + label)
    print("PASS: typed non-resurrection reconcile CI YAML event/root/job/permission authority (15 exact-diagnostic negatives)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_yaml_authority(source)
    validate_trigger_reachability(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"typed non-resurrection reconcile workflow source boundary drift: {label}")


    if not source.rstrip().endswith('          test -z "$(git status --porcelain)"'):
        raise SystemExit("typed non-resurrection reconcile workflow source boundary drift: final read-only terminator")
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("typed non-resurrection reconcile workflow complete source blob drift")


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
            raise SystemExit("typed non-resurrection reconcile runtime branch guard drift: " + label)
    print("PASS: typed non-resurrection reconcile PR/push branch guard runtime (6 cases)")


RECONCILE_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-non-resurrection-reconcile-negative.py"
PRIVATE_ROLLBACK_NEGATIVES = (
    ("prove_rollback_attempts_all_restores", "typed non-resurrection rollback incomplete"),
    ("prove_primary_and_rollback_failures_are_preserved",
     "typed non-resurrection reconcile failed; rollback incomplete"),
    ("prove_second_replace_rollback",
     "typed non-resurrection reconcile failed; rollback completed"),
    ("prove_post_write_aggregate_rollback",
     "typed non-resurrection reconcile failed; rollback completed"),
)


def require_private_rollback_negative_reachable(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise SystemExit("typed rollback negative syntax invalid") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    main = functions.get("main")
    if main is None:
        raise SystemExit("typed rollback negative main missing")
    for function_name, expected in PRIVATE_ROLLBACK_NEGATIVES:
        target = functions.get(function_name)
        if target is None:
            raise SystemExit("typed private rollback negative missing: " + function_name)
        calls = [node for node in ast.walk(main) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == function_name]
        if len(calls) != 1:
            raise SystemExit("typed private rollback negative invocation drift: " + function_name)
        strings = {node.value for node in ast.walk(target)
                   if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        if expected not in strings:
            raise SystemExit("typed private rollback failure class missing: " + function_name)


def prove_private_rollback_negative_deletion_rejected() -> None:
    source = RECONCILE_NEGATIVE.read_text(encoding="utf-8")
    require_private_rollback_negative_reachable(source)
    for function_name, _expected in PRIVATE_ROLLBACK_NEGATIVES:
        anchor = f"    {function_name}()\n"
        if source.count(anchor) != 1:
            raise SystemExit("typed private rollback negative deletion anchor drift")
        mutated = source.replace(anchor, "    pass\n", 1)
        try:
            require_private_rollback_negative_reachable(mutated)
        except SystemExit:
            pass
        else:
            raise SystemExit("typed private rollback negative deletion accepted: " + function_name)
    print("PASS: typed private rollback class negatives and invocation deletion rejected")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_yaml_authority_negatives(source)
    prove_branch_guards_runtime()
    prove_private_rollback_negative_deletion_rejected()
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
        ("material delta review trigger", REQUIRED[16][1], ""),
    )
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit(f"typed non-resurrection reconcile negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated, check_blob=False)
        except SystemExit:
            continue
        raise SystemExit(f"typed non-resurrection reconcile accepted forbidden mutation: {label}")
    # The canonical workflow may or may not end in a newline; both are valid.
    validate(source.rstrip("\n") + "\n", check_blob=False)
    try:
        validate(source + '\n          echo "unreviewed final command"\n')
    except SystemExit:
        pass
    else:
        raise SystemExit("typed non-resurrection reconcile accepted appended final command")
    for label, old, replacement in (
        ("PR base ref", REQUIRED[14][1], ""),
        ("PR target filter", REQUIRED[15][1], "  pull_request:\n    paths:\n"),
    ):
        if old not in source:
            raise SystemExit("typed non-resurrection reconcile PR branch negative anchor missing: " + label)
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated, check_blob=False)
        except SystemExit:
            continue
        raise SystemExit("typed non-resurrection reconcile accepted forbidden PR branch mutation: " + label)
    # Whole-source binding rejects otherwise anchor-preserving workflow changes.
    for label, mutated in (
        ("extra executable step", source.replace(
            "      - name: Prove transactional typed non-resurrection reconciliation\n",
            "      - run: echo unreviewed\n      - name: Prove transactional typed non-resurrection reconciliation\n", 1)),
    ):
        if mutated == source:
            raise SystemExit("typed non-resurrection reconcile source digest negative anchor missing: " + label)
        try:
            validate(mutated)
        except SystemExit:
            continue
        raise SystemExit("typed non-resurrection reconcile accepted whole-source mutation: " + label)
    print(f"PASS: typed non-resurrection reconcile workflow source admission ({len(cases) + 2} semantic anchor negatives; 2 complete-source/terminator negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
