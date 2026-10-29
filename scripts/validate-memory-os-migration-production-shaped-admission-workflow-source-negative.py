#!/usr/bin/env python3
"""Negative and runtime proof for migration production-shaped admission CI source trust."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/migration-production-shaped-admission.yml"
INDEPENDENT = ".github/workflows/migration-production-shaped-admission-source-negative.yml"
SELF = "scripts/validate-memory-os-migration-production-shaped-admission-workflow-source-negative.py"
PUBLISHER_SHA = "de15191e084b753b379ca6f657b57521fa1dbf92"
INDEPENDENT_SHA = "6e5d70153437516601b00c9d6d542dc90abf7191"

PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/migration-production-shaped-admission.yml",
    ".github/workflows/migration-production-shaped-admission-source-negative.yml",
    "scripts/validate-memory-os-migration-production-shaped-admission-workflow-source-negative.py",
    "scripts/validate-memory-os-migration-production-shaped-admission-permission-negative.py",
    "contracts/operations/requests/migration-production-shaped-admission-foundation.v1.json",
    "contracts/operations/migration-production-shaped-admission-contract.v1.json",
    "contracts/operations/migration-production-shaped-admission-registry.v1.json",
    "docs/evidence/migration-production-shaped-admission/independent-reviews/**",
    "contracts/operations/migration-lifecycle-contract.v1.json",
    "contracts/operations/migration-evidence-registry.v1.json",
    "contracts/operations/migration-evidence-registry-contract.v1.json",
    "contracts/operations/release-baseline-registry-contract.v1.json",
    "contracts/operations/release-baseline-registry.v1.json",
    "contracts/operations/release-compatibility-pair-registry.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "scripts/memory_os_migration_production_admission_ledger.py",
    "scripts/register-memory-os-migration-production-shaped-admission.py",
    "scripts/validate-memory-os-migration-production-shaped-admission.py",
    "scripts/validate-memory-os-migration-production-shaped-admission-negative.py",
    "scripts/validate-memory-os-migration-production-shaped-admission-generation-authority-negative.py",
    "scripts/validate-memory-os-migration-production-admission-ledger-authority-negative.py",
    "scripts/validate-memory-os-migration-production-shaped-admission-reconcile-rollback.py",
    "scripts/reconcile-memory-os-migration-production-shaped-admission.py",
    "scripts/register-memory-os-release-baseline.py",
    "scripts/register-memory-os-release-compatibility-pair.py",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation.py",
    "scripts/register-memory-os-migration-rehearsal-evidence.py",
    "scripts/validate-memory-os-migration-evidence-registry.py",
    "scripts/validate-memory-os-release-baseline-registry.py",
    "scripts/validate-memory-os-migration-lifecycle.py",
    "scripts/validate-memory-os-operability.py",
)
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/migration-production-shaped-admission.yml",
    ".github/workflows/migration-production-shaped-admission-source-negative.yml",
    "scripts/validate-memory-os-migration-production-shaped-admission-workflow-source-negative.py",
    ".github/workflows/migration-production-shaped-negative-isolation.yml",
    "scripts/diagnose-memory-os-migration-production-shaped-admission-negative-isolated.py",
    "scripts/validate-memory-os-migration-production-shaped-admission-negative.py",
    ".github/workflows/migration-production-shaped-admission-permission-negative.yml",
    "scripts/validate-memory-os-migration-production-shaped-admission-permission-negative.py",
)
ISOLATION = ".github/workflows/migration-production-shaped-negative-isolation.yml"
ISOLATION_SCRIPT = "scripts/diagnose-memory-os-migration-production-shaped-admission-negative-isolated.py"
NEGATIVE_SCRIPT = "scripts/validate-memory-os-migration-production-shaped-admission-negative.py"
ISOLATION_SHA = "e439088b4ac8ab0fce2a08bfd46f38a2a8b33933"
ISOLATION_SCRIPT_SHA = "00dcd7e95896b7352f682d8d1eeefbd3f8920755"
NEGATIVE_SCRIPT_SHA = "3366455aa1140f464d7442b2b788ed3240ee898b"
PERMISSION_CI = ".github/workflows/migration-production-shaped-admission-permission-negative.yml"
PERMISSION_SCRIPT = "scripts/validate-memory-os-migration-production-shaped-admission-permission-negative.py"
PERMISSION_CI_SHA = "97cf42f2e0a206a9fb489a43e9c16e9f941fc9e3"
PERMISSION_SCRIPT_SHA = "be584a02b612a7df2d399beefcd6defa760764e3"
D = chr(36)
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
PR_EVENT = 'test "' + D + '{GITHUB_EVENT_NAME:-}" = "pull_request"'
WRITER_EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
PR_SHA_FORMAT = '[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA_FORMAT = '[[ "' + D + '{GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'
REDACTION = "'output': 'REDACTED: migration production-shaped admission failed; raw output withheld',"
SUPPRESS = 'printf "Migration production-shaped admission exit code: %s (raw validator log suppressed)\\n" "$code"'
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
PR_CHECKOUT = 'ref: ' + D + '{{ github.event.pull_request.head.sha }}'
WRITER_CHECKOUT = 'ref: ' + D + '{{ github.sha }}'

PUBLISHER_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("validator trigger", '      - "' + SELF + '"\n', 2),
    ("permission validator trigger", '      - "scripts/validate-memory-os-migration-production-shaped-admission-permission-negative.py"\n', 2),
    ("checkout pin", CHECKOUT, 2),
    ("setup pin", SETUP, 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("writer credentials", "          persist-credentials: true\n", 1),
    ("PR base", PR_BASE, 1),
    ("PR event", PR_EVENT, 1),
    ("writer event", WRITER_EVENT, 1),
    ("writer branch", WRITER_REF, 1),
    ("PR SHA format", PR_SHA_FORMAT, 1),
    ("writer SHA format", WRITER_SHA_FORMAT, 1),
    ("source self check", "          python " + SELF + "\n", 2),
    ("writer scope", WRITER_SCOPE, 1),
    ("writer token", "      contents: write\n", 1),
    ("root read token", "permissions:\n  contents: read\n", 1),
    ("PR read token", "      contents: read\n", 1),
    ("checkout PR head", PR_CHECKOUT, 1),
    ("checkout writer head", WRITER_CHECKOUT, 1),
    ("PR HEAD identity", 'test "$(git rev-parse HEAD)" = "$PR_HEAD_SHA"', 1),
    ("writer HEAD identity", 'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', 1),
    ("redacted diagnostic", REDACTION, 1),
    ("suppressed CI log", SUPPRESS, 1),
    ("bounded failed stage", 'if [[ "$code" != "0" ]]; then printf "Migration admission failed stage: %s\\n" "$stage"; fi', 1),
    ("compile stage", "          stage=compile\n", 1),
    ("generation authority stage", "            stage=generation-authority\n", 1),
    ("ledger authority stage", "            stage=ledger-authority\n", 1),
    ("admission negative stage", "            stage=admission-negative\n", 1),
    ("rollback stage", "            stage=rollback\n", 1),
    ("reconcile stage", "            stage=reconcile\n", 1),
    ("lifecycle stage", "            stage=lifecycle\n", 1),
    ("operability stage", "            stage=operability\n", 1),
    ("no raw tail", "text[-12000:]", 0),
    ("no raw CI log", '          cat "$log"\n', 0),
)
INDEPENDENT_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("validator trigger", '      - "' + SELF + '"\n', 2),
    ("isolation workflow trigger", '      - "' + ISOLATION + '"\n', 2),
    ("isolation runner trigger", '      - "' + ISOLATION_SCRIPT + '"\n', 2),
    ("migration negative trigger", '      - "' + NEGATIVE_SCRIPT + '"\n', 2),
    ("permission CI trigger", '      - "' + PERMISSION_CI + '"\n', 2),
    ("permission script trigger", '      - "' + PERMISSION_SCRIPT + '"\n', 2),
    ("checkout pin", CHECKOUT, 1),
    ("setup pin", SETUP, 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR base", PR_BASE, 1),
    ("push branch", WRITER_REF, 1),
    ("SHA format", SHA_FORMAT, 1),
    ("self execution", "          python " + SELF + "\n", 1),
    ("read permissions", "  contents: read\n", 2),
    ("source job scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
)



def validate_trigger_reachability(
    source: str, *, publisher: bool, trigger_paths: tuple[str, ...] | None = None
) -> None:
    """Pin every reviewed publisher/independent CI path under both PR and push."""
    expected = PUBLISHER_TRIGGER_PATHS if publisher else INDEPENDENT_TRIGGER_PATHS
    paths = expected if trigger_paths is None else trigger_paths
    if len(paths) != len(expected) or len(set(paths)) != len(expected):
        raise SystemExit("migration production-shaped CI trigger inventory shortened or duplicated")
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    end = "  workflow_dispatch:\n" if publisher else "\npermissions:\n"
    if any(source.count(marker) != 1 for marker in (pr, push, end)):
        raise SystemExit("migration production-shaped CI event marker drift")
    if not (source.index(pr) < source.index(push) < source.index(end)):
        raise SystemExit("migration production-shaped CI event order drift")
    for event, start, stop in (("pull_request", pr, push), ("push", push, end)):
        block = source.split(start, 1)[1].split(stop, 1)[0]
        actual = tuple(line for line in block.splitlines()
                       if line.strip() and not line.lstrip().startswith("#"))
        approved = tuple('      - "' + path + '"' for path in paths)
        if actual != approved:
            raise SystemExit("migration production-shaped CI " + event + " exact trigger inventory drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    """Test all event-specific omissions, additions and shortened inventory."""
    pr = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push = "  push:\n    branches:\n      - so\n    paths:\n"
    for label, source, paths, is_publisher in (
        ("publisher", publisher, PUBLISHER_TRIGGER_PATHS, True),
        ("independent", independent, INDEPENDENT_TRIGGER_PATHS, False),
    ):
        end = "  workflow_dispatch:\n" if is_publisher else "\npermissions:\n"
        for event, start, stop in (("pull_request", pr, push), ("push", push, end)):
            start_index = source.index(start) + len(start)
            end_index = source.index(stop, start_index)
            block = source[start_index:end_index]
            for path in paths:
                token = '      - "' + path + '"\n'
                if block.count(token) != 1:
                    raise SystemExit("migration production-shaped CI mutation anchor drift: " + path)
                mutated = source[:start_index] + block.replace(token, "", 1) + source[end_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("migration production-shaped CI accepted missing " + label + " " + event + " trigger: " + path)
            for name, injection in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                mutated = source[:start_index] + injection + source[start_index:]
                try:
                    validate_trigger_reachability(mutated, publisher=is_publisher)
                except SystemExit:
                    pass
                else:
                    raise SystemExit("migration production-shaped CI accepted " + label + " " + event + " " + name)
        try:
            validate_trigger_reachability(source, publisher=is_publisher, trigger_paths=paths[:-1])
        except SystemExit:
            pass
        else:
            raise SystemExit("migration production-shaped CI accepted shortened " + label + " inventory")
    print("PASS: migration production-shaped CI event triggers (88 removals; 16 additions; 2 shortened inventory negatives)")


def read(relative: str) -> str:
    path = ROOT / relative
    try:
        if not path.is_file() or path.is_symlink():
            raise ValueError("not a regular file")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped repository root")
        return path.read_text(encoding="utf-8")
    except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
        raise SystemExit("migration production-shaped admission source missing/substituted: " + relative) from exc


def validate(
    publisher: str, independent: str, *,
    check_publisher_blob: bool = True, check_independent_blob: bool = True
) -> None:
    validate_trigger_reachability(publisher, publisher=True)
    validate_trigger_reachability(independent, publisher=False)
    for name, source, required, reviewed in (
        ("publisher", publisher, PUBLISHER_REQUIRED, PUBLISHER_SHA),
        ("independent", independent, INDEPENDENT_REQUIRED, INDEPENDENT_SHA),
    ):
        validate_yaml_authority(source, name)
        for label, token, count in required:
            if source.count(token) != count:
                raise SystemExit("migration production-shaped admission " + name + " source drift: " + label)
        data = source.encode("utf-8")
        digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        if (check_publisher_blob if name == "publisher" else check_independent_blob) and digest != reviewed:
            raise SystemExit("migration production-shaped admission " + name + " complete source drift")


def validate_yaml_authority(content: str, kind: str) -> None:
    """Bind effective reviewed YAML event, root and permission authority separately from blob identity."""
    if kind == "publisher":
        name = "name: Migration Production Shaped Admission"
        events = ["  pull_request:", "  push:", "  workflow_dispatch:"]
        roots = [name, "on:", "permissions:", "concurrency:", "jobs:"]
    elif kind == "independent":
        name = "name: Migration Production Shaped Admission Source Negative"
        events = ["  pull_request:", "  push:"]
        roots = [name, "on:", "permissions:", "jobs:"]
    else:
        raise SystemExit("migration production-shaped unknown YAML authority kind")
    prefix = "migration production-shaped " + kind + " "
    if (content.count("\non:\n") != 1 or content.count("\npermissions:\n") != 1
            or not content.startswith(name + "\n\non:\n")):
        raise SystemExit(prefix + "event header drift")
    event_block = content.split("\non:\n", 1)[1].split("\npermissions:\n", 1)[0]
    event_keys = [
        line for line in event_block.splitlines()
        if line.startswith("  ") and not line.startswith("    ")
        and line.strip() and not line.lstrip().startswith("#")
    ]
    if event_keys != events:
        raise SystemExit(prefix + "event topology drift")
    root_keys = [
        line for line in content.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if root_keys != roots:
        raise SystemExit(prefix + "root YAML key shadow drift")
    permission_rows = []
    for line in content.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            permission_rows.append(line)
    if permission_rows != ["  contents: read"]:
        raise SystemExit(prefix + "permission leaf shadow drift")
    body = content.split("\n" + "jobs:\n", 1)[1]
    if kind == "publisher":
        jobs = (
            ("validate-pr", "    if: github.event_name == 'pull_request'", "read", 8),
            ("reconcile", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "write", 8),
        )
    else:
        jobs = (
            ("source-negative", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "read", 5),
        )
    headers = [
        row for row in body.splitlines()
        if row.startswith("  ") and not row.startswith("   ")
        and row.strip() and not row.lstrip().startswith("#")
    ]
    if headers != ["  " + job[0] + ":" for job in jobs]:
        raise SystemExit(prefix + "job mapping shadow drift")
    for index, (job, condition, scope, timeout) in enumerate(jobs):
        section = body.split("  " + job + ":\n", 1)[1]
        if index + 1 < len(jobs):
            section = section.split("  " + jobs[index + 1][0] + ":\n", 1)[0]
        keys = [
            row for row in section.splitlines()
            if row.startswith("    ") and not row.startswith("     ")
            and row.strip() and not row.lstrip().startswith("#")
        ]
        if keys != [
            condition, "    permissions:", "    runs-on: ubuntu-latest",
            "    timeout-minutes: " + str(timeout), "    steps:",
        ]:
            raise SystemExit(prefix + "job key/permission shadow drift")
        marker = "    permissions:\n"
        if (section.count(marker) != 1
                or section.split(marker, 1)[1].split("    runs-on: ubuntu-latest\n", 1)[0]
                != "      contents: " + scope + "\n"):
            raise SystemExit(prefix + "job permission scope drift")


def prove_yaml_authority_negatives(publisher: str, independent: str) -> None:
    """Exercise both CI YAML authorities with exact-diagnostic semantic negative mutations."""
    count = 0
    for kind, content in (("publisher", publisher), ("independent", independent)):
        validate_yaml_authority(content, kind)
        event = content.replace("on:\n", "on:\n  issues:\n", 1)
        if event == content:
            raise SystemExit("migration production-shaped " + kind + " event fixture anchor drift")
        cases = [("extra event", event, "event topology drift")]
        for label, suffix in (
            ("spaced on", "on :\n  issues:\n"),
            ("quoted on", "'on':\n  issues:\n"),
            ("spaced permissions", "permissions :\n  contents: write\n"),
            ("quoted permissions", "'permissions':\n  contents: write\n"),
            ("spaced jobs", "jobs : {}\n"),
            ("quoted jobs", "'jobs': {}\n"),
        ):
            cases.append((label, content.rstrip("\n") + "\n" + suffix,
                          "root YAML key shadow drift"))
        marker = "\npermissions:\n  contents: read\n"
        if content.count(marker) != 1:
            raise SystemExit("migration production-shaped " + kind + " permission fixture anchor drift")
        for label, leaf in (
            ("spaced contents", "  contents : write\n"),
            ("quoted contents", "  'contents': write\n"),
        ):
            cases.append((label, content.replace(marker, marker + leaf, 1),
                          "permission leaf shadow drift"))
        jobs = (
            (("validate-pr", "    if: github.event_name == 'pull_request'", "read"),
             ("reconcile", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'", "write"))
            if kind == "publisher" else
            (("source-negative", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')", "read"),)
        )
        for job, condition, scope in jobs:
            job_anchor = "  " + job + ":\n"
            if content.count(job_anchor) != 1:
                raise SystemExit("migration production-shaped " + kind + " job fixture anchor drift: " + job)
            for label, suffix in (
                ("duplicate job", "  " + job + ": {}\n"),
                ("spaced job", "  " + job + " : {}\n"),
                ("quoted job", "  '" + job + "': {}\n"),
            ):
                cases.append((job + " " + label, content.rstrip("\n") + "\n" + suffix,
                              "job mapping shadow drift"))
            prefix, section = content.split(job_anchor, 1)
            runs_on = "    runs-on: ubuntu-latest\n"
            if runs_on not in section:
                raise SystemExit("migration production-shaped " + kind + " runs-on fixture anchor drift: " + job)
            for label, leaf in (
                ("job permission", "    permissions:\n      contents: write\n"),
                ("spaced job permission", "    permissions :\n      contents: write\n"),
                ("quoted job permission", "    'permissions':\n      contents: write\n"),
            ):
                cases.append((job + " " + label,
                              prefix + job_anchor + section.replace(runs_on, runs_on + leaf, 1),
                              "job key/permission shadow drift"))
            permission = "    permissions:\n      contents: " + scope + "\n"
            if permission not in section:
                raise SystemExit("migration production-shaped " + kind + " scope fixture anchor drift: " + job)
            alternate = "write" if scope == "read" else "read"
            cases.append((job + " direct scope", prefix + job_anchor + section.replace(
                permission, "    permissions:\n      contents: " + alternate + "\n", 1),
                "job permission scope drift"))
            for label, leaf in (
                ("spaced contents", "      contents : write\n"),
                ("quoted contents", "      'contents': write\n"),
            ):
                cases.append((job + " " + label, prefix + job_anchor + section.replace(
                    permission, permission + leaf, 1), "job permission scope drift"))
            if condition + "\n" not in section:
                raise SystemExit("migration production-shaped " + kind + " event fixture anchor drift: " + job)
            cases.append((job + " event bypass", prefix + job_anchor + section.replace(
                condition + "\n", "    if: true\n", 1),
                "job key/permission shadow drift"))
        if len(cases) != (29 if kind == "publisher" else 19):
            raise SystemExit("migration production-shaped " + kind + " YAML fixture count drift")
        for label, mutated, diagnostic in cases:
            if mutated == content:
                raise SystemExit("migration production-shaped " + kind + " unchanged YAML fixture: " + label)
            try:
                validate_yaml_authority(mutated, kind)
            except SystemExit as exc:
                expected = "migration production-shaped " + kind + " " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("migration production-shaped " + kind + " wrong YAML diagnostic: "
                                     + label + ": " + str(exc)) from exc
            else:
                raise SystemExit("migration production-shaped " + kind + " accepted YAML mutation: " + label)
            count += 1
    if count != 48:
        raise SystemExit("migration production-shaped YAML negative population drift")
    print("PASS: migration production-shaped publisher/independent YAML event/root/job/permission authority (48 exact-diagnostic negatives)")



def validate_concurrency_authority(publisher: str) -> None:
    """Bind the reviewed migration admission publisher's noncancelling concurrency."""
    marker = "\nconcurrency:\n"
    end = "\njobs:\n"
    expected = (
        "  group: migration-production-shaped-admission-${{ github.ref }}\n"
        "  cancel-in-progress: false\n"
    )
    if publisher.count(marker) != 1 or publisher.count(end) != 1:
        raise SystemExit("migration production-shaped publisher concurrency scope drift")
    if publisher.split(marker, 1)[1].split(end, 1)[0] != expected:
        raise SystemExit("migration production-shaped publisher concurrency scope drift")


