#!/usr/bin/env python3
"""Fail closed if end-to-end backup/restore admission PR validation regains write authority."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-admission-chain.yml"
NEGATIVE_WORKFLOW = ROOT / ".github/workflows/backup-restore-admission-chain-negative.yml"
REVIEWED_NEGATIVE_WORKFLOW_BLOB_SHA = "9e49f2bb43d94d333e2753bc30ed22b7ee9715b7"
READONLY_WORKFLOW = ROOT / ".github/workflows/backup-restore-admission-chain-readonly.yml"
REVIEWED_READONLY_WORKFLOW_BLOB_SHA = "d6a35451b4b76545b20c0a8ab74e487d9e469f8d"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_publisher_event_scope(header: str) -> None:
    expected = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n    permissions:\n      contents: write\n"
    require(header.startswith(expected),
            "admission-chain publisher must scope write authority to so push/dispatch")
    keys = []
    for line in header.splitlines():
        if not line.startswith("    ") or line.startswith("     "):
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"    ([a-z][a-z-]*):(?:[ \t].*)?", line)
        require(match is not None, "publisher job key inventory drift")
        keys.append(match.group(1))
    require(tuple(keys) == ("if", "permissions", "runs-on", "timeout-minutes"),
            "publisher job key inventory drift")


REVIEWED_HEADERS = {True: ["      - name: Checkout exact PR source","      - name: Set up Python","      - name: Verify exact clean PR authority source","      - name: Validate end-to-end recovery admission chain read-only"], False: ["      - name: Checkout exact publication source","      - name: Set up Python","      - name: Capture exact chain authority source","      - name: Reconcile and validate end-to-end recovery admission chain","      - name: Commit bounded chain authority","      - name: Record privacy-safe chain diagnostic","      - name: Enforce recovery admission chain"]}
REVIEWED_PROPERTIES = {True: [["uses","with"],["uses","with"],["run"],["run"]], False: [["uses","with"],["uses","with"],["run"],["id","run"],["if","run"],["if","env","run"],["run"]]}
REVIEWED_CHECKOUT = {True: "      - name: Checkout exact PR source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n          fetch-depth: 0\n          persist-credentials: false\n\n", False: "      - name: Checkout exact publication source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n        with:\n          ref: ${{ github.sha }}\n          fetch-depth: 0\n          persist-credentials: true\n\n"}
REVIEWED_SETUP = {True: "      - name: Set up Python\n        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n\n", False: "      - name: Set up Python\n        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n\n"}


def require_reviewed_executable_steps(job: str, *, pr: bool) -> None:
    """Bind exact bootstrap and complete ordered step headers and properties."""
    require(job.count(REVIEWED_CHECKOUT[pr]) == 1,
            "admission chain checkout action/source/credential drift")
    require(job.count(REVIEWED_SETUP[pr]) == 1,
            "admission chain Python bootstrap action drift")
    blocks = re.split(r"(?m)(?=^      - (?:uses|name): )", job)
    steps = [block for block in blocks if block.startswith("      - ")]
    require([block.split("\n", 1)[0] for block in steps] == REVIEWED_HEADERS[pr],
            "admission chain executable step header drift")
    actual = []
    for block in steps:
        properties = []
        for line in re.findall(r"(?m)^        ([^ \t#\n][^\n]*)$", block):
            match = re.fullmatch(r"([a-z][a-z-]*):(?:[ \t].*)?", line)
            require(match is not None, "admission chain quoted/unreviewed step property")
            properties.append(match.group(1))
        actual.append(properties)
    require(actual == REVIEWED_PROPERTIES[pr],
            "admission chain executable step property drift")


def require_reviewed_executable_negatives(job: str, *, pr: bool) -> None:
    require_reviewed_executable_steps(job, pr=pr)
    checkout = REVIEWED_CHECKOUT[pr]
    run = "        run: |\n"
    require(run in job, "admission chain negative run anchor missing")
    mutated_checkout = checkout.replace(
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/checkout@v4", 1
    )
    mutated_source = checkout.replace("          ref: ", "          ref: HEAD^ # ", 1)
    mutated_credential = checkout.replace(
        "persist-credentials: false" if pr else "persist-credentials: true",
        "persist-credentials: true" if pr else "persist-credentials: false", 1
    )
    mutations = (
        ("action", job.replace(checkout, mutated_checkout, 1)),
        ("source", job.replace(checkout, mutated_source, 1)),
        ("credential", job.replace(checkout, mutated_credential, 1)),
        ("extra-step", job.replace(checkout, checkout + "      - name: Unreviewed shell\n        run: echo unreviewed\n", 1)),
        ("continue-on-error", job.replace(run, "        continue-on-error: true\n" + run, 1)),
        ("quoted-property", job.replace(run, '        "continue-on-error": true\n' + run, 1)),
        ("working-directory", job.replace(run, "        working-directory: /tmp\n" + run, 1)),
        ("duplicate-run", job.replace(run, "        run: echo unreviewed\n" + run, 1)),
    )
    for label, mutated in mutations:
        require(mutated != job, f"admission chain negative fixture unchanged: {label}")
        try:
            require_reviewed_executable_steps(mutated, pr=pr)
        except Fail:
            pass
        else:
            raise Fail(f"admission chain unreviewed executable mutation accepted: {label}")



REVIEWED_CONTROL_LINES = {True: [[],[],[],[]], False: [[],[],[],["        id: chain"],["        if: steps.chain.outputs.exit_code == '0' && github.ref == 'refs/heads/so'"],["        if: steps.chain.outputs.exit_code != '0' && github.ref == 'refs/heads/so'","        env:","          CHAIN_EXIT_CODE: ${{ steps.chain.outputs.exit_code }}"],[]]}


def require_reviewed_controls(job: str, *, pr: bool) -> None:
    """Bind ordered if/id/env and diagnostic env-value controls, not just keys."""
    blocks = re.split(r"(?m)(?=^      - (?:uses|name): )", job)
    steps = [block for block in blocks if block.startswith("      - ")]
    actual = []
    for block in steps:
        before_run = block.split("\n        run:", 1)[0]
        actual.append([
            line for line in before_run.splitlines()
            if re.match(r"^        (?:id|if|env):", line)
            or re.match(r"^          [A-Z][A-Z_]*:", line)
        ])
    require(actual == REVIEWED_CONTROL_LINES[pr],
            "admission step control values drift")


def require_control_negatives(job: str) -> None:
    require_reviewed_controls(job, pr=False)
    controls = [line for step in REVIEWED_CONTROL_LINES[False] for line in step]
    id_line = next(line for line in controls if line.startswith("        id:"))
    if_line = next(line for line in controls if line.startswith("        if:"))
    env_line = next(line for line in controls if line.startswith("          "))
    mutations = (
        ("id", job.replace(id_line, "        id: unreviewed", 1)),
        ("if", job.replace(if_line, "        if: true", 1)),
        ("env-value", job.replace(env_line, env_line.split(": ", 1)[0] + ": 0", 1)),
        ("env-name", job.replace(env_line, "          UNREVIEWED_EXIT_CODE: 0", 1)),
    )
    for label, mutated in mutations:
        require(mutated != job, f"admission control fixture unchanged: {label}")
        try:
            require_reviewed_controls(mutated, pr=False)
        except Fail:
            pass
        else:
            raise Fail(f"admission unreviewed control mutation accepted: {label}")



def require_root_event_inventory(source: str) -> None:
    """Reject unreviewed root mappings and YAML-equivalent event names."""
    roots = []
    for line in source.splitlines():
        if not line or line[0].isspace() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([a-z][a-z-]*):(?:[ \t].*)?", line)
        require(match is not None, "recovery workflow quoted/unreviewed root key")
        roots.append(match.group(1))
    require(roots == ["name", "on", "permissions", "concurrency", "jobs"],
            "recovery workflow root key inventory drift")
    sections = source.split("\non:\n", 1)
    require(len(sections) == 2, "recovery workflow event block missing")
    event_block = sections[1].split("\npermissions:\n", 1)
    require(len(event_block) == 2, "recovery workflow permissions boundary missing")
    events = re.findall(r"(?m)^  ([^ \t#\n][^\n]*)$", event_block[0])
    require(events == ["pull_request:", "push:", "workflow_dispatch:"],
            "recovery workflow event inventory drift")


def require_root_event_negatives(source: str) -> None:
    require_root_event_inventory(source)
    mutations = (
        ("quoted-root", source.replace("\non:\n", '\n"on":\n', 1)),
        ("duplicate-permissions", source.replace("\npermissions:\n", "\npermissions:\npermissions:\n", 1)),
        ("workflow-run", source.replace("  workflow_dispatch:\n", "  workflow_dispatch:\n  workflow_run:\n", 1)),
        ("quoted-event", source.replace("  workflow_dispatch:\n", "  workflow_dispatch:\n  'pull_request_target':\n", 1)),
        ("duplicate-push", source.replace("  push:\n", "  push:\n  push:\n", 1)),
        ("schedule", source.replace("  workflow_dispatch:\n", "  workflow_dispatch:\n  schedule:\n", 1)),
    )
    for label, mutated in mutations:
        require(mutated != source, f"recovery root/event fixture unchanged: {label}")
        try:
            require_root_event_inventory(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"recovery unreviewed root/event mutation accepted: {label}")



REVIEWED_TRIGGER_PATHS = [".github/workflows/backup-restore-admission-chain.yml","contracts/operations/backup-restore-*.json","contracts/operations/production-equivalent-environment-*.json","contracts/operations/recovery-objectives-*.json","contracts/operations/operability-admission-inventory.v1.json","contracts/operations/production-operability-status.json","docs/evidence/backup-restore/**","docs/evidence/recovery-objectives/approvals/**","docs/fixtures/memory-os-operability/backup-restore-generation-evidence/**","docs/fixtures/memory-os-operability/recovery-objectives-approval/**","scripts/memory_os_backup_restore_blockers.py","scripts/memory_os_environment_generation_eligibility.py","scripts/*backup*.py","scripts/*recovery*objective*.py","scripts/*production*equivalent*environment*.py","scripts/validate-memory-os-operability.py"]


def require_reviewed_trigger_paths(source: str) -> None:
    """Bind complete PR/push trigger paths and so-only publisher push branch."""
    sections = source.split("\non:\n", 1)
    require(len(sections) == 2, "recovery trigger source missing")
    event = sections[1].split("\npermissions:\n", 1)
    require(len(event) == 2, "recovery trigger permissions boundary missing")
    parts = event[0].split("  pull_request:\n", 1)
    require(len(parts) == 2, "recovery PR trigger missing")
    parts = parts[1].split("  push:\n", 1)
    require(len(parts) == 2, "recovery push trigger missing")
    pr_body, remainder = parts
    parts = remainder.split("  workflow_dispatch:\n", 1)
    require(len(parts) == 2, "recovery dispatch trigger missing")
    push_body = parts[0]
    pr_keys = re.findall(r"(?m)^    ([^ \t#\n][^\n]*)$", pr_body)
    push_keys = re.findall(r"(?m)^    ([^ \t#\n][^\n]*)$", push_body)
    require(pr_keys == ["paths:"] and push_keys == ["branches:", "paths:"],
            "recovery trigger filter key inventory drift")
    require(push_body.startswith("    branches:\n      - so\n    paths:\n"),
            "recovery publisher push branch drift")
    for body in (pr_body, push_body.split("    paths:\n", 1)[1]):
        paths = re.findall(r"(?m)^      - ([^\n]+)$", body)
        require(paths == [f'"{path}"' for path in REVIEWED_TRIGGER_PATHS],
                "recovery trigger path inventory drift")


def require_trigger_path_negatives(source: str) -> None:
    require_reviewed_trigger_paths(source)
    first = f'      - "{REVIEWED_TRIGGER_PATHS[0]}"\n'
    require(source.count(first) == 2, "recovery trigger fixture first path missing")
    before, after = source.split("  push:\n", 1)
    mutations = (
        ("pr-path-removed", source.replace(first, "", 1)),
        ("pr-negative-path", source.replace(first, '      - "!unreviewed/**"\n' + first, 1)),
        ("push-branch", source.replace("    branches:\n      - so\n", "    branches:\n      - main\n", 1)),
        ("duplicate-branches", source.replace("    branches:\n      - so\n", "    branches:\n      - so\n    branches:\n      - main\n", 1)),
        ("paths-ignore", source.replace("    paths:\n", "    paths-ignore:\n      - \"docs/**\"\n    paths:\n", 1)),
        ("quoted-paths", source.replace("    paths:\n", '    "paths":\n', 1)),
        ("push-path-removed", before + "  push:\n" + after.replace(first, "", 1)),
    )
    for label, mutated in mutations:
        require(mutated != source, f"recovery trigger fixture unchanged: {label}")
        try:
            require_reviewed_trigger_paths(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"recovery trigger mutation accepted: {label}")



REVIEWED_WORKFLOW_GIT_BLOB_SHA = "28a5b4f151e222883a61134ffef3b022d9e892fb"


def require_reviewed_workflow_blob(source: str) -> None:
    """Bind all workflow bytes, including executable run bodies and metadata."""
    payload = source.encode("utf-8")
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    require(hashlib.sha1(git_blob).hexdigest() == REVIEWED_WORKFLOW_GIT_BLOB_SHA,
            "recovery publisher complete workflow blob drift")


def require_run_body_negatives(source: str) -> None:
    require_reviewed_workflow_blob(source)
    anchor = "        run: |\n"
    strict = "          set -euo pipefail\n"
    require(anchor in source and strict in source,
            "recovery publisher run-body negative anchors missing")
    mutations = (
        ("injected-command", source.replace(anchor, anchor + "          echo UNREVIEWED\n", 1)),
        ("relaxed-shell", source.replace(strict, "          set +e\n", 1)),
        ("inline-run", source.replace(anchor, "        run: echo UNREVIEWED\n", 1)),
        ("pr-head-format", source.replace("[[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]", "test -n \"$expected\"", 1)),
        ("publisher-ref", source.replace("test \"${GITHUB_REF:-}\" = \"refs/heads/so\"", "true # bypass publisher ref", 1)),
        ("publisher-event", source.replace("[[ \"${GITHUB_EVENT_NAME:-}\" == \"push\" || \"${GITHUB_EVENT_NAME:-}\" == \"workflow_dispatch\" ]]", "true # bypass publisher event", 1)),
        ("publisher-sha-format", source.replace("[[ \"${GITHUB_SHA:-}\" =~ ^[0-9a-f]{40}$ ]]", "test -n \"$GITHUB_SHA\"", 1)),
    )
    for label, before, _ in (
        ("pr-head-format", "[[ \"$expected\" =~ ^[0-9a-f]{40}$ ]]", None),
        ("publisher-ref", "test \"${GITHUB_REF:-}\" = \"refs/heads/so\"", None),
        ("publisher-event", "[[ \"${GITHUB_EVENT_NAME:-}\" == \"push\" || \"${GITHUB_EVENT_NAME:-}\" == \"workflow_dispatch\" ]]", None),
        ("publisher-sha-format", "[[ \"${GITHUB_SHA:-}\" =~ ^[0-9a-f]{40}$ ]]", None),
    ):
        require(source.count(before) == 1, f"recovery source identity fixture anchor drift: {label}")
    for label, mutated in mutations:
        require(mutated != source, f"recovery run-body fixture unchanged: {label}")
        try:
            require_reviewed_workflow_blob(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"recovery unreviewed run-body mutation accepted: {label}")


def require_reviewed_negative_workflow_blob(source: str) -> None:
    """Bind the complete read-only negative CI source, not just action names."""
    payload = source.encode("utf-8")
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    require(hashlib.sha1(git_blob).hexdigest() == REVIEWED_NEGATIVE_WORKFLOW_BLOB_SHA,
            "admission negative CI complete workflow source drift")


def prove_negative_workflow_branch_guards_runtime(source: str) -> None:
    """Run reviewed PR-base and push-ref predicates with bounded synthetic inputs."""
    pr = 'test "${GITHUB_BASE_REF:-}" = "so"'
    push = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
    require(source.count(pr) == 1 and source.count(push) == 2,
            "admission negative CI runtime branch predicate inventory drift")
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
        require((completed.returncode == 0) == expected,
                "admission negative CI runtime branch predicate drift: " + label)
    print("PASS: admission negative CI PR/push branch guard runtime (6 cases)")


def require_negative_workflow_source_negatives(source: str) -> None:
    require_reviewed_negative_workflow_blob(source)
    prove_negative_workflow_branch_guards_runtime(source)
    cases = (
        ("floating-checkout", "actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@v4"),
        ("persisted-credentials", "persist-credentials: false", "persist-credentials: true"),
        ("missing-pr-head-guard", '[[ "$pr_head" =~ ^[0-9a-f]{40}$ ]]', "true"),
        ("dispatch-other-branch", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n            test "${GITHUB_REF:-}" = "refs/heads/so"', 'elif [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n            true # bypass dispatch ref'),
        ("missing-push-ref-guard", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then\n            test "${GITHUB_REF:-}" = "refs/heads/so"', 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then\n            true # bypass push ref'),
        ("missing-push-sha-guard", '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]', "true # bypass push SHA"),
        ("unreviewed-event-accepted", 'echo "Unreviewed admission negative CI event" >&2\n            exit 1', 'echo "Unreviewed admission negative CI event" >&2\n            exit 0'),
        ("push-event-substituted", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then', 'elif [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then'),
        ("skipped-chain-negative", "run: python scripts/validate-memory-os-backup-restore-admission-chain-negative.py", "run: echo UNREVIEWED"),
        ("injected-shell", "          python -m py_compile", "          echo UNREVIEWED\n          python -m py_compile"),
        ("missing-pr-base-guard", 'test "${GITHUB_BASE_REF:-}" = "so"', 'test "${GITHUB_BASE_REF:-}" = "main"'),
        ("missing-pr-target-filter", "  pull_request:\n    branches:\n      - so\n    paths:\n", "  pull_request:\n    paths:\n"),
    )
    for label, before, after in cases:
        require(source.count(before) == 1, f"admission negative CI fixture anchor drift: {label}")
        mutated = source.replace(before, after, 1)
        require(mutated != source, f"admission negative CI fixture unchanged: {label}")
        try:
            require_reviewed_negative_workflow_blob(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"admission negative CI source mutation accepted: {label}")


def require_reviewed_readonly_workflow_blob(source: str) -> None:
    """Bind complete read-only admission source, including shell and trigger bytes."""
    payload = source.encode("utf-8")
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    require(hashlib.sha1(git_blob).hexdigest() == REVIEWED_READONLY_WORKFLOW_BLOB_SHA,
            "admission readonly CI complete workflow source drift")


def prove_readonly_branch_guards_runtime(source: str) -> None:
    """Execute the reviewed readonly PR base and push-ref predicates."""
    pr = 'test "${PR_BASE_REF:-}" = "so"'
    push = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
    require(source.count(pr) == 1 and source.count(push) == 2,
            "admission readonly branch guard source drift")
    cases = (
        ("PR so", pr, "PR_BASE_REF", "so", True),
        ("PR main", pr, "PR_BASE_REF", "main", False),
        ("PR missing", pr, "PR_BASE_REF", "", False),
        ("push so", push, "GITHUB_REF", "refs/heads/so", True),
        ("push main", push, "GITHUB_REF", "refs/heads/main", False),
        ("push tag", push, "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        require((result.returncode == 0) == expected,
                "admission readonly branch runtime guard drift: " + label)
    print("PASS: admission readonly PR/push branch guard runtime (6 cases)")


def require_readonly_workflow_source_negatives(source: str) -> None:
    require_reviewed_readonly_workflow_blob(source)
    prove_readonly_branch_guards_runtime(source)
    cases = (
        ("PR target changed", "  pull_request:\n    branches: [so]\n    paths:\n", "  pull_request:\n    branches: [main]\n    paths:\n"),
        ("PR base environment removed", "PR_BASE_REF: ${{ github.base_ref }}", "PR_BASE_REF: main"),
        ("PR base assertion removed", 'test "${PR_BASE_REF:-}" = "so"', "true"),
        ("floating-checkout", "actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@v4"),
        ("persisted-credentials", "persist-credentials: false", "persist-credentials: true"),
        ("missing-pr-head-guard", '[[ "$pr_head" =~ ^[0-9a-f]{40}$ ]]', "true"),
        ("dispatch-other-branch", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n            test "${GITHUB_REF:-}" = "refs/heads/so"', 'elif [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n            true # bypass dispatch ref'),
        ("missing-push-ref-guard", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then\n            test "${GITHUB_REF:-}" = "refs/heads/so"', 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then\n            true # bypass push ref'),
        ("missing-push-sha-guard", '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]', "true # bypass push SHA"),
        ("unreviewed-event-accepted", 'echo "Unreviewed admission readonly event" >&2\n            exit 1', 'echo "Unreviewed admission readonly event" >&2\n            exit 0'),
        ("push-event-substituted", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then', 'elif [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then'),
        ("skipped-full-chain", "python scripts/validate-memory-os-backup-restore-admission-chain-full.py", "echo UNREVIEWED"),
        ("injected-shell", "          python -m py_compile", "          echo UNREVIEWED\n          python -m py_compile"),
    )
    for label, before, after in cases:
        require(source.count(before) == 1, f"admission readonly CI fixture anchor drift: {label}")
        mutated = source.replace(before, after, 1)
        require(mutated != source, f"admission readonly CI fixture unchanged: {label}")
        try:
            require_reviewed_readonly_workflow_blob(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"admission readonly CI source mutation accepted: {label}")

    # Independent admission readonly CI must run when the permission gate or
    # either external workflow-permission validator changes.
    permission_trigger = '      - ".github/workflows/backup-restore-permission-boundary-negative.yml"\n'
    require(source.count(permission_trigger) == 2,
            "admission readonly permission trigger fixture inventory drift")
    before_push, after_push = source.split("  push:\n", 1)
    trigger_mutations = (
        ("missing-permission-gate-pr-trigger",
         before_push.replace(permission_trigger, "", 1) + "  push:\n" + after_push),
        ("missing-permission-gate-push-trigger",
         before_push + "  push:\n" + after_push.replace(permission_trigger, "", 1)),
    )
    require(len(cases) + len(trigger_mutations) == 15,
            "admission readonly negative diagnostic inventory drift")
    for label, mutated in trigger_mutations:
        require(mutated != source, f"admission readonly trigger fixture unchanged: {label}")
        try:
            require_reviewed_readonly_workflow_blob(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"admission readonly CI trigger mutation accepted: {label}")


def require_diagnostic_privacy_source(source: str) -> None:
    """Forbid raw admission-chain logs in diagnostics and public CI."""
    marker = "              'output': 'REDACTED: admission chain validation failed; consult CI job logs',\n"
    suppressed = '          printf "Admission chain validation exit code: %s (raw validator log suppressed)\\n" "$code"\n'
    require(source.count(marker) == 1, "admission-chain diagnostic redaction marker drift")
    require(source.count(suppressed) == 1, "admission-chain raw CI log suppression drift")
    require("text[-12000:]" not in source, "admission-chain raw diagnostic tail restored")
    require('          cat "$log"\n' not in source, "admission-chain raw CI log echo restored")


def require_diagnostic_privacy_negatives(source: str) -> None:
    require_diagnostic_privacy_source(source)
    cases = (
        ("raw diagnostic", "              'output': 'REDACTED: admission chain validation failed; consult CI job logs',\n",
         "              'output': Path('/tmp/backup-restore-admission-chain.log').read_text(),\n"),
        ("raw CI log", '          printf "Admission chain validation exit code: %s (raw validator log suppressed)\\n" "$code"\n',
         '          cat "$log"\n'),
        ("missing redaction", "              'output': 'REDACTED: admission chain validation failed; consult CI job logs',\n", ""),
    )
    for label, old, new in cases:
        require(source.count(old) == 1, "admission-chain diagnostic fixture anchor drift: " + label)
        mutated = source.replace(old, new, 1)
        require(mutated != source, "admission-chain diagnostic fixture unchanged: " + label)
        try:
            require_diagnostic_privacy_source(mutated)
        except Fail:
            pass
        else:
            raise Fail("admission-chain diagnostic accepted privacy regression: " + label)
    print(f"PASS: admission-chain diagnostic privacy negatives ({len(cases)} cases)")


def prove_diagnostic_redaction_runtime(source: str) -> None:
    """Execute the exact inline diagnostic writer in a temporary directory."""
    start = "          python - <<'PY'\n"
    end = "          PY\n"
    require(source.count(start) == 1 and source.count(end) == 1,
            "admission-chain diagnostic writer not uniquely reachable")
    inline = source.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="admission-chain-diagnostic-") as tmpdir:
        env = os.environ.copy()
        env.update({
            "SOURCE_SHA": "b" * 40,
            "CHAIN_EXIT_CODE": "37",
            "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_MNO",
        })
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=tmpdir, env=env,
            capture_output=True, text=True, check=False,
        )
        require(result.returncode == 0,
                "admission-chain isolated diagnostic failed: " + result.stderr[:500])
        output = Path(tmpdir) / "docs/fixtures/memory-os-operability/backup-restore-admission-chain-diagnostic.last.json"
        data = json.loads(output.read_text(encoding="utf-8"))
        require(data.get("output") == "REDACTED: admission chain validation failed; consult CI job logs",
                "admission-chain diagnostic persisted raw validator output")
        require(data.get("sourceCommitSha") == "b" * 40 and data.get("exitCode") == 37,
                "admission-chain diagnostic source/exit binding drift")
        require(data.get("containsSecrets") is False and data.get("preflightCreatedPrerequisite") is False,
                "admission-chain diagnostic secret/prerequisite flags drift")
        require(data.get("productionEvidence") is False and data.get("productionReady") is False,
                "admission-chain diagnostic production evidence/readiness drift")
        require(data.get("typedEvidenceCreated") is False and data.get("restoreExecuted") is False,
                "admission-chain diagnostic typed/restore flags drift")
        require("CANARY_DO_NOT_PERSIST_MNO" not in output.read_text(encoding="utf-8"),
                "admission-chain diagnostic persisted synthetic canary")
    print("PASS: admission-chain isolated diagnostic redaction (1 runtime case)")


def run_independent_workflow_permission_negative() -> None:
    """Execute the separate event-specific permission source negative from this CI-reachable gate."""
    path = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain-workflow-permissions-negative.py"
    require(path.is_file() and not path.is_symlink(),
            "independent workflow permission negative missing or substituted")
    completed = subprocess.run(
        [sys.executable, str(path)], cwd=ROOT, capture_output=True, text=True,
        check=False, timeout=120,
    )
    require(completed.returncode == 0,
            "independent workflow permission negative failed: exit " + str(completed.returncode))
    for expected in (
        "PASS: independent permission event-specific trigger reachability (36 removals; 1 shortened inventory negative)",
        "PASS: admission chain negative event-specific trigger reachability (152 removals; 1 shortened inventory negative)",
        "Backup/restore admission-chain workflow permission negative PASS",
    ):
        require(expected in completed.stdout,
                "independent workflow permission negative proof output missing")
    print("PASS: CI-reachable independent permission trigger negatives (36 + 152 omissions; 2 inventory negatives)")


def main() -> int:
    require(NEGATIVE_WORKFLOW.is_file() and not NEGATIVE_WORKFLOW.is_symlink(),
            "admission negative CI workflow missing or substituted")
    require_negative_workflow_source_negatives(NEGATIVE_WORKFLOW.read_text(encoding="utf-8"))
    require(READONLY_WORKFLOW.is_file() and not READONLY_WORKFLOW.is_symlink(),
            "admission readonly CI workflow missing or substituted")
    require_readonly_workflow_source_negatives(READONLY_WORKFLOW.read_text(encoding="utf-8"))
    text = WORKFLOW.read_text(encoding="utf-8")
    require_root_event_negatives(text)
    require_trigger_path_negatives(text)
    require_run_body_negatives(text)
    require_diagnostic_privacy_negatives(text)
    prove_diagnostic_redaction_runtime(text)
    require("pull_request_target:" not in text, "backup/restore admission chain must not use pull_request_target")
    require("permissions:\n  contents: read\n" in text, "admission-chain workflow default token must remain read-only")
    require("\njobs:\n  validate-pr:\n" in text, "dedicated admission-chain PR validation job missing")
    require("\n  validate-and-publish:\n" in text, "dedicated admission-chain non-PR publication job missing")

    _, jobs = text.split("\njobs:\n", 1)
    validate_pr, publish = jobs.split("\n  validate-and-publish:\n", 1)

    require("if: github.event_name == 'pull_request'" in validate_pr, "admission-chain PR validator must be pull-request-only")
    require("permissions:\n      contents: read" in validate_pr, "admission-chain PR validator must explicitly remain contents: read")
    require("ref: ${{ github.event.pull_request.head.sha }}" in validate_pr, "admission-chain PR validator must checkout exact pull-request head")
    require("contents: write" not in validate_pr, "admission-chain PR validator unexpectedly has write authority")
    require("test -z \"$(git status --porcelain)\"" in validate_pr, "admission-chain PR validator must require a clean source")
    require("validate-memory-os-backup-restore-admission-chain-full.py" in validate_pr, "admission-chain PR validator must execute the full authority chain")
    require("git diff --exit-code" in validate_pr, "admission-chain PR validator must reject deterministic authority drift")

    publish_header = publish.split("steps:", 1)[0]
    require_publisher_event_scope(publish_header)
    require_reviewed_executable_negatives(validate_pr, pr=True)
    require_reviewed_executable_negatives(publish, pr=False)
    require_reviewed_controls(validate_pr, pr=True)
    require_control_negatives(publish)
    approved_if = "    " + "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"
    mutations = (
        publish_header.replace(approved_if, "    if: github.event_name != 'pull_request'", 1),
        publish_header.replace("refs/heads/so", "refs/heads/main", 1),
        publish_header.replace(approved_if, approved_if + "\n    if: true", 1),
        publish_header.replace("github.event_name == 'push'",
                               "github.event_name == 'pull_request_target'", 1),
        publish_header.replace(approved_if,
                               approved_if + "\n    \"if\": true", 1),
        publish_header.replace(approved_if,
                               approved_if + "\n    'permissions':\n      contents: write", 1),
        publish_header.replace(approved_if,
                               approved_if + "\n    environment: production", 1),
        publish_header.replace(approved_if,
                               approved_if + "\n    'steps': []", 1),
    )
    for mutated in mutations:
        require(mutated != publish_header, "publisher scope negative fixture unchanged")
        try:
            require_publisher_event_scope(mutated)
        except Fail:
            pass
        else:
            raise Fail("publisher scope negative mutation accepted")
    require("permissions:\n      contents: write" in publish_header, "admission-chain publisher must hold write authority only at job scope")
    require("ref: ${{ github.sha }}" in publish, "admission-chain publisher must checkout exact event SHA")
    require("git rev-parse origin/so" in publish, "admission-chain publisher must retain stale-source CAS")
    require("revalidate_latest_chain" in publish, "admission-chain publisher must retain bounded latest-so full revalidation")
    require("os.replace(tmp_name, path)" in publish, "admission-chain failure diagnostic must retain atomic replacement")
    require("'productionEvidence': False" in publish, "admission-chain failure diagnostic must remain non-production evidence")
    require("'productionReady': False" in publish, "admission-chain failure diagnostic must not claim production readiness")

    print("PASS: end-to-end admission PR validation is exact-head and read-only")
    print("PASS: admission publication is so push/dispatch-only with job-scoped write authority")
    print("publisher event/ref and job-key negative mutations rejected: 8")
    print("admission executable negative mutations rejected: 16")
    print("step-control negative mutations rejected: 4")
    print("PASS: bounded full revalidation, stale-source CAS and atomic failure diagnostics remain enforced")
    print("production evidence generated: false")
    print("workflow root/event negative mutations rejected: 6")
    print("workflow trigger-path negative mutations rejected: 7")
    print("complete workflow run-body negative mutations rejected: 3")
    print("independent admission negative CI source mutations rejected: 12")
    print("independent admission readonly CI source mutations rejected: 15")
    run_independent_workflow_permission_negative()
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
