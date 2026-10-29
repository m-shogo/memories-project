#!/usr/bin/env python3
"""Fail-closed source-admission negatives for semantic preflight reconcile CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-drill-preflight-reconcile-negative.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "2ee5dd443a19a4a8f01113bdbc5ced4fbd4bdc60"
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
    ("unreviewed event", '          else\n            echo "Unreviewed semantic preflight reconcile negative event" >&2\n            exit 1\n          fi\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$expected"\n', 1),
    ("clean source", '          test -z "$(git status --porcelain)"', 2),
    ("self-trigger", '      - "scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py"\n', 2),
    ("self-execution", '          python scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py\n', 1),
    ("PR base ref", '            test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("PR target filter", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
)


INDEPENDENT_PATH = ROOT / ".github/workflows/backup-restore-drill-preflight-reconcile-source-negative.yml"
INDEPENDENT_BLOB = "31f8be5c3cb73e82d925684cc6bba47d03e37607"
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/backup-restore-drill-preflight-reconcile-negative.yml",
    ".github/workflows/backup-restore-drill-preflight-reconcile-source-negative.yml",
    "scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py",
)
INDEPENDENT_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("push target", "  push:\n    branches:\n      - so\n    paths:\n", 1),
    ("reviewed workflow trigger", "      - \".github/workflows/backup-restore-drill-preflight-reconcile-negative.yml\"\n", 2),
    ("guard self trigger", "      - \".github/workflows/backup-restore-drill-preflight-reconcile-source-negative.yml\"\n", 2),
    ("validator trigger", "      - \"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py\"\n", 2),
    ("checkout pin", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup pin", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR head binding", "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n", 1),
    ("PR base", "            test \"${GITHUB_BASE_REF:-}\" = \"so\"\n", 1),
    ("push ref", "            test \"${GITHUB_REF:-}\" = \"refs/heads/so\"\n", 1),
    ("SHA format", "          [[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]\n", 1),
    ("exact HEAD", "          test \"$(git rev-parse HEAD)\" = \"$expected\"\n", 1),
    ("clean checkout", "          test -z \"$(git status --porcelain)\"\n", 2),
    ("read token", "  contents: read\n", 2),
    ("exact job scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    ("self execution", "          python scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py\n", 1),
)


PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/backup-restore-drill-preflight-reconcile-negative.yml",
    "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "contracts/operations/production-operability-status.json",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/memory_os_environment_generation_eligibility.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/validate-memory-os-backup-restore-drill-preflight.py",
    "scripts/reconcile-memory-os-backup-restore-drill-preflight.py",
    "scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-negative.py",
    "scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py",
    "scripts/validate-memory-os-operability.py",
)


def validate_publisher_yaml_authority(
    source: str, *, trigger_paths: tuple[str, ...] = PUBLISHER_TRIGGER_PATHS
) -> None:
    """Pin semantic preflight reconcile CI event, path, root and job authority."""
    if len(trigger_paths) != 16 or len(set(trigger_paths)) != 16:
        raise SystemExit("semantic preflight reconcile publisher trigger inventory drift")
    paths = "".join('      - "' + item + '"\n' for item in trigger_paths)
    header = (
        "name: Backup Restore Drill Preflight Reconcile Negative\n\non:\n"
        + "  pull_request:\n    branches:\n      - so\n    paths:\n" + paths
        + "  push:\n    branches:\n      - so\n    paths:\n" + paths
        + "  workflow_dispatch:\n"
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != header):
        raise SystemExit("semantic preflight reconcile publisher exact event header drift")
    roots = [
        row for row in source.splitlines()
        if row.strip() and not row[0].isspace()
        and not row.lstrip().startswith("#")
    ]
    if roots != [
        "name: Backup Restore Drill Preflight Reconcile Negative",
        "on:", "permissions:", "concurrency:", "jobs:",
    ]:
        raise SystemExit("semantic preflight reconcile publisher root YAML key shadow drift")
    leaves = []
    for row in source.split("\npermissions:\n", 1)[1].splitlines():
        if row.strip() and not row[0].isspace():
            break
        if row.strip() and not row.lstrip().startswith("#"):
            leaves.append(row)
    if leaves != ["  contents: read"]:
        raise SystemExit("semantic preflight reconcile publisher permission leaf shadow drift")
    body = source.split("\n" + "jobs:\n", 1)[1]
    job_rows = [
        row for row in body.splitlines()
        if row.startswith("  ") and not row.startswith("   ")
        and row.strip() and not row.lstrip().startswith("#")
    ]
    if job_rows != ["  validate:"]:
        raise SystemExit("semantic preflight reconcile publisher job mapping shadow drift")
    job_keys = [
        row for row in body.splitlines()
        if row.startswith("    ") and not row.startswith("     ")
        and row.strip() and not row.lstrip().startswith("#")
    ]
    if job_keys != ["    runs-on: ubuntu-latest", "    timeout-minutes: 10", "    steps:"]:
        raise SystemExit("semantic preflight reconcile publisher job key/permission shadow drift")


def prove_publisher_yaml_authority_negatives(source: str) -> None:
    """Reject reviewed preflight reconcile CI path and YAML mutations by exact diagnostic."""
    validate_publisher_yaml_authority(source)
    extra = source.replace("on:\n", "on:\n  issues:\n", 1)
    if extra == source:
        raise SystemExit("semantic preflight reconcile publisher extra-event fixture drift")
    cases = [("extra event", extra, "exact event header drift")]
    for label, suffix in (
        ("spaced on", "on :\n  issues:\n"),
        ("quoted on", "'on':\n  issues:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("quoted permissions", "'permissions':\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
        ("quoted jobs", "'jobs': {}\n"),
    ):
        cases.append((label, source.rstrip("\n") + "\n" + suffix,
                      "root YAML key shadow drift"))
    marker = "\npermissions:\n  contents: read\n"
    if source.count(marker) != 1:
        raise SystemExit("semantic preflight reconcile publisher root permission fixture drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(marker, marker + leaf, 1),
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
        raise SystemExit("semantic preflight reconcile publisher job fixture anchor drift")
    for label, leaf in (
        ("job permission", "    permissions:\n      contents: write\n"),
        ("spaced job permission", "    permissions :\n      contents: write\n"),
        ("quoted job permission", "    'permissions':\n      contents: write\n"),
    ):
        cases.append((label, source.replace(runs_on, runs_on + leaf, 1),
                      "job key/permission shadow drift"))
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for path in PUBLISHER_TRIGGER_PATHS:
            token = '      - "' + path + '"\n'
            if source.count(token) != 2:
                raise SystemExit("semantic preflight reconcile publisher trigger fixture drift: " + path)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            cases.append((event + " removed " + path, mutated, "exact event header drift"))
    for event, marker in (("pull_request", pr_marker), ("push", push_marker)):
        for label, extra_path in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", '      - "' + PUBLISHER_TRIGGER_PATHS[0] + '"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", "      - " + PUBLISHER_TRIGGER_PATHS[0] + "\n"),
        ):
            if source.count(marker) != 1:
                raise SystemExit("semantic preflight reconcile publisher addition fixture anchor drift")
            cases.append((event + " " + label, source.replace(marker, marker + extra_path, 1),
                          "exact event header drift"))
    if len(cases) != 55:
        raise SystemExit("semantic preflight reconcile publisher YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("semantic preflight reconcile publisher unchanged negative: " + label)
        try:
            validate_publisher_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "semantic preflight reconcile publisher " + diagnostic
            if str(exc) != expected:
                raise SystemExit("semantic preflight reconcile publisher wrong diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("semantic preflight reconcile publisher accepted mutation: " + label)
    try:
        validate_publisher_yaml_authority(source, trigger_paths=PUBLISHER_TRIGGER_PATHS[:-1])
    except SystemExit as exc:
        if str(exc) != "semantic preflight reconcile publisher trigger inventory drift":
            raise SystemExit("semantic preflight reconcile publisher shortened inventory wrong diagnostic") from exc
    else:
        raise SystemExit("semantic preflight reconcile publisher shortened inventory accepted")
    print("PASS: semantic preflight reconcile publisher event/root/job/permission authority (55 exact-diagnostic negatives; 1 shortened inventory)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_publisher_yaml_authority(source)
    validate_publisher_concurrency_authority(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit(f"semantic preflight reconcile workflow source boundary drift: {label}")


    if not source.rstrip().endswith('          test -z "$(git status --porcelain)"'):
        raise SystemExit("semantic preflight reconcile workflow source boundary drift: final read-only terminator")
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("semantic preflight reconcile complete workflow source drift")



def validate_independent_trigger_reachability(
    source: str, *, trigger_paths: tuple[str, ...] = INDEPENDENT_TRIGGER_PATHS
) -> None:
    """Pin each reviewed preflight reconcile source CI path under PR and push."""
    if len(trigger_paths) != 3 or len(set(trigger_paths)) != 3:
        raise SystemExit("semantic preflight reconcile independent trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    end_marker = "\npermissions:\n"
    for marker in (pr_marker, push_marker, end_marker):
        if source.count(marker) != 1:
            raise SystemExit("semantic preflight reconcile independent trigger marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(end_marker, 1)[0]
    expected = ['      - "' + item + '"' for item in trigger_paths]
    for event, block in (("pull_request", pr), ("push", push)):
        actual = [line for line in block.splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
        if actual != expected:
            raise SystemExit("semantic preflight reconcile independent " + event + " exact trigger inventory drift")


def prove_independent_trigger_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for item in INDEPENDENT_TRIGGER_PATHS:
            token = '      - "' + item + '"' + chr(10)
            if source.count(token) != 2:
                raise SystemExit("semantic preflight reconcile independent trigger fixture drift: " + item)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_independent_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("semantic preflight reconcile independent accepted missing " + event + " trigger: " + item)
    # Unquoted YAML paths must be covered by digest-independent trigger admission.
    for event, marker in (
        ("pull_request", "  pull_request:\n    branches:\n      - so\n    paths:\n"),
        ("push", push_marker),
    ):
        for label, injected in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", '      - "' + INDEPENDENT_TRIGGER_PATHS[0] + '"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", "      - " + INDEPENDENT_TRIGGER_PATHS[0] + "\n"),
        ):
            if source.count(marker) != 1:
                raise SystemExit("semantic preflight reconcile unquoted fixture marker drift")
            mutated = source.replace(marker, marker + injected, 1)
            try:
                validate_independent_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("semantic preflight reconcile accepted " + event + " " + label)
    try:
        validate_independent_trigger_reachability(source, trigger_paths=INDEPENDENT_TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("semantic preflight reconcile independent shortened trigger inventory accepted")
    print("PASS: semantic preflight reconcile independent event-specific triggers (6 removals; 8 additions; 1 shortened inventory negative)")



def validate_independent_yaml_authority(source: str) -> None:
    """Reject event/root/permission YAML shadows independently of the reviewed blob."""
    name = "name: Backup Restore Drill Preflight Reconcile Source Negative"
    paths = "".join('      - "' + item + '"\n' for item in INDEPENDENT_TRIGGER_PATHS)
    events = (
        "  pull_request:\n    branches:\n      - so\n    paths:\n" + paths
        + "  push:\n    branches:\n      - so\n    paths:\n" + paths
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != name + "\n\non:\n" + events):
        raise SystemExit("semantic preflight reconcile independent exact event header drift")
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [name, "on:", "permissions:", "jobs:"]:
        raise SystemExit("semantic preflight reconcile independent root YAML key shadow drift")
    leaves = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            leaves.append(line)
    if leaves != ["  contents: read"]:
        raise SystemExit("semantic preflight reconcile independent permission leaf shadow drift")
    body = source.split("\njobs:\n", 1)[1]
    headers = [
        line for line in body.splitlines()
        if line.startswith("  ") and not line.startswith("   ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if headers != ["  source-admission:"]:
        raise SystemExit("semantic preflight reconcile independent job mapping shadow drift")
    job_keys = [
        line for line in body.splitlines()
        if line.startswith("    ") and not line.startswith("     ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if job_keys != [
        "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')",
        "    permissions:", "    runs-on: ubuntu-latest",
        "    timeout-minutes: 5", "    steps:",
    ]:
        raise SystemExit("semantic preflight reconcile independent job key/permission shadow drift")
    section = body.split("    permissions:\n", 1)[1].split("    runs-on:", 1)[0]
    job_leaves = [
        line for line in section.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if job_leaves != ["      contents: read"]:
        raise SystemExit("semantic preflight reconcile independent job permission leaf shadow drift")


def prove_independent_yaml_authority_negatives(source: str) -> None:
    """Prove seventeen exact YAML diagnostics, including job/permission shadows."""
    validate_independent_yaml_authority(source)
    extra_event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if extra_event == source:
        raise SystemExit("semantic preflight reconcile independent YAML event fixture unchanged")
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
    marker = "\npermissions:\n  contents: read\n"
    if source.count(marker) != 1:
        raise SystemExit("semantic preflight reconcile independent YAML permission fixture anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(marker, marker + leaf, 1),
                      "permission leaf shadow drift"))
    for label, suffix in (
        ("duplicate job", "  source-admission: {}\n"),
        ("spaced job", "  source-admission : {}\n"),
        ("quoted job", "  'source-admission': {}\n"),
    ):
        cases.append((label, source.rstrip("\n") + "\n" + suffix,
                      "job mapping shadow drift"))
    marker = "    permissions:\n      contents: read\n"
    if source.count(marker) != 1:
        raise SystemExit("semantic preflight reconcile independent job leaf fixture anchor drift")
    for label, leaf in (
        ("spaced job leaf", "      contents : write\n"),
        ("quoted job leaf", "      'contents': write\n"),
    ):
        cases.append((label, source.replace(marker, marker + leaf, 1),
                      "job permission leaf shadow drift"))
    runs_on = "    runs-on: ubuntu-latest\n"
    if source.count(runs_on) != 1:
        raise SystemExit("semantic preflight reconcile independent late job fixture anchor drift")
    for label, leaf in (
        ("late permission", "    permissions:\n      contents: write\n"),
        ("late spaced permission", "    permissions :\n      contents: write\n"),
        ("late quoted permission", "    'permissions':\n      contents: write\n"),
    ):
        cases.append((label, source.replace(runs_on, runs_on + leaf, 1),
                      "job key/permission shadow drift"))
    if len(cases) != 17:
        raise SystemExit("semantic preflight reconcile independent YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("semantic preflight reconcile independent unchanged YAML fixture: " + label)
        try:
            validate_independent_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "semantic preflight reconcile independent " + diagnostic
            if str(exc) != expected:
                raise SystemExit("semantic preflight reconcile independent wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("semantic preflight reconcile independent accepted YAML mutation: " + label)
    print("PASS: semantic preflight reconcile independent YAML event/root/job/permission authority (17 exact-diagnostic negatives)")


def validate_independent(source: str, *, check_blob: bool = True) -> None:
    validate_independent_yaml_authority(source)
    validate_independent_trigger_reachability(source)
    for label, token, expected in INDEPENDENT_REQUIRED:
        if source.count(token) != expected:
            raise SystemExit("semantic preflight independent source drift: " + label)
    if not source.rstrip().endswith('          test -z "$(git status --porcelain)"'):
        raise SystemExit("semantic preflight independent final read-only terminator drift")
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != INDEPENDENT_BLOB:
            raise SystemExit("semantic preflight independent complete workflow source drift")


def prove_independent_runtime(source: str) -> None:
    for label, command, key, value, allowed in (
        ("PR so", INDEPENDENT_REQUIRED[9][1].strip(), "GITHUB_BASE_REF", "so", True),
        ("PR main", INDEPENDENT_REQUIRED[9][1].strip(), "GITHUB_BASE_REF", "main", False),
        ("PR absent", INDEPENDENT_REQUIRED[9][1].strip(), "GITHUB_BASE_REF", "", False),
        ("push so", INDEPENDENT_REQUIRED[10][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", INDEPENDENT_REQUIRED[10][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", INDEPENDENT_REQUIRED[10][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    ):
        if source.count(command) != 1:
            raise SystemExit("semantic preflight independent runtime predicate unreachable: " + label)
        result = subprocess.run(["bash", "-e", "-c", command],
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
            capture_output=True, check=False)
        if (result.returncode == 0) != allowed:
            raise SystemExit("semantic preflight independent branch runtime drift: " + label)
    predicate = INDEPENDENT_REQUIRED[11][1].strip()
    if source.count(predicate) != 1:
        raise SystemExit("semantic preflight independent SHA runtime predicate unreachable")
    for label, value, allowed in (
        ("lowercase", "a" * 40, True), ("numeric", "0" * 40, True),
        ("short", "a" * 39, False), ("long", "a" * 41, False),
        ("uppercase", "A" * 40, False), ("nonhex", "g" * 40, False),
        ("missing", "", False), ("substitution", "$(echo unexpected)", False),
    ):
        command = 'expected="${PROBE_SHA:-}"\n' + predicate
        result = subprocess.run(["bash", "-e", "-c", command],
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value},
            capture_output=True, check=False)
        if (result.returncode == 0) != allowed:
            raise SystemExit("semantic preflight independent SHA runtime drift: " + label)
    print("PASS: semantic preflight independent branch (6) and SHA (8) runtime cases")


def prove_independent_negatives(source: str) -> None:
    cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", "  pull_request:\n    paths:\n"),
        ("push target", "  push:\n    branches:\n      - so\n    paths:\n", "  push:\n    paths:\n"),
        ("workflow trigger", "      - \".github/workflows/backup-restore-drill-preflight-reconcile-negative.yml\"\n", ""),
        ("self trigger", "      - \".github/workflows/backup-restore-drill-preflight-reconcile-source-negative.yml\"\n", ""),
        ("validator trigger", "      - \"scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py\"\n", ""),
        ("checkout floating", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", "      - uses: actions/checkout@v4\n"),
        ("setup floating", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", "      - uses: actions/setup-python@v5\n"),
        ("credential persistence", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR head substitution", "          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n", "          PR_HEAD_SHA: ${{ github.sha }}\n"),
        ("PR base", "            test \"${GITHUB_BASE_REF:-}\" = \"so\"\n", ""),
        ("push ref", "            test \"${GITHUB_REF:-}\" = \"refs/heads/so\"\n", ""),
        ("SHA weakened", "          [[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]\n", "          test -n \"$expected\"\n"),
        ("HEAD weakened", "          test \"$(git rev-parse HEAD)\" = \"$expected\"\n", "          test -n \"$expected\"\n"),
        ("job scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", "    if: always()\n"),
        ("self execution", "          python scripts/validate-memory-os-backup-restore-drill-preflight-reconcile-workflow-negative.py\n", ""),
        ("injected action", "      - name: Prove reconcile source admission\n", "      - uses: unreviewed/action@v1\n      - name: Prove reconcile source admission\n"),
        ("appended shell", "          git diff --exit-code\n", "          git diff --exit-code\n          echo unreviewed\n"),
    )
    if len(cases) != 17 or tuple(label for label, _, _ in cases[-2:]) != ("injected action", "appended shell"):
        raise SystemExit("semantic preflight independent negative population drift")
    for index, (label, old, replacement) in enumerate(cases):
        if old not in source:
            raise SystemExit("semantic preflight independent negative anchor missing: " + label)
        try:
            validate_independent(source.replace(old, replacement, 1), check_blob=index >= 15)
        except SystemExit:
            continue
        raise SystemExit("semantic preflight independent accepted forbidden mutation: " + label)
    print(f"PASS: semantic preflight independent source admission ({len(cases) - 2} semantic anchor + 2 blob-only negatives)")




def prove_branch_guards_runtime() -> None:
    """Execute reviewed branch predicates against disposable synthetic refs."""
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
            raise SystemExit("semantic preflight reconcile runtime branch guard drift: " + label)
    print("PASS: semantic preflight reconcile PR/push branch guard runtime (6 cases)")


def prove_sha_guard_runtime() -> None:
    """Execute the shared PR and push/dispatch 40-hex predicate on synthetic input."""
    cases = (
        ("lowercase SHA", "a" * 40, True),
        ("numeric SHA", "0" * 40, True),
        ("short SHA", "a" * 39, False),
        ("long SHA", "a" * 41, False),
        ("uppercase SHA", "A" * 40, False),
        ("nonhex SHA", "g" * 40, False),
        ("missing SHA", "", False),
        ("literal substitution", "$(echo unexpected)", False),
    )
    command = 'expected="${PROBE_SHA:-}"\n' + REQUIRED[6][1].strip()
    for label, value, accepted in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}
        result = subprocess.run(
            ["bash", "-e", "-c", command], env=env, capture_output=True, check=False
        )
        if (result.returncode == 0) != accepted:
            raise SystemExit("semantic preflight reconcile SHA guard drift: " + label)
    print(f"PASS: semantic preflight reconcile shared PR/push SHA runtime ({len(cases)} cases)")


def validate_publisher_concurrency_authority(source: str) -> None:
    """Pin reviewed semantic preflight reconcile CI serialization independently of the blob."""
    marker = "\nconcurrency:\n"
    end = "\njobs:\n"
    group = ("  group: backup-restore-drill-preflight-reconcile-negative-"
             + chr(36) + "{{ github.event.pull_request.number || 'so' }}\n")
    expected = group + "  cancel-in-progress: false\n"
    if source.count(marker) != 1 or source.count(end) != 1:
        raise SystemExit("semantic preflight reconcile publisher concurrency scope drift")
    if source.split(marker, 1)[1].split(end, 1)[0] != expected:
        raise SystemExit("semantic preflight reconcile publisher concurrency scope drift")


def prove_publisher_concurrency_authority_negatives(source: str) -> None:
    """Reject ten YAML-equivalent publisher concurrency shadows by exact diagnostic."""
    validate_publisher_concurrency_authority(source)
    group = ("  group: backup-restore-drill-preflight-reconcile-negative-"
             + chr(36) + "{{ github.event.pull_request.number || 'so' }}\n")
    original = group + "  cancel-in-progress: false\n"
    cases = (
        ("global group", "  group: backup-restore-drill-preflight-reconcile-negative-global\n  cancel-in-progress: false\n"),
        ("cancel enabled", original.replace("false", "true")),
        ("duplicate group", original + "  group: unreviewed-global\n"),
        ("duplicate cancellation", original + "  cancel-in-progress: true\n"),
        ("spaced group", original + "  group : unreviewed-global\n"),
        ("quoted group", original + "  'group': unreviewed-global\n"),
        ("spaced cancellation", original + "  cancel-in-progress : true\n"),
        ("quoted cancellation", original + "  'cancel-in-progress': true\n"),
        ("unreviewed leaf", original + "  max-parallel: 10\n"),
        ("removed cancellation", group),
    )
    if source.count(original) != 1 or len(cases) != 10:
        raise SystemExit("semantic preflight reconcile publisher concurrency fixture anchor drift")
    for label, replacement in cases:
        mutated = source.replace(original, replacement, 1)
        if mutated == source:
            raise SystemExit("semantic preflight reconcile publisher inert concurrency fixture: " + label)
        try:
            validate_publisher_concurrency_authority(mutated)
        except SystemExit as exc:
            if str(exc) != "semantic preflight reconcile publisher concurrency scope drift":
                raise SystemExit(
                    "semantic preflight reconcile publisher wrong concurrency diagnostic: " + label + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("semantic preflight reconcile publisher accepted concurrency mutation: " + label)
    print("PASS: semantic preflight reconcile publisher concurrency serialization (10 exact-diagnostic negatives)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_publisher_yaml_authority_negatives(source)
    prove_publisher_concurrency_authority_negatives(source)
    independent = INDEPENDENT_PATH.read_text(encoding="utf-8")
    validate_independent(independent)
    prove_independent_trigger_negatives(independent)
    prove_independent_yaml_authority_negatives(independent)
    prove_branch_guards_runtime()
    prove_sha_guard_runtime()
    prove_independent_runtime(independent)
    prove_independent_negatives(independent)
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
            raise SystemExit(f"semantic preflight reconcile negative anchor missing: {label}")
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated, check_blob=False)
        except SystemExit:
            continue
        raise SystemExit(f"semantic preflight reconcile accepted forbidden mutation: {label}")
    sha_token = REQUIRED[6][1]
    second_sha = source.rfind(sha_token)
    if second_sha == source.find(sha_token):
        raise SystemExit("semantic preflight reconcile second SHA predicate missing")
    mutated_second_sha = (
        source[:second_sha] + '            test -n "$expected"\n' +
        source[second_sha + len(sha_token):]
    )
    try:
        validate(mutated_second_sha, check_blob=False)
    except SystemExit:
        pass
    else:
        raise SystemExit("semantic preflight reconcile accepted weakened second SHA predicate")
    # The canonical workflow may or may not end in a newline; both are valid.
    validate(source.rstrip("\n") + "\n", check_blob=False)
    try:
        validate(source + '\n          echo "unreviewed final command"\n')
    except SystemExit:
        pass
    else:
        raise SystemExit("semantic preflight reconcile accepted appended final command")
    for label, old, replacement in (
        ("PR base ref", REQUIRED[14][1], ""),
        ("PR target filter", REQUIRED[15][1], "  pull_request:\n    paths:\n"),
    ):
        if old not in source:
            raise SystemExit("semantic preflight reconcile PR branch negative anchor missing: " + label)
        try:
            validate(source.replace(old, replacement, 1), check_blob=False)
        except SystemExit:
            continue
        raise SystemExit("semantic preflight reconcile accepted forbidden PR branch mutation: " + label)
    for label, old, replacement in (
        ("inserted executable step", "      - name: Prove preflight partial-publication rollback\n", "      - run: echo unreviewed\n      - name: Prove preflight partial-publication rollback\n"),
        ("extra command before final read-only step", "          git diff --exit-code\n", "          git diff --exit-code\n          echo unreviewed\n"),
    ):
        if old not in source:
            raise SystemExit("semantic preflight reconcile whole-source negative anchor missing: " + label)
        try:
            validate(source.replace(old, replacement, 1))
        except SystemExit:
            continue
        raise SystemExit("semantic preflight reconcile accepted forbidden whole-source mutation: " + label)
    print(f"PASS: semantic preflight reconcile workflow source admission ({len(cases) + 3} semantic anchor negatives; 3 complete-source/terminator negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