def prove_concurrency_authority_negatives(publisher: str) -> None:
    """Ten expected-diagnostic cases for publisher serialization/cancellation."""
    validate_concurrency_authority(publisher)
    original = (
        "  group: migration-production-shaped-admission-${{ github.ref }}\n"
        "  cancel-in-progress: false\n"
    )
    variants = (
        ("global group", "  group: migration-production-shaped-admission-global\n"
         "  cancel-in-progress: false\n"),
        ("cancel enabled", original.replace("false", "true")),
        ("duplicate group", original + "  group: unreviewed-global\n"),
        ("duplicate cancellation", original + "  cancel-in-progress: true\n"),
        ("spaced group", original + "  group : unreviewed-global\n"),
        ("quoted group", original + "  'group': unreviewed-global\n"),
        ("spaced cancellation", original + "  cancel-in-progress : true\n"),
        ("quoted cancellation", original + "  'cancel-in-progress': true\n"),
        ("unreviewed leaf", original + "  max-parallel: 100\n"),
        ("removed cancellation", original.replace("  cancel-in-progress: false\n", "")),
    )
    if publisher.count(original) != 1:
        raise SystemExit("migration production-shaped concurrency mutation anchor drift")
    for name, changed_block in variants:
        changed = publisher.replace(original, changed_block, 1)
        if changed == publisher:
            raise SystemExit("migration production-shaped unchanged concurrency fixture: " + name)
        try:
            validate_concurrency_authority(changed)
        except SystemExit as exc:
            if str(exc) != "migration production-shaped publisher concurrency scope drift":
                raise SystemExit("migration production-shaped wrong concurrency diagnostic: "
                                 + name + ": " + str(exc)) from exc
        else:
            raise SystemExit("migration production-shaped accepted concurrency mutation: " + name)
    print("PASS: migration production-shaped publisher concurrency serialization (10 exact-diagnostic negatives)")


