#!/usr/bin/env python3
"""Fail-closed whole-source and runtime negatives for environment eligibility negative CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-equivalent-environment-eligibility-negative.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "c234f7d09d97195980d6cf9406dba22808f9f0ab"
TRIGGER_PATHS = (
    ".github/workflows/production-equivalent-environment-eligibility-negative.yml",
    "scripts/memory_os_environment_generation_eligibility.py",
    "scripts/validate-memory-os-environment-generation-eligibility-negative.py",
    "scripts/validate-memory-os-environment-generation-eligibility-workflow-negative.py",
)
PR_MARKER = "  pull_request:\n    branches: [so]\n    paths:\n"
PUSH_MARKER = "  push:\n    branches:\n      - so\n    paths:\n"
DISPATCH_MARKER = "  workflow_dispatch:\n"
REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("checkout ref", "          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
    ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", 1),
    ("PR base environment", "          PR_BASE_REF: ${{ github.base_ref }}\n", 1),
    ("PR base assertion", "            test \"${PR_BASE_REF:-}\" = \"so\"\n", 1),
    ("PR event", "          if [[ \"${GITHUB_EVENT_NAME:-}\" == \"pull_request\" ]]; then\n", 1),
    ("PR head", "            expected=\"${{ github.event.pull_request.head.sha }}\"\n", 1),
    ("push/dispatch event", "          elif [[ \"${GITHUB_EVENT_NAME:-}\" == \"push\" || \"${GITHUB_EVENT_NAME:-}\" == \"workflow_dispatch\" ]]; then\n", 1),
    ("push/dispatch branch", "            test \"${GITHUB_REF:-}\" = \"refs/heads/so\"\n", 1),
    ("SHA format", "          [[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]\n", 1),
    ("HEAD identity", "          test \"$(git rev-parse HEAD)\" = \"$expected\"\n", 1),
    ("clean source", "          test -z \"$(git status --porcelain)\"\n", 2),
    ("self-trigger", "      - \"scripts/validate-memory-os-environment-generation-eligibility-workflow-negative.py\"\n", 2),
    ("self-execution", "        run: python scripts/validate-memory-os-environment-generation-eligibility-workflow-negative.py\n", 1),
    ("read-only token", "permissions:\n  contents: read\n", 1),
    ("unreviewed event", "          else\n            echo \"Unreviewed environment eligibility negative CI event\" >&2\n            exit 1\n          fi\n", 1),
)


def validate_trigger_reachability(
    source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS
) -> None:
    """Admit only the exact reviewed, ordered PR and push path inventories."""
    if any(source.count(marker) != 1 for marker in (PR_MARKER, PUSH_MARKER, DISPATCH_MARKER)):
        raise SystemExit("environment eligibility negative CI event marker drift")
    if not (source.index(PR_MARKER) < source.index(PUSH_MARKER) < source.index(DISPATCH_MARKER)):
        raise SystemExit("environment eligibility negative CI event order drift")
    pr = source.split(PR_MARKER, 1)[1].split(PUSH_MARKER, 1)[0]
    push = source.split(PUSH_MARKER, 1)[1].split(DISPATCH_MARKER, 1)[0]
    expected = tuple(f'      - "{path}"' for path in trigger_paths)
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if actual != expected:
            raise SystemExit(f"environment eligibility negative CI {event} trigger inventory drift")
    # Exact PR/push path blocks alone do not exclude an extra event or
    # later effective YAML root/permission shadow after the reviewed header.
    expected_header = (
        "name: Production Equivalent Environment Eligibility Negative\n\non:\n"
        + PR_MARKER + "".join(f'      - "{path}"\n' for path in trigger_paths)
        + PUSH_MARKER + "".join(f'      - "{path}"\n' for path in trigger_paths)
        + DISPATCH_MARKER
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("environment eligibility negative CI exact event header drift")
    observed_roots = [
        row for row in source.splitlines()
        if row.strip() and not row[0].isspace()
        and not row.lstrip().startswith("#")
    ]
    if observed_roots != [
        "name: Production Equivalent Environment Eligibility Negative",
        "on:", "permissions:", "concurrency:", "jobs:",
    ]:
        raise SystemExit("environment eligibility negative CI root YAML key shadow drift")
    permission_lines = source.split("\npermissions:\n", 1)[1].splitlines()
    permission_rows = []
    for row in permission_lines:
        if row.strip() and not row[0].isspace():
            break
        if row.strip() and not row.lstrip().startswith("#"):
            permission_rows.append(row)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("environment eligibility negative CI permission leaf shadow drift")


def validate(
    source: str, *, check_blob: bool = True,
    trigger_paths: tuple[str, ...] = TRIGGER_PATHS,
) -> None:
    validate_trigger_reachability(source, trigger_paths=trigger_paths)
    for label, token, count in REQUIRED:
        if source.count(token) != count:
            raise SystemExit("environment eligibility negative CI source drift: " + label)
    if check_blob:
        payload = source.encode("utf-8")
        blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
            raise SystemExit("environment eligibility negative CI complete source drift")


def prove_trigger_reachability_negatives(source: str) -> None:
    """Prove event-specific removals, additions and inventory shortening without a blob check."""
    anchor = f'      - "{TRIGGER_PATHS[0]}"\n'
    for event in ("pull_request", "push"):
        prefix, suffix = source.split(PUSH_MARKER, 1)
        for path in TRIGGER_PATHS:
            token = f'      - "{path}"\n'
            mutated = (
                prefix.replace(token, "", 1) + PUSH_MARKER + suffix
                if event == "pull_request"
                else prefix + PUSH_MARKER + suffix.replace(token, "", 1)
            )
            if mutated == source:
                raise SystemExit(f"environment eligibility negative CI removal fixture missing: {event} {path}")
            try:
                validate(mutated, check_blob=False)
            except SystemExit:
                pass
            else:
                raise SystemExit(f"environment eligibility negative CI accepted {event} trigger removal: {path}")
        for label, injected in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", anchor),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", f"      - {TRIGGER_PATHS[0]}\n"),
        ):
            mutated = (
                prefix.replace(anchor, injected + anchor, 1) + PUSH_MARKER + suffix
                if event == "pull_request"
                else prefix + PUSH_MARKER + suffix.replace(anchor, injected + anchor, 1)
            )
            if mutated == source:
                raise SystemExit(f"environment eligibility negative CI addition fixture missing: {event} {label}")
            try:
                validate(mutated, check_blob=False)
            except SystemExit:
                pass
            else:
                raise SystemExit(f"environment eligibility negative CI accepted {event} trigger addition: {label}")
    try:
        validate(source, check_blob=False, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("environment eligibility negative CI shortened trigger inventory accepted")
    # All path inventories remain unchanged in these mutations.
    extra_event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if extra_event == source:
        raise SystemExit("environment eligibility extra-event negative anchor drift")
    try:
        validate_trigger_reachability(extra_event)
    except SystemExit as exc:
        if str(exc) != "environment eligibility negative CI exact event header drift":
            raise SystemExit(
                "environment eligibility event rejected for wrong reason: " + str(exc)
            ) from exc
    else:
        raise SystemExit("environment eligibility accepted extra event")
    for name, suffix in (
        ("spaced on", "on :\n  issues:\n"),
        ("quoted on", "'on':\n  issues:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
    ):
        try:
            validate_trigger_reachability(source + suffix)
        except SystemExit as exc:
            if str(exc) != "environment eligibility negative CI root YAML key shadow drift":
                raise SystemExit(
                    "environment eligibility root shadow rejected for wrong reason: "
                    + name + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("environment eligibility accepted root shadow: " + name)
    anchor = "permissions:\n  contents: read\n"
    if source.count(anchor) != 1:
        raise SystemExit("environment eligibility permission negative anchor drift")
    for name, extra in (
        ("spaced", "  contents : write\n"),
        ("quoted", "  'contents': write\n"),
    ):
        mutated = source.replace(anchor, anchor + extra, 1)
        try:
            validate_trigger_reachability(mutated)
        except SystemExit as exc:
            if str(exc) != "environment eligibility negative CI permission leaf shadow drift":
                raise SystemExit(
                    "environment eligibility permission shadow rejected for wrong reason: "
                    + name + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("environment eligibility accepted permission leaf shadow: " + name)
    print("PASS: environment eligibility negative CI semantic YAML negatives "
          "(1 extra-event, 4 root, 2 permission exact-diagnostic cases)")
    print("PASS: environment eligibility negative CI event triggers (8 removals; 8 additions; 1 shortened inventory)")


def prove_branch_guards_runtime() -> None:
    cases = (
        ("PR so", REQUIRED[6][1].strip(), "PR_BASE_REF", "so", True),
        ("PR main", REQUIRED[6][1].strip(), "PR_BASE_REF", "main", False),
        ("PR missing", REQUIRED[6][1].strip(), "PR_BASE_REF", "", False),
        ("push so", REQUIRED[10][1].strip(), "GITHUB_REF", "refs/heads/so", True),
        ("push main", REQUIRED[10][1].strip(), "GITHUB_REF", "refs/heads/main", False),
        ("push tag", REQUIRED[10][1].strip(), "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("environment eligibility negative CI runtime branch drift: " + label)
    print("PASS: environment eligibility negative CI PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_branch_guards_runtime()
    cases = (
        ("checkout SHA", REQUIRED[0][1], "      - uses: actions/checkout@v4\n"),
        ("setup SHA", REQUIRED[1][1], "      - uses: actions/setup-python@v5\n"),
        ("no credentials", REQUIRED[2][1], ""),
        ("checkout ref", REQUIRED[3][1], "          ref: ${{ github.sha }}\n"),
        ("PR target", REQUIRED[4][1], "  pull_request:\n    branches: [main]\n    paths:\n"),
        ("PR base environment", REQUIRED[5][1], ""),
        ("PR base assertion", REQUIRED[6][1], "            test -n \"${PR_BASE_REF:-}\"\n"),
        ("PR event", REQUIRED[7][1], ""),
        ("PR head", REQUIRED[8][1], "            expected=\"${GITHUB_SHA:-}\"\n"),
        ("push/dispatch event", REQUIRED[9][1], ""),
        ("push/dispatch branch", REQUIRED[10][1], ""),
        ("SHA format", REQUIRED[11][1], "          test -n \"$expected\"\n"),
        ("HEAD identity", REQUIRED[12][1], ""),
        ("clean source", REQUIRED[13][1], ""),
        ("self-trigger", REQUIRED[14][1], ""),
        ("self-execution", REQUIRED[15][1], ""),
        ("read-only token", REQUIRED[16][1], "permissions:\n  contents: write\n"),
        ("unreviewed event", REQUIRED[17][1], ""),
        ("injected shell command", "          python -m py_compile \\\n", "          echo UNREVIEWED\n          python -m py_compile \\\n"),
        ("injected executable action", "      - name: Prove strict pair derivation\n", "      - uses: unreviewed/action@v1\n      - name: Prove strict pair derivation\n"),
        ("removed PR self-trigger", "      - \"scripts/validate-memory-os-environment-generation-eligibility-workflow-negative.py\"\n", ""),
    )
    blob_only = {"injected shell command", "injected executable action"}
    if len(cases) != 21 or sum(label in blob_only for label, _, _ in cases) != 2:
        raise SystemExit("environment eligibility negative CI source mutation inventory drift")
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit("environment eligibility negative CI negative anchor missing: " + label)
        mutated = source.replace(old, replacement, 1)
        try:
            validate(mutated, check_blob=label in blob_only)
        except SystemExit:
            continue
        raise SystemExit("environment eligibility negative CI accepted forbidden mutation: " + label)
    print(f"PASS: environment eligibility negative CI source admission ({len(cases) - 2} semantic + 2 blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
