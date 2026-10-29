#!/usr/bin/env python3
"""Fail-closed source-admission negatives for generation evidence reconcile CI."""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-evidence-reconcile-negative.yml"
TRANSPORT_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence-transport-negative.py"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "563c543233e125f37b1661f865ae275ccab7de90"
TRIGGER_PATHS = (
    ".github/workflows/backup-restore-generation-evidence-reconcile-negative.yml",
    "scripts/reconcile-memory-os-backup-restore-generation-evidence.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-review-source-order.py",
    "scripts/validate-memory-os-backup-restore-generation-independent-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-transport-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-registry-transaction-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-negative.py",
    "scripts/validate-memory-os-backup-restore-semantic-generation-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-binding.py",
    "scripts/validate-memory-os-backup-restore-generation-binding-transport-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-workflow-negative.py",
    "scripts/validate-memory-os-operability.py",
    "contracts/operations/backup-restore-generation-evidence-contract.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
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
    ("unreviewed event", '          else\n            echo "Unreviewed generation evidence reconcile negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-generation-evidence-reconcile-workflow-negative.py\n', 1),
    ("PR base ref", '            test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR target filter", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("material delta review trigger", '      - "scripts/validate-memory-os-backup-restore-generation-material-delta-review-execution-negative.py"\n', 2),
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Require the reviewed generation evidence reconcile paths in each CI event."""
    if len(trigger_paths) != 27 or len(set(trigger_paths)) != 27:
        raise SystemExit("generation evidence reconcile CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("generation evidence reconcile CI trigger marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    expected = ['      - "' + item + '"' for item in trigger_paths]
    for event, block in (("pull_request", pr), ("push", push)):
        actual = [line for line in block.splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
        if actual != expected:
            raise SystemExit("generation evidence reconcile CI " + event + " exact trigger inventory drift")


def validate_yaml_authority(source: str) -> None:
    """Reject effective event/root/permission shadows without a whole-blob shortcut."""
    paths = "".join('      - "' + path + '"\n' for path in TRIGGER_PATHS)
    expected_header = (
        "name: Backup Restore Generation Evidence Reconcile Negative\n\non:\n"
        + "  pull_request:\n    branches:\n      - so\n    paths:\n" + paths
        + "  push:\n    branches:\n      - so\n    paths:\n" + paths
        + "  workflow_dispatch:\n"
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("generation evidence reconcile CI exact event header drift")
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [
        "name: Backup Restore Generation Evidence Reconcile Negative",
        "on:", "permissions:", "jobs:",
    ]:
        raise SystemExit("generation evidence reconcile CI root YAML key shadow drift")
    permission_rows = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            permission_rows.append(line)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("generation evidence reconcile CI permission leaf shadow drift")
    body = source.split("\njobs:\n", 1)[1]
    headers = [
        line for line in body.splitlines()
        if line.startswith("  ") and not line.startswith("   ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if headers != ["  negative:"]:
        raise SystemExit("generation evidence reconcile CI job mapping shadow drift")
    job_keys = [
        line for line in body.splitlines()
        if line.startswith("    ") and not line.startswith("     ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_keys != ["    runs-on: ubuntu-latest", "    timeout-minutes: 5", "    steps:"]:
        raise SystemExit("generation evidence reconcile CI job key/permission shadow drift")


def prove_yaml_authority_negatives(source: str) -> None:
    validate_yaml_authority(source)
    extra_event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if extra_event == source:
        raise SystemExit("generation evidence reconcile CI event mutation anchor drift")
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
        raise SystemExit("generation evidence reconcile CI permission mutation anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(anchor, anchor + leaf, 1),
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
        raise SystemExit("generation evidence reconcile CI job permission fixture anchor drift")
    for label, leaf in (
        ("job permission", "    permissions:\n      contents: write\n"),
        ("spaced job permission", "    permissions :\n      contents: write\n"),
        ("quoted job permission", "    'permissions':\n      contents: write\n"),
    ):
        cases.append((label, source.replace(runs_on, runs_on + leaf, 1),
                      "job key/permission shadow drift"))
    if len(cases) != 15:
        raise SystemExit("generation evidence reconcile CI YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("generation evidence reconcile CI unchanged YAML negative: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "generation evidence reconcile CI " + diagnostic
            if str(exc) != expected:
                raise SystemExit("generation evidence reconcile CI wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("generation evidence reconcile CI accepted YAML mutation: " + label)
    print("PASS: generation evidence reconcile CI YAML event/root/job/permission authority (15 exact-diagnostic negatives)")



def prove_trigger_reachability_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for item in TRIGGER_PATHS:
            token = '      - "' + item + '"' + chr(10)
            if source.count(token) != 2:
                raise SystemExit("generation evidence reconcile CI trigger mutation anchor drift: " + item)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("generation evidence reconcile CI accepted missing " + event + " trigger: " + item)
    # YAML also accepts unquoted paths; do not ignore them in semantic admission.
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
                raise SystemExit("generation evidence reconcile CI unquoted fixture marker drift")
            mutated = source.replace(marker, marker + injected, 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("generation evidence reconcile CI accepted " + event + " " + label)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("generation evidence reconcile CI shortened trigger inventory accepted")
    print("PASS: generation evidence reconcile CI event-specific trigger reachability (54 removals; 8 additions; 1 shortened inventory negative)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    validate_yaml_authority(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"generation evidence reconcile workflow source boundary drift: {label}")


    if not source.rstrip().endswith('          test -z "$(git status --porcelain)"'):
        raise SystemExit("generation evidence reconcile workflow source boundary drift: final read-only terminator")
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("generation evidence reconcile workflow complete source blob drift")



def require_private_child_negative_reachable(source: str) -> None:
    """Require the real transport negative's private child check to execute in main."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        raise SystemExit("generation evidence transport negative invalid syntax") from None
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if "prove_private_bounded_child_execution" not in functions or "main" not in functions:
        raise SystemExit("generation evidence private child negative missing")
    calls = [
        node for node in ast.walk(functions["main"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "prove_private_bounded_child_execution"
    ]
    if len(calls) != 1:
        raise SystemExit("generation evidence private child negative execution drift")
    if "prove_private_writer_import_failures" not in functions:
        raise SystemExit("generation evidence private writer import negative missing")
    writer_calls = [
        node for node in ast.walk(functions["main"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "prove_private_writer_import_failures"
    ]
    if len(writer_calls) != 1:
        raise SystemExit("generation evidence private writer import negative execution drift")
    if "prove_private_escaped_path_diagnostic" not in functions:
        raise SystemExit("generation evidence private escaped-path negative missing")
    path_calls = [
        node for node in ast.walk(functions["main"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "prove_private_escaped_path_diagnostic"
    ]
    if len(path_calls) != 1:
        raise SystemExit("generation evidence private escaped-path negative execution drift")


def prove_private_child_negative_removal_rejected() -> None:
    source = TRANSPORT_NEGATIVE.read_text(encoding="utf-8")
    require_private_child_negative_reachable(source)
    anchor = "    prove_private_bounded_child_execution(module)\n"
    if source.count(anchor) != 1:
        raise SystemExit("generation evidence private child negative removal anchor drift")
    mutated = source.replace(anchor, "    pass\n", 1)
    try:
        require_private_child_negative_reachable(mutated)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation evidence private child negative deletion accepted")
    print("PASS: generation evidence private child negative execution deletion rejected")
    writer_anchor = "    prove_private_writer_import_failures(module)\n"
    if source.count(writer_anchor) != 1:
        raise SystemExit("generation evidence private writer import negative removal anchor drift")
    mutated_writer = source.replace(writer_anchor, "    pass\n", 1)
    try:
        require_private_child_negative_reachable(mutated_writer)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation evidence private writer import negative deletion accepted")
    print("PASS: generation evidence private writer import negative execution deletion rejected")
    path_anchor = "    prove_private_escaped_path_diagnostic(module)\n"
    if source.count(path_anchor) != 1:
        raise SystemExit("generation evidence private escaped-path negative removal anchor drift")
    mutated_path = source.replace(path_anchor, "    pass\n", 1)
    try:
        require_private_child_negative_reachable(mutated_path)
    except SystemExit:
        pass
    else:
        raise SystemExit("generation evidence private escaped-path negative deletion accepted")
    print("PASS: generation evidence private escaped-path negative execution deletion rejected")



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
            raise SystemExit("generation evidence reconcile runtime branch guard drift: " + label)
    print("PASS: generation evidence reconcile PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_yaml_authority_negatives(source)
    prove_branch_guards_runtime()
    prove_private_child_negative_removal_rejected()
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
            raise SystemExit(f"generation evidence reconcile negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        expected = (
            "generation evidence reconcile CI pull_request exact trigger inventory drift"
            if label in {"self-trigger", "material delta review trigger"}
            else "generation evidence reconcile workflow source boundary drift: " + label
        )
        try:
            validate(mutated, check_blob=False)
        except SystemExit as exc:
            if str(exc) != expected:
                raise SystemExit("generation evidence reconcile wrong source negative diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit(f"generation evidence reconcile accepted forbidden mutation: {label}")
    # A path occurring in both events must be removed from push independently;
    # replacing the first occurrence alone exercises PR twice.
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    if source.count(push_marker) != 1:
        raise SystemExit("generation evidence reconcile push negative marker drift")
    for label, token in (
        ("push self-trigger", REQUIRED[12][1]),
        ("push material delta review trigger", REQUIRED[16][1]),
    ):
        prefix, push_block = source.split(push_marker, 1)
        if push_block.count(token) != 1:
            raise SystemExit("generation evidence reconcile push negative anchor drift: " + label)
        mutated = prefix + push_marker + push_block.replace(token, "", 1)
        try:
            validate(mutated, check_blob=False)
        except SystemExit as exc:
            expected = "generation evidence reconcile CI push exact trigger inventory drift"
            if str(exc) != expected:
                raise SystemExit("generation evidence reconcile wrong push negative diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("generation evidence reconcile accepted missing " + label)
    # The canonical workflow may or may not end in a newline; both are valid.
    validate(source.rstrip("\n") + "\n", check_blob=False)
    try:
        validate(source + '\n          echo "unreviewed final command"\n')
    except SystemExit as exc:
        if str(exc) != "generation evidence reconcile workflow source boundary drift: final read-only terminator":
            raise SystemExit("generation evidence reconcile wrong appended command diagnostic: " + str(exc)) from exc
    else:
        raise SystemExit("generation evidence reconcile accepted appended final command")
    for label, old, replacement in (
        ("PR base ref", REQUIRED[14][1], ""),
        ("PR target filter", REQUIRED[15][1], "  pull_request:\n    paths:\n"),
    ):
        if old not in source:
            raise SystemExit("generation evidence reconcile PR branch negative anchor missing: " + label)
        mutated = source.replace(old, replacement, 1)
        expected = ("generation evidence reconcile CI trigger marker drift"
                    if label == "PR target filter"
                    else "generation evidence reconcile workflow source boundary drift: " + label)
        try:
            validate(mutated, check_blob=False)
        except SystemExit as exc:
            if str(exc) != expected:
                raise SystemExit("generation evidence reconcile wrong PR negative diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("generation evidence reconcile accepted forbidden PR branch mutation: " + label)
    # Whole-source binding rejects otherwise anchor-preserving workflow changes.
    for label, mutated in (
        ("extra executable step", source.replace(
            "      - name: Prove transactional generation recovery reconciliation\n",
            "      - run: echo unreviewed\n      - name: Prove transactional generation recovery reconciliation\n", 1)),
    ):
        if mutated == source:
            raise SystemExit("generation evidence reconcile source digest negative anchor missing: " + label)
        try:
            validate(mutated)
        except SystemExit as exc:
            if str(exc) != "generation evidence reconcile workflow complete source blob drift":
                raise SystemExit("generation evidence reconcile wrong whole-source diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("generation evidence reconcile accepted whole-source mutation: " + label)
    print(f"PASS: generation evidence reconcile workflow source admission ({len(cases) + 4} semantic anchor negatives including 2 push-only removals; 2 complete-source/terminator negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