def runtime(publisher: str, independent: str) -> None:
    for name, source in (("publisher", publisher), ("independent", independent)):
        for label, token, key, value, allow in (
            ("base so", PR_BASE, "GITHUB_BASE_REF", "so", True),
            ("base main", PR_BASE, "GITHUB_BASE_REF", "main", False),
            ("base empty", PR_BASE, "GITHUB_BASE_REF", "", False),
            ("ref so", WRITER_REF, "GITHUB_REF", "refs/heads/so", True),
            ("ref main", WRITER_REF, "GITHUB_REF", "refs/heads/main", False),
            ("ref tag", WRITER_REF, "GITHUB_REF", "refs/tags/v1", False),
        ):
            if source.count(token) != 1:
                raise SystemExit("migration production-shaped admission unreachable runtime branch: " + name + " " + label)
            result = subprocess.run(["bash", "-e", "-c", token], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}, capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("migration production-shaped admission branch runtime drift: " + name + " " + label)
    for token, allowed in ((PR_EVENT, ("pull_request",)), (WRITER_EVENT, ("push", "workflow_dispatch"))):
        for event in ("pull_request", "push", "workflow_dispatch", "", "schedule"):
            result = subprocess.run(["bash", "-e", "-c", token], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event}, capture_output=True, check=False)
            if (result.returncode == 0) != (event in allowed):
                raise SystemExit("migration production-shaped admission event runtime drift: " + event)
    for label, var, predicate in (("PR", "PR_HEAD_SHA", PR_SHA_FORMAT), ("writer", "GITHUB_SHA", WRITER_SHA_FORMAT), ("independent", "expected", SHA_FORMAT)):
        for value, allow in (("a" * 40, True), ("0" * 40, True), ("A" * 40, False), ("g" * 40, False), ("a" * 39, False), ("a" * 41, False), ("", False), ("$(echo bad)", False)):
            prefix = var + '="' + D + '{PROBE_SHA:-}"\n'
            result = subprocess.run(["bash", "-e", "-c", prefix + predicate],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}, capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("migration production-shaped admission SHA runtime drift: " + label + " " + value[:10])
    print("PASS: migration production-shaped admission branch/event/SHA runtime (46 cases)")


