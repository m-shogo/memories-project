#!/usr/bin/env python3
"""Fail-closed whole-source and runtime negatives for human promotion source-order CI."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-promotion-review-source-order.yml"
REVIEWED_WORKFLOW_BLOB_SHA = "90cee6d05601f051fb2cca3dc68b1f0aae71e939"

TRIGGER_PATHS = (
    "scripts/validate-memory-os-backup-restore-promotion-review-source-order.py",
    "scripts/register-memory-os-backup-restore-promotion-review.py",
    "scripts/register-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-promotion-review.py",
    "scripts/validate-memory-os-backup-restore-promotion-review-negative.py",
    "contracts/operations/backup-restore-promotion-review-contract.v1.json",
    "contracts/operations/backup-restore-promotion-review-registry.v1.json",
    "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    "contracts/operations/operability-admission-inventory.v1.json",
    "docs/evidence/backup-restore/**",
    ".github/workflows/backup-restore-promotion-review-source-order.yml",
    "scripts/validate-memory-os-backup-restore-promotion-review-source-order-workflow-negative.py",
)
REQUIRED = (
    ("checkout SHA", "      - uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n", 1),
    ("setup SHA", "      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n", 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("checkout ref", "          ref: ${{ github.event.pull_request.head.sha || github.sha }}\n", 1),
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
    ("self-trigger", "      - 'scripts/validate-memory-os-backup-restore-promotion-review-source-order-workflow-negative.py'\n", 2),
    ("self-execution", "        run: python scripts/validate-memory-os-backup-restore-promotion-review-source-order-workflow-negative.py\n", 1),
    ("read-only token", "permissions:\n  contents: read\n", 1),
    ("unreviewed event", "          else\n            echo \"Unreviewed promotion source-order CI event\" >&2\n            exit 1\n          fi\n", 1),
    ("no contents write permission", "contents: write", 0),
)


def validate_trigger_reachability(source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS) -> None:
    """Pin every reviewed source trigger separately for PR and push."""
    if len(trigger_paths) != 13 or len(set(trigger_paths)) != 13:
        raise SystemExit("promotion source-order CI trigger inventory drift")
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (push_marker, pr_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("promotion source-order CI trigger marker drift")
    push_block = source.split(push_marker, 1)[1].split(pr_marker, 1)[0]
    pr_block = source.split(pr_marker, 1)[1].split(dispatch_marker, 1)[0]
    for event, block in (("push", push_block), ("pull_request", pr_block)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        expected = tuple(f"      - '{path}'" for path in trigger_paths)
        if actual != expected:
            raise SystemExit("promotion source-order CI " + event + " trigger inventory drift")
        for path in trigger_paths:
            token = "      - '" + path + "'\n"
            if block.count(token) != 1:
                raise SystemExit("promotion source-order CI " + event + " trigger drift: " + path)


def prove_trigger_reachability_negatives(source: str) -> None:
    """Remove each event's path independently and prove semantic rejection."""
    pr_marker = "  pull_request:\n    branches: [so]\n    paths:\n"

    def expect_trigger_rejected(mutated: str, expected: str, case: str) -> None:
        try:
            validate_trigger_reachability(mutated)
        except SystemExit as exc:
            if str(exc) != expected:
                raise SystemExit(
                    "promotion source-order CI wrong trigger diagnostic: "
                    + case + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("promotion source-order CI accepted " + case)

    for event in ("push", "pull_request"):
        for path in TRIGGER_PATHS:
            token = "      - '" + path + "'\n"
            if source.count(token) != 2:
                raise SystemExit("promotion source-order CI trigger negative anchor drift: " + path)
            if event == "push":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(pr_marker, 1)
                mutated = prefix + pr_marker + suffix.replace(token, "", 1)
            expect_trigger_rejected(
                mutated, "promotion source-order CI " + event + " trigger inventory drift",
                event + " missing " + path,
            )
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit as exc:
        if str(exc) != "promotion source-order CI trigger inventory drift":
            raise SystemExit(
                "promotion source-order CI wrong shortened-inventory diagnostic: "
                + str(exc)
            ) from exc
    else:
        raise SystemExit("promotion source-order CI shortened trigger inventory accepted")
    print(f"PASS: promotion source-order CI PR/push trigger reachability ({len(TRIGGER_PATHS) * 2} semantic removal negatives; 1 shortened inventory negative)")
    for event in ("push", "pull_request"):
        for label, inserted in (
            ("single-quoted extra", "      - 'unreviewed/**'\n"),
            ("single-quoted duplicate", f"      - '{TRIGGER_PATHS[0]}'\n"),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", f"      - {TRIGGER_PATHS[0]}\n"),
        ):
            token = f"      - '{TRIGGER_PATHS[0]}'\n"
            prefix, suffix = source.split(pr_marker, 1)
            if event == "push":
                mutated = prefix.replace(token, inserted + token, 1) + pr_marker + suffix
            else:
                mutated = prefix + pr_marker + suffix.replace(token, inserted + token, 1)
            if mutated == source:
                raise SystemExit(f"promotion source-order CI addition fixture missing: {event} {label}")
            expect_trigger_rejected(
                mutated, "promotion source-order CI " + event + " trigger inventory drift",
                event + " addition " + label,
            )
    print("PASS: promotion source-order CI trigger additions (8 event-specific semantic negatives)")




def validate_yaml_authority(source: str) -> None:
    """Pin human promotion source-order CI event/root/permission YAML authority."""
    name = "name: Backup Restore Promotion Review Source Order"
    push = "  push:\n    branches: [so]\n    paths:\n"
    pr = "  pull_request:\n    branches: [so]\n    paths:\n"
    paths = "".join("      - '" + item + "'\n" for item in TRIGGER_PATHS)
    header = name + "\n\non:\n" + push + paths + pr + paths + "  workflow_dispatch:\n"
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != header):
        raise SystemExit("promotion source-order CI exact event header drift")
    roots = [
        line for line in source.splitlines()
        if line.strip() and not line[0].isspace()
        and not line.lstrip().startswith("#")
    ]
    if roots != [name, "on:", "permissions:", "jobs:"]:
        raise SystemExit("promotion source-order CI root YAML key shadow drift")
    leaves = []
    for line in source.split("\npermissions:\n", 1)[1].splitlines():
        if line.strip() and not line[0].isspace():
            break
        if line.strip() and not line.lstrip().startswith("#"):
            leaves.append(line)
    if leaves != ["  contents: read"]:
        raise SystemExit("promotion source-order CI permission leaf shadow drift")


