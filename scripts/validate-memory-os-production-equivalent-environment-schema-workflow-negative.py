#!/usr/bin/env python3
"""Independent complete-source and event/ref negative guard for environment schema CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/production-equivalent-environment-schema.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "ce0ee25b25a6811a01615e4f782bb184048f1428"

TRIGGER_PATHS = (
    ".github/workflows/production-equivalent-environment-schema.yml",
    "scripts/validate-memory-os-production-equivalent-environment-schema-workflow-negative.py",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "scripts/validate-memory-os-production-equivalent-environment-schema.py",
    "scripts/validate-memory-os-production-equivalent-environment-fixtures.py",
    "docs/fixtures/memory-os-operability/production-equivalent-environment-record.*.v1.json",
)
REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("self trigger", '      - "scripts/validate-memory-os-production-equivalent-environment-schema-workflow-negative.py"\n', 2),
    ("checkout pin", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", 2),
    ("setup pin", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", 1),
    ("read-only credentials", "          persist-credentials: false\n", 1),
    ("publisher credentials", "          persist-credentials: true\n", 1),
    ("PR base", '            test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("branch", '          test "${GITHUB_REF:-}" = "refs/heads/so"\n', 2),
    ("PR head", '            EXPECTED_SHA="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("event whitelist", '          elif [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n', 1),
    ("SHA format", '          [[ "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]]\n', 1),
    ("source HEAD", '          test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"\n', 1),
    ("self execution", "          python scripts/validate-memory-os-production-equivalent-environment-schema-workflow-negative.py\n", 1),
    ("publisher scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
    ("publisher SHA", '          [[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]\n', 1),
    ("publisher HEAD", '          test "$(git rev-parse HEAD)" = "$GITHUB_SHA"\n', 1),
    ("publisher job token", "      contents: write\n", 1),
)



def validate_trigger_reachability(
    source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS
) -> None:
    """Pin the exact reviewed schema CI PR/push trigger inventory without digest."""
    if len(trigger_paths) != 6 or len(set(trigger_paths)) != 6:
        raise SystemExit("environment schema CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("environment schema CI event marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    approved = tuple('      - "' + path + '"' for path in trigger_paths)
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if actual != approved:
            raise SystemExit("environment schema CI " + event + " exact trigger inventory drift")


def validate_yaml_authority(source: str) -> None:
    """Pin effective reviewed event, root and permission YAML mapping independently of digest."""
    expected_header = (
        "name: Production Equivalent Environment Schema\n\non:\n"
        + "  pull_request:\n    branches:\n      - so\n    paths:\n"
        + "".join('      - "' + path + '"\n' for path in TRIGGER_PATHS)
        + "  push:\n    branches:\n      - so\n    paths:\n"
        + "".join('      - "' + path + '"\n' for path in TRIGGER_PATHS)
        + "  workflow_dispatch:\n"
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("environment schema CI exact event header drift")
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [
        "name: Production Equivalent Environment Schema",
        "on:", "permissions:", "jobs:",
    ]:
        raise SystemExit("environment schema CI root YAML key shadow drift")
    permission_rows = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            permission_rows.append(line)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("environment schema CI permission leaf shadow drift")


def prove_yaml_authority_negatives(source: str) -> None:
    """Require exact semantic rejection for extra event, root and permission shadows."""
    validate_yaml_authority(source)
    event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if event == source:
        raise SystemExit("environment schema CI event fixture anchor drift")
    cases = [("extra event", event, "exact event header drift")]
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
        raise SystemExit("environment schema CI permission fixture anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(marker, marker + leaf, 1),
                      "permission leaf shadow drift"))
    if len(cases) != 9:
        raise SystemExit("environment schema CI YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("environment schema CI unchanged YAML negative: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "environment schema CI " + diagnostic
            if str(exc) != expected:
                raise SystemExit("environment schema CI wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("environment schema CI accepted YAML mutation: " + label)
    print("PASS: environment schema CI YAML event/root/permission authority (9 exact-diagnostic negatives)")


def prove_trigger_reachability_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for path in TRIGGER_PATHS:
            token = '      - "' + path + '"\n'
            if source.count(token) != 2:
                raise SystemExit("environment schema CI mutation anchor drift: " + path)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("environment schema CI accepted missing " + event + " trigger: " + path)
        marker = pr_marker if event == "pull_request" else push_marker
        for label, injected in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", '      - "' + TRIGGER_PATHS[0] + '"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", "      - " + TRIGGER_PATHS[0] + "\n"),
        ):
            if source.count(marker) != 1:
                raise SystemExit("environment schema CI addition marker drift: " + event)
            mutated = source.replace(marker, marker + injected, 1)
            if mutated == source:
                raise SystemExit("environment schema CI addition fixture unchanged")
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("environment schema CI accepted " + event + " addition: " + label)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("environment schema CI shortened trigger inventory accepted")
    print("PASS: environment schema CI event-specific triggers (12 removals; 8 additions; 1 shortened inventory negative)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    validate_yaml_authority(source)
    for label, token, count in REQUIRED:
        if source.count(token) != count:
            raise SystemExit("environment schema workflow source drift: " + label)
    if check_blob:
        payload = source.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
            raise SystemExit("environment schema complete workflow source drift")


def prove_runtime_branch_guards() -> None:
    pr = REQUIRED[6][1].strip()
    push = REQUIRED[7][1].strip()
    cases = (
        ("PR so", pr, "GITHUB_BASE_REF", "so", True),
        ("PR main", pr, "GITHUB_BASE_REF", "main", False),
        ("PR missing", pr, "GITHUB_BASE_REF", "", False),
        ("push so", push, "GITHUB_REF", "refs/heads/so", True),
        ("push main", push, "GITHUB_REF", "refs/heads/main", False),
        ("push tag", push, "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        completed = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (completed.returncode == 0) != expected:
            raise SystemExit("environment schema runtime branch guard drift: " + label)
    print("PASS: environment schema PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_yaml_authority_negatives(source)
    prove_runtime_branch_guards()
    cases = (
        ("PR target", REQUIRED[0][1], "  pull_request:\n    paths:\n"),
        ("self trigger", REQUIRED[1][1], ""),
        ("checkout floating", REQUIRED[2][1], "uses: actions/checkout@v4"),
        ("setup floating", REQUIRED[3][1], "uses: actions/setup-python@v5"),
        ("persist PR credentials", REQUIRED[4][1], "          persist-credentials: true\n"),
        ("remove publisher credentials", REQUIRED[5][1], ""),
        ("PR base", REQUIRED[6][1], ""),
        ("branch", REQUIRED[7][1], ""),
        ("PR head", REQUIRED[8][1], '            EXPECTED_SHA="${GITHUB_SHA:-}"\n'),
        ("event whitelist", REQUIRED[9][1], ""),
        ("SHA format", REQUIRED[10][1], '          test -n "$EXPECTED_SHA"\n'),
        ("source HEAD", REQUIRED[11][1], ""),
        ("self execution", REQUIRED[12][1], ""),
        ("publisher broad", REQUIRED[13][1], "    if: github.event_name != 'pull_request'\n"),
        ("publisher SHA", REQUIRED[14][1], ""),
        ("publisher HEAD", REQUIRED[15][1], ""),
        ("publisher write scope", REQUIRED[16][1], "      contents: read\n"),
        ("injected shell step", "      - name: Install pinned JSON Schema validator\n", "      - run: echo unreviewed\n      - name: Install pinned JSON Schema validator\n"),
        ("injected Action step", "      - name: Install pinned JSON Schema validator\n", "      - uses: unreviewed/action@v1\n      - name: Install pinned JSON Schema validator\n"),
    )
    blob_only = {"injected shell step", "injected Action step"}
    if len(cases) != 19 or sum(label in blob_only for label, _, _ in cases) != 2:
        raise SystemExit("environment schema workflow negative inventory drift")
    for label, old, new in cases:
        if old not in source:
            raise SystemExit("environment schema negative fixture missing: " + label)
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("environment schema negative fixture unchanged: " + label)
        try:
            validate(mutated, check_blob=label in blob_only)
        except SystemExit:
            continue
        raise SystemExit("environment schema accepted unreviewed source mutation: " + label)
    print(f"PASS: environment schema workflow source admission ({len(cases) - 2} semantic anchor + 2 blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