def diagnostic_runtime(publisher: str) -> None:
    start, end = "          python - <<'PY'\n", "          PY\n"
    if publisher.count(start) != 1 or publisher.count(end) != 1:
        raise SystemExit("migration production-shaped admission diagnostic writer not unique")
    inline = publisher.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="migration-production-shaped-admission-diagnostic-") as directory:
        env = os.environ.copy()
        env.update({"SOURCE_COMMIT_SHA": "e" * 40, "ADMISSION_EXIT_CODE": "23", "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_MIGRATION"})
        result = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env, capture_output=True, text=True, check=False)
        if result.returncode:
            raise SystemExit("migration production-shaped admission isolated diagnostic failed: " + result.stderr[:500])
        output = Path(directory) / "docs/fixtures/memory-os-operability/migration-production-shaped-admission-diagnostic.last.json"
        raw = output.read_text(encoding="utf-8")
        value = json.loads(raw)
        if value.get("output") != "REDACTED: migration production-shaped admission failed; raw output withheld":
            raise SystemExit("migration production-shaped admission diagnostic persisted raw validator output")
        if value.get("sourceCommitSha") != "e" * 40 or value.get("exitCode") != 23:
            raise SystemExit("migration production-shaped admission diagnostic source/exit binding drift")
        if value.get("containsSecrets") is not False or value.get("productionEvidence") is not False or value.get("productionReady") is not False:
            raise SystemExit("migration production-shaped admission diagnostic evidence/readiness flag drift")
        if value.get("admittedRehearsalCount") != 0 or "CANARY_DO_NOT_PERSIST_MIGRATION" in raw:
            raise SystemExit("migration production-shaped admission diagnostic fabricated evidence or persisted canary")
        output.chmod(0o640)
        preserved = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                   capture_output=True, text=True, timeout=15, check=False)
        if preserved.returncode or stat.S_IMODE(output.stat().st_mode) != 0o640:
            raise SystemExit("migration production-shaped diagnostic did not preserve existing mode")
        previous = output.read_bytes()
        for label, before, replacement in (
            ("replace", "os.replace(temp_name, path)", "raise OSError('synthetic admission diagnostic replace failure')"),
            ("fsync", "os.fsync(handle.fileno())", "raise OSError('synthetic admission diagnostic fsync failure')"),
        ):
            if script.count(before) != 1:
                raise SystemExit("migration production-shaped diagnostic failure anchor drift: " + label)
            injected = script.replace(before, replacement, 1)
            failure = subprocess.run([sys.executable, "-c", injected], cwd=directory, env=env,
                                     capture_output=True, text=True, timeout=15, check=False)
            if failure.returncode == 0 or "synthetic admission diagnostic " + label + " failure" not in failure.stderr:
                raise SystemExit("migration production-shaped diagnostic failure did not execute: " + label)
            if output.read_bytes() != previous or stat.S_IMODE(output.stat().st_mode) != 0o640:
                raise SystemExit("migration production-shaped diagnostic failure changed existing output: " + label)
            if list(output.parent.glob(".migration-production-shaped-admission-diagnostic.*.tmp")):
                raise SystemExit("migration production-shaped diagnostic failure left temporary file: " + label)
        outside = Path(directory) / "external-admission-diagnostic-canary"
        outside.write_bytes(previous)
        output.unlink()
        output.symlink_to(outside)
        symlink = subprocess.run([sys.executable, "-c", script], cwd=directory, env=env,
                                 capture_output=True, text=True, timeout=15, check=False)
        if symlink.returncode == 0 or "target must not be a symlink" not in symlink.stderr:
            raise SystemExit("migration production-shaped diagnostic accepted symlink target")
        if not output.is_symlink() or outside.read_bytes() != previous:
            raise SystemExit("migration production-shaped diagnostic mutated external symlink target")
        if list(output.parent.glob(".migration-production-shaped-admission-diagnostic.*.tmp")):
            raise SystemExit("migration production-shaped diagnostic symlink rejection left temporary file")
    print("PASS: migration production-shaped admission diagnostic redaction and atomic runtime (5 cases)")