def prove_yaml_authority_negatives(source: str) -> None:
    """Require nine exact-diagnostic YAML shadow rejections independently of blob."""
    validate_yaml_authority(source)
    event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if event == source:
        raise SystemExit("promotion source-order CI YAML event fixture anchor drift")
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
        raise SystemExit("promotion source-order CI YAML permission fixture anchor drift")
    for label, leaf in (
        ("spaced contents", "  contents : write\n"),
        ("quoted contents", "  'contents': write\n"),
    ):
        cases.append((label, source.replace(marker, marker + leaf, 1),
                      "permission leaf shadow drift"))
    if len(cases) != 9:
        raise SystemExit("promotion source-order CI YAML negative inventory drift")
    for label, mutated, diagnostic in cases:
        if mutated == source:
            raise SystemExit("promotion source-order CI unchanged YAML fixture: " + label)
        try:
            validate_yaml_authority(mutated)
        except SystemExit as exc:
            expected = "promotion source-order CI " + diagnostic
            if str(exc) != expected:
                raise SystemExit("promotion source-order CI wrong YAML diagnostic: "
                                 + label + ": " + str(exc)) from exc
        else:
            raise SystemExit("promotion source-order CI accepted YAML mutation: " + label)
    print("PASS: promotion source-order CI YAML event/root/permission authority (9 exact-diagnostic negatives)")


def validate(source: str, *, check_blob: bool = True) -> None:
    validate_yaml_authority(source)
    validate_trigger_reachability(source)
    for label, token, count in REQUIRED:
        if source.count(token) != count:
            raise SystemExit("promotion source-order CI source drift: " + label)
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if check_blob and hashlib.sha1(blob).hexdigest() != REVIEWED_WORKFLOW_BLOB_SHA:
        raise SystemExit("promotion source-order CI complete source drift")


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
            raise SystemExit("promotion source-order CI runtime branch drift: " + label)
    print("PASS: promotion source-order CI PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_yaml_authority_negatives(source)
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
        ("injected executable action", "      - name: Compile chronology and promotion validators\n", "      - uses: unreviewed/action@v1\n      - name: Compile chronology and promotion validators\n"),
        ("removed PR self-trigger", "      - 'scripts/validate-memory-os-backup-restore-promotion-review-source-order-workflow-negative.py'\n", ""),
        ("job permission escalation", "jobs:\n  validate:\n", "jobs:\n  validate:\n    permissions:\n      contents: write\n"),
    )
    if len(cases) != 22:
        raise SystemExit("promotion source-order CI mutation inventory drift")
    digest_only = frozenset({"injected shell command", "injected executable action"})
    semantic_count = 0
    blob_only_count = 0
    special_diagnostics = {
        "PR target": "promotion source-order CI exact event header drift",
        "self-trigger": "promotion source-order CI exact event header drift",
        "removed PR self-trigger": "promotion source-order CI exact event header drift",
        "read-only token": "promotion source-order CI permission leaf shadow drift",
        "job permission escalation": "promotion source-order CI source drift: no contents write permission",
        "injected shell command": "promotion source-order CI complete source drift",
        "injected executable action": "promotion source-order CI complete source drift",
    }
    for label, old, replacement in cases:
        if old not in source:
            raise SystemExit("promotion source-order CI negative anchor missing: " + label)
        if label == "removed PR self-trigger":
            marker = "  pull_request:\n    branches: [so]\n    paths:\n"
            if source.count(marker) != 1:
                raise SystemExit("promotion source-order CI PR event mutation marker drift")
            prefix, suffix = source.split(marker, 1)
            if suffix.count(old) != 1:
                raise SystemExit("promotion source-order CI PR self-trigger fixture drift")
            mutated = prefix + marker + suffix.replace(old, replacement, 1)
        else:
            mutated = source.replace(old, replacement, 1)
        if mutated == source:
            raise SystemExit("promotion source-order CI mutation unchanged: " + label)
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in REQUIRED)
        if semantic == (label in digest_only):
            raise SystemExit("promotion source-order CI mutation classification drift: " + label)
        semantic_count += int(semantic)
        blob_only_count += int(not semantic)
        expected = special_diagnostics.get(label, "promotion source-order CI source drift: " + label)
        try:
            validate(mutated, check_blob=not semantic)
        except SystemExit as exc:
            if str(exc) != expected:
                raise SystemExit(
                    "promotion source-order CI wrong source diagnostic: "
                    + label + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("promotion source-order CI accepted forbidden mutation: " + label)
    if (semantic_count, blob_only_count) != (20, 2):
        raise SystemExit("promotion source-order CI semantic/blob mutation coverage drift")
    print(f"PASS: promotion source-order CI source admission ({semantic_count} semantic; {blob_only_count} blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
