#!/usr/bin/env python3
"""Fail-closed source and event/ref negatives for strict preflight eligibility consistency."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-preflight-generation-eligibility-consistency.yml"
REVIEWED_WORKFLOW_GIT_BLOB_SHA = "4eb6040b3c5ba7508a716605aeea2dc9e05c49c1"

TRIGGER_PATHS = (
    ".github/workflows/backup-restore-preflight-generation-eligibility-consistency.yml",
    "scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency-workflow-negative.py",
    "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
    "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "contracts/operations/recovery-objectives-admission-contract.v1.json",
    "contracts/operations/recovery-objectives-registry.v1.json",
    "contracts/operations/backup-restore-drill-request-contract.v1.json",
    "contracts/operations/backup-restore-drill-request-registry.v1.json",
    "docs/evidence/backup-restore/**",
    "docs/evidence/recovery-objectives/approvals/**",
    "scripts/memory_os_environment_generation_eligibility.py",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-eligibility.py",
    "scripts/register-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency.py",
    "scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency-negative.py",
    "scripts/request-memory-os-backup-restore-drill.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
)
REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("self trigger", '      - "scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency-workflow-negative.py"\n', 2),
    ("checkout SHA", "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262", 2),
    ("setup SHA", "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("publisher credentials", "          persist-credentials: true\n", 1),
    ("PR base", '          test "${GITHUB_BASE_REF:-}" = "so"\n', 1),
    ("SHA format", '          [[ "$expected" =~ ^[0-9a-f]{40}$ ]]\n', 2),
    ("publisher branch", '          test "${GITHUB_REF:-}" = "refs/heads/so"\n', 1),
    ("publisher event", '          [[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]\n', 1),
    ("publisher scope", "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
    ("self execution", "\n          python scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency-workflow-negative.py\n", 2),
    ("writer SHA", '          expected="${GITHUB_SHA:-}"\n', 1),
    ("PR SHA", '          expected="${{ github.event.pull_request.head.sha }}"\n', 1),
    ("HEAD check", '          test "$(git rev-parse HEAD)" = "$expected"\n', 2),
    ("write scope", "      contents: write\n", 1),
    ("stale-source CAS", '\n          if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then\n', 2),
    ("nested stale-source CAS", '\n            if [[ "$(git rev-parse origin/so)" != "$SOURCE_SHA" ]]; then\n', 2),
)



def validate_trigger_reachability(
    source: str, *, trigger_paths: tuple[str, ...] = TRIGGER_PATHS
) -> None:
    """Pin every reviewed consistency CI path separately under PR and push."""
    if len(trigger_paths) != 23 or len(set(trigger_paths)) != 23:
        raise SystemExit("preflight eligibility consistency CI trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit("preflight eligibility consistency CI trigger marker drift")
    pr = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    for event, block in (("pull_request", pr), ("push", push)):
        approved = tuple('      - "' + item + '"' for item in trigger_paths)
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if actual != approved:
            raise SystemExit("preflight eligibility consistency CI " + event + " exact trigger inventory drift")
    # Strict preflight requires an exclusive reviewed event header and
    # effective read-only YAML root/permission authority, not only paths.
    expected_header = (
        "name: Backup Restore Preflight Generation Eligibility Consistency\n\non:\n"
        + pr_marker + "".join('      - "' + item + '"\n' for item in trigger_paths)
        + push_marker + "".join('      - "' + item + '"\n' for item in trigger_paths)
        + dispatch_marker
    )
    if (source.count("\npermissions:\n") != 1
            or source.split("\npermissions:\n", 1)[0] != expected_header):
        raise SystemExit("preflight eligibility consistency CI exact event header drift")
    observed_roots = [
        row for row in source.splitlines()
        if row.strip() and not row[0].isspace()
        and not row.lstrip().startswith("#")
    ]
    if observed_roots != [
        "name: Backup Restore Preflight Generation Eligibility Consistency",
        "on:", "permissions:", "concurrency:", "jobs:",
    ]:
        raise SystemExit("preflight eligibility consistency CI root YAML key shadow drift")
    permission_lines = source.split("\npermissions:\n", 1)[1].splitlines()
    permission_rows = []
    for row in permission_lines:
        if row.strip() and not row[0].isspace():
            break
        if row.strip() and not row.lstrip().startswith("#"):
            permission_rows.append(row)
    if permission_rows != ["  contents: read"]:
        raise SystemExit("preflight eligibility consistency CI permission leaf shadow drift")
    # Strict eligibility CI must not permit a shadow job or an extra writer.
    if source.count("\njobs:\n") != 1:
        raise SystemExit("preflight eligibility consistency CI job mapping shadow drift")
    body = source.split("\njobs:\n", 1)[1]
    jobs = (("  validate-pr:", "read"), ("  validate-and-publish:", "write"))
    headers = [line for line in body.splitlines()
               if line.startswith("  ") and not line.startswith("   ")
               and line.strip() and not line.lstrip().startswith("#")]
    if headers != [job for job, _ in jobs]:
        raise SystemExit("preflight eligibility consistency CI job mapping shadow drift")
    for index, (job, access) in enumerate(jobs):
        block = body.split(job + "\n", 1)[1]
        if index + 1 < len(jobs):
            block = block.split(jobs[index + 1][0] + "\n", 1)[0]
        if block.count("    permissions:\n") != 1 or block.count("    runs-on:") != 1:
            raise SystemExit("preflight eligibility consistency CI job permission leaf shadow drift")
        section = block.split("    permissions:\n", 1)[1].split("    runs-on:", 1)[0]
        leaves = [line for line in section.splitlines()
                  if line.strip() and not line.lstrip().startswith("#")]
        if leaves != ["      contents: " + access]:
            raise SystemExit("preflight eligibility consistency CI job permission leaf shadow drift")


def prove_trigger_reachability_negatives(source: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for event in ("pull_request", "push"):
        for item in TRIGGER_PATHS:
            token = '      - "' + item + '"' + chr(10)
            if source.count(token) != 2:
                raise SystemExit("preflight eligibility consistency CI trigger mutation anchor drift: " + item)
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("preflight eligibility consistency CI accepted missing " + event + " trigger: " + item)
    for event in ("pull_request", "push"):
        marker = "  pull_request:\n    branches:\n      - so\n    paths:\n" if event == "pull_request" else push_marker
        for label, injected in (
            ("quoted extra", '      - "unreviewed/**"\n'),
            ("quoted duplicate", '      - "' + TRIGGER_PATHS[0] + '"\n'),
            ("unquoted extra", "      - unreviewed/**\n"),
            ("unquoted duplicate", "      - " + TRIGGER_PATHS[0] + "\n"),
        ):
            if source.count(marker) != 1:
                raise SystemExit("preflight eligibility consistency CI addition marker drift: " + event)
            mutated = source.replace(marker, marker + injected, 1)
            if mutated == source:
                raise SystemExit("preflight eligibility consistency CI addition fixture unchanged")
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit("preflight eligibility consistency CI accepted " + event + " addition: " + label)
    try:
        validate_trigger_reachability(source, trigger_paths=TRIGGER_PATHS[:-1])
    except SystemExit:
        pass
    else:
        raise SystemExit("preflight eligibility consistency CI shortened trigger inventory accepted")
    # The reviewed workflow has no trailing newline. Prefix an explicit
    # newline so root shadows are valid separate YAML mapping keys.
    extra_event = source.replace("on:\n", "on:\n  issues:\n", 1)
    if extra_event == source:
        raise SystemExit("preflight eligibility extra-event negative anchor drift")
    try:
        validate_trigger_reachability(extra_event)
    except SystemExit as exc:
        if str(exc) != "preflight eligibility consistency CI exact event header drift":
            raise SystemExit(
                "preflight eligibility event rejected for wrong reason: " + str(exc)
            ) from exc
    else:
        raise SystemExit("preflight eligibility accepted extra event")
    for name, suffix in (
        ("spaced on", "on :\n  issues:\n"),
        ("quoted on", "'on':\n  issues:\n"),
        ("spaced permissions", "permissions :\n  contents: write\n"),
        ("spaced jobs", "jobs : {}\n"),
    ):
        try:
            validate_trigger_reachability(source + "\n" + suffix)
        except SystemExit as exc:
            if str(exc) != "preflight eligibility consistency CI root YAML key shadow drift":
                raise SystemExit(
                    "preflight eligibility root shadow rejected for wrong reason: "
                    + name + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("preflight eligibility accepted root shadow: " + name)
    anchor = "permissions:\n  contents: read\n"
    if source.count(anchor) != 1:
        raise SystemExit("preflight eligibility permission negative anchor drift")
    for name, extra in (
        ("spaced", "  contents : write\n"),
        ("quoted", "  'contents': write\n"),
    ):
        mutated = source.replace(anchor, anchor + extra, 1)
        try:
            validate_trigger_reachability(mutated)
        except SystemExit as exc:
            if str(exc) != "preflight eligibility consistency CI permission leaf shadow drift":
                raise SystemExit(
                    "preflight eligibility permission shadow rejected for wrong reason: "
                    + name + ": " + str(exc)
                ) from exc
        else:
            raise SystemExit("preflight eligibility accepted permission shadow: " + name)
    job_count = 0
    for job, access in (("validate-pr", "read"), ("validate-and-publish", "write")):
        cases = []
        for label, key in (("spaced job", job + " "), ("quoted job", "'" + job + "'")):
            cases.append((label, source + "\n  " + key + ": {}\n",
                          "job mapping shadow drift"))
        marker = "    permissions:\n      contents: " + access + "\n"
        if source.count(marker) != 1:
            raise SystemExit("preflight eligibility consistency CI job fixture anchor drift: " + job)
        for label, leaf in (("spaced", "      contents : write\n"),
                            ("quoted", "      'contents': write\n")):
            cases.append((label, source.replace(marker, marker + leaf, 1),
                          "job permission leaf shadow drift"))
        for label, mutated, diagnostic in cases:
            try:
                validate_trigger_reachability(mutated)
            except SystemExit as exc:
                expected = "preflight eligibility consistency CI " + diagnostic
                if str(exc) != expected:
                    raise SystemExit("preflight eligibility job rejected for wrong reason: "
                                     + job + " " + label + ": " + str(exc)) from exc
            else:
                raise SystemExit("preflight eligibility accepted job shadow: " + job + " " + label)
            job_count += 1
    if job_count != 8:
        raise SystemExit("preflight eligibility consistency CI job negative population drift")
    print("PASS: preflight eligibility consistency CI semantic YAML negatives "
          "(1 extra-event, 4 root, 2 permission, 8 job exact-diagnostic cases)")
    print("PASS: preflight eligibility consistency CI event-specific triggers (46 removals; 8 additions; 1 shortened inventory negative)")



def validate(source: str, *, check_blob: bool = True) -> None:
    validate_trigger_reachability(source)
    for label, token, expected in REQUIRED:
        if source.count(token) != expected:
            raise SystemExit("preflight eligibility consistency CI source drift: " + label)
    payload = source.encode("utf-8")
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    if check_blob and hashlib.sha1(git_blob).hexdigest() != REVIEWED_WORKFLOW_GIT_BLOB_SHA:
        raise SystemExit("preflight eligibility consistency CI complete workflow source drift")


def prove_branch_guards_runtime() -> None:
    pr = REQUIRED[6][1].strip()
    push = REQUIRED[8][1].strip()
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
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        if (result.returncode == 0) != expected:
            raise SystemExit("preflight eligibility consistency CI runtime branch guard drift: " + label)
    print("PASS: preflight eligibility consistency CI PR/push branch guard runtime (6 cases)")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    prove_trigger_reachability_negatives(source)
    prove_branch_guards_runtime()
    cases = (
        ("PR target", REQUIRED[0][1], "  pull_request:\n    paths:\n"),
        ("self trigger", REQUIRED[1][1], ""),
        ("checkout floating", REQUIRED[2][1], "uses: actions/checkout@v4"),
        ("setup floating", REQUIRED[3][1], "uses: actions/setup-python@v5"),
        ("PR credentials", REQUIRED[4][1], "          persist-credentials: true\n"),
        ("writer credentials", REQUIRED[5][1], ""),
        ("PR base", REQUIRED[6][1], ""),
        ("SHA format", REQUIRED[7][1], '          test -n "$expected"\n'),
        ("publisher branch", REQUIRED[8][1], ""),
        ("publisher event", REQUIRED[9][1], ""),
        ("publisher scope", REQUIRED[10][1], "    if: github.event_name != 'pull_request'\n"),
        ("self execution", REQUIRED[11][1], ""),
        ("writer SHA", REQUIRED[12][1], '          expected="${{ github.sha }}"\n'),
        ("PR SHA", REQUIRED[13][1], '          expected="${GITHUB_SHA:-}"\n'),
        ("HEAD check", REQUIRED[14][1], ""),
        ("write scope", REQUIRED[15][1], "      contents: read\n"),
        ("stale-source CAS", REQUIRED[16][1], ""),
        ("nested stale-source CAS", REQUIRED[17][1], ""),
        ("inserted Action", "      - name: Capture exact consistency authority source\n", "      - uses: unreviewed/action@v1\n      - name: Capture exact consistency authority source\n"),
        ("inserted shell", "      - name: Capture exact consistency authority source\n", "      - run: echo unreviewed\n      - name: Capture exact consistency authority source\n"),
    )
    semantic_count = 0
    blob_only_count = 0
    for label, old, new in cases:
        if old not in source:
            raise SystemExit("preflight eligibility consistency CI negative fixture missing: " + label)
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("preflight eligibility consistency CI negative fixture unchanged: " + label)
        semantic = any(mutated.count(token) != source.count(token)
                       for _, token, _ in REQUIRED)
        semantic_count += int(semantic)
        blob_only_count += int(not semantic)
        try:
            validate(mutated, check_blob=not semantic)
        except SystemExit:
            continue
        raise SystemExit("preflight eligibility consistency CI accepted unreviewed mutation: " + label)
    if (semantic_count, blob_only_count) != (len(cases) - 2, 2):
        raise SystemExit("preflight eligibility consistency semantic/blob mutation coverage drift")
    print(f"PASS: preflight eligibility consistency CI workflow source admission ({semantic_count} semantic; {blob_only_count} blob-only negatives)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