def negatives(publisher: str, independent: str) -> None:
    publisher_cases = (
        ("PR branch", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("validator trigger", '      - "' + SELF + '"\n', ""),
        ("permission validator trigger", '      - "scripts/validate-memory-os-migration-production-shaped-admission-permission-negative.py"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("PR credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("writer credentials", "          persist-credentials: true\n", ""),
        ("PR base", PR_BASE, "true"),
        ("writer branch", WRITER_REF, "true"),
        ("writer event", WRITER_EVENT, "true"),
        ("PR event", PR_EVENT, "true"),
        ("PR SHA format", PR_SHA_FORMAT, 'test -n "$PR_HEAD_SHA"'),
        ("writer SHA format", WRITER_SHA_FORMAT, 'test -n "$GITHUB_SHA"'),
        ("broad writer job", WRITER_SCOPE, "    if: github.event_name != 'pull_request'\n"),
        ("self check", "          python " + SELF + "\n", ""),
        ("checkout PR", PR_CHECKOUT, WRITER_CHECKOUT),
        ("checkout writer", WRITER_CHECKOUT, 'ref: ' + D + '{{ github.ref }}'),
        ("raw diagnostic", REDACTION, "'output': Path('/tmp/migration-production-shaped-admission.log').read_text(),"),
        ("raw CI echo", SUPPRESS, 'cat "$log"'),
        ("missing failed stage", 'if [[ "$code" != "0" ]]; then printf "Migration admission failed stage: %s\\n" "$stage"; fi', ""),
        ("skip operability stage", "            stage=operability\n", ""),
        ("skip compile stage", "          stage=compile\n", ""),
        ("unreviewed Action", "      - name: Confirm exact clean authority source\n", "      - uses: unreviewed/action@v1\n      - name: Confirm exact clean authority source\n"),
        ("unreviewed shell", "      - name: Confirm exact clean authority source\n", "      - run: echo unreviewed\n      - name: Confirm exact clean authority source\n"),
    )
    independent_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("validator trigger", '      - "' + SELF + '"\n', ""),
        ("isolation workflow trigger", '      - "' + ISOLATION + '"\n', ""),
        ("isolation runner trigger", '      - "' + ISOLATION_SCRIPT + '"\n', ""),
        ("migration negative trigger", '      - "' + NEGATIVE_SCRIPT + '"\n', ""),
        ("permission CI trigger", '      - "' + PERMISSION_CI + '"\n', ""),
        ("permission script trigger", '      - "' + PERMISSION_SCRIPT + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("persist credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base", PR_BASE, "true"),
        ("push branch", WRITER_REF, "true"),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("self execution", "          python " + SELF + "\n", ""),
        ("unreviewed Action", "      - name: Prove migration production-shaped admission publisher source\n", "      - uses: unreviewed/action@v1\n      - name: Prove migration production-shaped admission publisher source\n"),
        ("unreviewed shell", "      - name: Prove migration production-shaped admission publisher source\n", "      - run: echo unreviewed\n      - name: Prove migration production-shaped admission publisher source\n"),
    )
    blob_only = {
        "publisher": {"unreviewed Action", "unreviewed shell"},
        "independent": {"unreviewed Action", "unreviewed shell"},
    }
    semantic_counts = {"publisher": 0, "independent": 0}
    blob_counts = {"publisher": 0, "independent": 0}
    for name, original, cases in (("publisher", publisher, publisher_cases), ("independent", independent, independent_cases)):
        for label, before, after in cases:
            if before not in original:
                raise SystemExit("migration production-shaped admission negative fixture missing: " + name + " " + label)
            mutated = original.replace(before, after, 1)
            if mutated == original:
                raise SystemExit("migration production-shaped admission negative fixture unchanged: " + name + " " + label)
            required = PUBLISHER_REQUIRED if name == "publisher" else INDEPENDENT_REQUIRED
            semantic = any(mutated.count(token) != original.count(token) for _, token, _ in required)
            if semantic == (label in blob_only[name]):
                raise SystemExit("migration production-shaped source mutation classification drift: " + name + " " + label)
            semantic_counts[name] += int(semantic)
            blob_counts[name] += int(not semantic)
            try:
                if name == "publisher":
                    validate(mutated, independent, check_publisher_blob=not semantic)
                else:
                    validate(publisher, mutated, check_independent_blob=not semantic)
            except SystemExit:
                continue
            raise SystemExit("migration production-shaped admission accepted source mutation: " + name + " " + label)
    if semantic_counts != {"publisher": 24, "independent": 16} or blob_counts != {"publisher": 2, "independent": 2}:
        raise SystemExit("migration production-shaped source semantic/blob-only population drift")
    print("PASS: migration production-shaped source negatives (24 publisher + 16 independent semantic; 2 publisher + 2 independent blob-only)")



def prove_failed_stage_runtime(publisher: str) -> None:
    """Prove the bounded stage marker emits no validator output or success noise."""
    token = 'if [[ "$code" != "0" ]]; then printf "Migration admission failed stage: %s\\n" "$stage"; fi'
    if publisher.count(token) != 1:
        raise SystemExit("migration admission bounded failure stage not uniquely reachable")
    for code, stage, expected in (
        ("1", "compile", "Migration admission failed stage: compile\n"),
        ("75", "reconcile", "Migration admission failed stage: reconcile\n"),
        ("0", "operability", ""),
    ):
        result = subprocess.run(["bash", "-e", "-c", token],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "code": code, "stage": stage},
                                capture_output=True, text=True, check=False)
        if result.returncode != 0 or result.stdout != expected or result.stderr:
            raise SystemExit("migration admission failed-stage runtime drift: " + stage + " code " + code)
    print("PASS: migration admission bounded failed-stage runtime (3 cases)")



def require_isolation_blob(label: str, source: str, expected: str) -> None:
    """Use the same fail-closed check for canonical and mutated source."""
    data = source.encode("utf-8")
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    if digest != expected:
        raise SystemExit("migration isolated negative source drift: " + label)


def verify_isolation_blob_bindings() -> None:
    """Prove the production guard rejects each mutated source, not just a different hash."""
    for label, path, expected in (
        ("isolation workflow", ISOLATION, ISOLATION_SHA),
        ("isolation runner", ISOLATION_SCRIPT, ISOLATION_SCRIPT_SHA),
        ("migration negative", NEGATIVE_SCRIPT, NEGATIVE_SCRIPT_SHA),
    ):
        source = read(path)
        require_isolation_blob(label, source, expected)
        for suffix in ("\n# inert source mutation\n", "\n# disabled test\n"):
            try:
                require_isolation_blob(label, source + suffix, expected)
            except SystemExit as exc:
                if str(exc) != "migration isolated negative source drift: " + label:
                    raise
            else:
                raise SystemExit("migration isolated negative mutation accepted: " + label)
    print("PASS: migration isolated workflow/runner/negative source bindings (6 mutations)")


def verify_permission_blob_bindings() -> None:
    """Independent proof for the permission CI and its executable validator."""
    for label, path, expected in (
        ("permission workflow", PERMISSION_CI, PERMISSION_CI_SHA),
        ("permission validator", PERMISSION_SCRIPT, PERMISSION_SCRIPT_SHA),
    ):
        source = read(path)
        require_isolation_blob(label, source, expected)
        for suffix in ("\n# inert permission mutation\n", "\n# disabled permission guard\n"):
            try:
                require_isolation_blob(label, source + suffix, expected)
            except SystemExit as exc:
                if str(exc) != "migration isolated negative source drift: " + label:
                    raise
            else:
                raise SystemExit("migration permission source mutation accepted: " + label)
    print("PASS: migration permission workflow/validator source bindings (4 mutations)")


def main() -> int:
    publisher = read(PUBLISHER)
    independent = read(INDEPENDENT)
    validate(publisher, independent)
    prove_yaml_authority_negatives(publisher, independent)
    prove_concurrency_authority_negatives(publisher)
    prove_trigger_reachability_negatives(publisher, independent)
    verify_isolation_blob_bindings()
    verify_permission_blob_bindings()
    runtime(publisher, independent)
    diagnostic_runtime(publisher)
    prove_failed_stage_runtime(publisher)
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
