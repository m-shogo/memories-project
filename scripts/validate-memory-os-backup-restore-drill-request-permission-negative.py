#!/usr/bin/env python3
"""Fail closed if restore-drill planning PR validation regains repository write authority."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-drill-request.yml"
ROLLBACK_WORKFLOW = ROOT / ".github/workflows/backup-restore-drill-request-reconcile-rollback.yml"
REVIEWED_ROLLBACK_WORKFLOW_BLOB_SHA = "9bb45262fb5cc1cf8121e81040a8b0107db5a1ef"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_publication_scope(header: str) -> None:
    expected = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n    permissions:\n      contents: write\n"
    require(header.startswith(expected),
            "drill publication event/ref authority drift")
    keys = []
    for line in header.splitlines():
        if not line.startswith("    ") or line.startswith("     "):
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"    ([a-z][a-z-]*):(?:[ \t].*)?", line)
        require(match is not None, "publication job key inventory drift")
        keys.append(match.group(1))
    require(tuple(keys) == ("if", "permissions", "runs-on", "timeout-minutes"),
            "publication job key inventory drift")



def require_reviewed_bootstrap(job: str, *, pr: bool) -> tuple[str, str]:
    """Bind both immutable actions, exact checkout source, and credential persistence."""
    name = "Checkout exact pull request source" if pr else "Checkout exact source"
    source = (
        "ref: ${{ github.event.pull_request.head.sha }}"
        if pr else "ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}"
    )
    checkout = (
        f"      - name: {name}\n"
        "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n"
        "        with:\n"
        f"          {source}\n"
        "          fetch-depth: 0\n"
        f"          persist-credentials: {'false' if pr else 'true'}\n"
    )
    setup = (
        "      - name: Set up Python\n"
        "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n"
        "        with:\n"
        '          python-version: "3.12"\n'
    )
    require(job.count(checkout) == 1, "drill bootstrap checkout source or credentials drift")
    require(job.count(setup) == 1, "drill bootstrap Python action drift")
    uses = re.findall(r"(?m)^\s*uses:\s*([^\n]+)$", job)
    require(uses == [
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    ], "drill bootstrap action inventory drift")
    require(not re.search(r"(?m)^\s*-\s+uses\s*:", job),
            "drill bootstrap unreviewed unnamed action step")
    require(not re.search(r"""(?m)^\s*(?:-\s*)?["\']uses["\']\s*:""", job),
            "drill bootstrap quoted action key drift")
    return checkout, setup


def require_bootstrap_negatives(job: str, *, pr: bool) -> None:
    checkout, setup = require_reviewed_bootstrap(job, pr=pr)
    credential = "false" if pr else "true"
    mutations = (
        job.replace("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@v4", 1),
        job.replace("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@11d5960a326750d5838078e36cf38b85af677260", 1),
        job.replace("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "actions/setup-python@v5", 1),
        job.replace("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87060", 1),
        job.replace(f"          persist-credentials: {credential}\n",
                    f"          persist-credentials: {'true' if pr else 'false'}\n", 1),
        job.replace(f"          persist-credentials: {credential}\n", "", 1),
        job.replace(checkout, checkout.replace("fetch-depth: 0", "fetch-depth: 1"), 1),
        job.replace(checkout, checkout + "      - uses: actions/checkout@v4\n", 1),
        job.replace(checkout, checkout + '      - "uses": actions/checkout@v4\n', 1),
        job.replace(checkout, checkout + '      - name: Unreviewed action\n        "uses": actions/checkout@v4\n', 1),
    )
    for mutated in mutations:
        require(mutated != job, "drill bootstrap negative fixture did not mutate")
        try:
            require_reviewed_bootstrap(mutated, pr=pr)
        except Fail:
            pass
        else:
            raise Fail("drill bootstrap negative mutation accepted")


REVIEWED_STEP_HEADERS = {
    True: ["      - name: Checkout exact pull request source","      - name: Set up Python","      - name: Validate drill planning authority read-only"],
    False: ["      - name: Checkout exact source","      - name: Set up Python","      - name: Capture exact drill planning authority source","      - name: Validate and reconcile planning authority","      - name: Reject stale drill planning authority on pull requests","      - name: Commit bounded drill planning authority","      - name: Record privacy-safe drill request diagnostic","      - name: Enforce drill request admission validation","      - name: Re-read canonical authority after reconciliation"],
}


def require_reviewed_step_inventory(job: str, *, pr: bool) -> None:
    actual = [line for line in job.splitlines() if line.startswith("      - ")]
    require(actual == REVIEWED_STEP_HEADERS[pr],
            "drill executable step header inventory drift")


def require_step_inventory_negatives(job: str, *, pr: bool) -> None:
    require_reviewed_step_inventory(job, pr=pr)
    anchor = "    steps:\n"
    require(job.count(anchor) == 1, "drill reviewed steps anchor drift")
    mutations = (
        job.replace(anchor, anchor + "      - run: echo unreviewed\n", 1),
        job.replace(anchor, anchor + "      - name: Unreviewed shell\n        run: echo unreviewed\n", 1),
        job.replace(anchor, anchor + '      - "run": echo unreviewed\n', 1),
    )
    for index, mutated in enumerate(mutations, 1):
        require(mutated != job, "drill step inventory negative fixture unchanged")
        try:
            require_reviewed_step_inventory(mutated, pr=pr)
        except Fail:
            pass
        else:
            raise Fail(f"drill step inventory negative mutation {index} accepted")


REVIEWED_STEP_KEYS = {True: [["uses","with"],["uses","with"],["run"]], False: [["uses","with"],["uses","with"],["run"],["id","run"],["if","run"],["if","run"],["if","env","run"],["run"],["if","run"]]}


def require_reviewed_step_keys(job: str, *, pr: bool) -> None:
    """Bind ordered step-level YAML keys, including duplicate and quoted keys."""
    blocks = re.split(r"(?m)(?=^      - (?:uses|name): )", job)
    steps = [block for block in blocks if block.startswith("      - ")]
    actual = []
    for block in steps:
        properties = []
        for line in re.findall(r"(?m)^        ([^ \t#\n][^\n]*)$", block):
            match = re.fullmatch(r"([a-z][a-z-]*):(?:[ \t].*)?", line)
            require(match is not None, "drill unreviewed or quoted step property")
            properties.append(match.group(1))
        actual.append(properties)
    require(actual == REVIEWED_STEP_KEYS[pr], "drill step property inventory drift")


def require_step_key_negatives(job: str, *, pr: bool) -> None:
    require_reviewed_step_keys(job, pr=pr)
    anchor = "        run: |\n"
    require(anchor in job, "drill step-property fixture anchor missing")
    mutations = (
        ("continue-on-error", "        continue-on-error: true\n" + anchor),
        ("quoted-key", '        "continue-on-error": true\n' + anchor),
        ("env", "        env:\n          UNREVIEWED: yes\n" + anchor),
        ("working-directory", "        working-directory: /tmp\n" + anchor),
        ("timeout", "        timeout-minutes: 1\n" + anchor),
        ("duplicate-run", "        run: echo unreviewed\n" + anchor),
        ("quoted-run", '        "run": echo unreviewed\n' + anchor),
    )
    for label, replacement in mutations:
        mutated = job.replace(anchor, replacement, 1)
        require(mutated != job, f"drill negative fixture unchanged: {label}")
        try:
            require_reviewed_step_keys(mutated, pr=pr)
        except Fail:
            pass
        else:
            raise Fail(f"drill unreviewed step-property accepted: {label}")




REVIEWED_CONTROL_LINES = {True: [[],[],[]], False: [[],[],[],["        id: admission"],["        if: steps.admission.outputs.exit_code == '0' && github.event_name == 'pull_request'"],["        if: steps.admission.outputs.exit_code == '0' && github.event_name != 'pull_request' && github.ref == 'refs/heads/so'"],["        if: steps.admission.outputs.exit_code != '0' && github.event_name != 'pull_request' && github.ref == 'refs/heads/so'","        env:","          ADMISSION_EXIT_CODE: ${{ steps.admission.outputs.exit_code }}"],[],["        if: steps.admission.outputs.exit_code == '0' && github.event_name != 'pull_request' && github.ref == 'refs/heads/so'"]]}


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
            "drill step control values drift")


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
        require(mutated != job, f"drill control fixture unchanged: {label}")
        try:
            require_reviewed_controls(mutated, pr=False)
        except Fail:
            pass
        else:
            raise Fail(f"drill unreviewed control mutation accepted: {label}")



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



REVIEWED_TRIGGER_PATHS = [".github/workflows/backup-restore-drill-request.yml","contracts/operations/backup-restore-drill-request-contract.v1.json","contracts/operations/backup-restore-drill-request-registry.v1.json","contracts/operations/production-equivalent-environment-generation-contract.v1.json","contracts/operations/production-equivalent-environment-generation-registry.v1.json","contracts/operations/recovery-objectives-admission-contract.v1.json","contracts/operations/recovery-objectives-registry.v1.json","contracts/operations/backup-restore-generation-evidence-contract.v1.json","contracts/operations/backup-restore-generation-evidence-registry.v1.json","contracts/operations/backup-restore-generation-binding-contract.v1.json","contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json","contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json","contracts/operations/production-operability-status.json","docs/evidence/backup-restore/**","docs/evidence/recovery-objectives/approvals/**","docs/fixtures/memory-os-operability/backup-restore-generation-evidence/**","docs/fixtures/memory-os-operability/recovery-objectives-approval/**","docs/runbooks/memory-os-production-equivalent-backup-restore-drill.md","scripts/memory_os_backup_restore_blockers.py","scripts/memory_os_environment_generation_eligibility.py","scripts/validate-memory-os-production-equivalent-environment-generation.py","scripts/register-memory-os-recovery-objectives.py","scripts/validate-memory-os-recovery-objectives.py","scripts/validate-memory-os-recovery-objectives-negative.py","scripts/request-memory-os-backup-restore-drill.py","scripts/validate-memory-os-backup-restore-drill-request.py","scripts/validate-memory-os-backup-restore-drill-request-writer-authority.py","scripts/validate-memory-os-backup-restore-drill-request-negative.py","scripts/validate-memory-os-backup-restore-drill-request-digest-negative.py","scripts/validate-memory-os-backup-restore-drill-objective-authority-negative.py","scripts/validate-memory-os-backup-restore-drill-request-load-negative.py","scripts/validate-memory-os-backup-restore-drill-request-reconcile-negative.py","scripts/validate-memory-os-backup-restore-drill-request-append-rollback-negative.py","scripts/reconcile-memory-os-backup-restore-drill-request.py","scripts/register-memory-os-backup-restore-generation-evidence.py","scripts/validate-memory-os-backup-restore-generation-evidence.py","scripts/validate-memory-os-backup-restore-review-source-order.py","scripts/validate-memory-os-backup-restore-generation-independent-review.py","scripts/validate-memory-os-backup-restore-generation-evidence-negative.py","scripts/validate-memory-os-backup-restore-semantic-generation-negative.py","scripts/register-memory-os-backup-restore-non-resurrection-evidence.py","scripts/validate-memory-os-backup-restore-non-resurrection-admission.py","scripts/validate-memory-os-backup-restore-non-resurrection-negative.py","scripts/validate-memory-os-backup-restore-generation-binding.py","scripts/validate-memory-os-backup-restore-generation-binding-negative.py","scripts/validate-memory-os-operability.py"]


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



REVIEWED_WORKFLOW_GIT_BLOB_SHA = "33a5089f6e629f5aaed48050a110b125532e1df5"


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
    )
    for label, mutated in mutations:
        require(mutated != source, f"recovery run-body fixture unchanged: {label}")
        try:
            require_reviewed_workflow_blob(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"recovery unreviewed run-body mutation accepted: {label}")


def require_reviewed_rollback_workflow_blob(source: str) -> None:
    """Bind the complete drill request rollback CI source."""
    payload = source.encode("utf-8")
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    require(hashlib.sha1(git_blob).hexdigest() == REVIEWED_ROLLBACK_WORKFLOW_BLOB_SHA,
            "drill rollback CI complete workflow source drift")


def require_rollback_workflow_source_negatives(source: str) -> None:
    require_reviewed_rollback_workflow_blob(source)
    cases = (
        ("floating-checkout", "actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@v4"),
        ("persisted-credentials", "persist-credentials: false", "persist-credentials: true"),
        ("missing-pr-head-guard", '[[ "$pr_head" =~ ^[0-9a-f]{40}$ ]]', "true"),
        ("dispatch-other-branch", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n            test "${GITHUB_REF:-}" = "refs/heads/so"', 'elif [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then\n            true # bypass dispatch ref'),
        ("missing-push-ref-guard", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then\n            test "${GITHUB_REF:-}" = "refs/heads/so"', 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then\n            true # bypass push ref'),
        ("missing-push-sha-guard", '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]', "true # bypass push SHA"),
        ("unreviewed-event-accepted", 'echo "Unreviewed drill rollback CI event" >&2\n            exit 1', 'echo "Unreviewed drill rollback CI event" >&2\n            exit 0'),
        ("push-event-substituted", 'elif [[ "${GITHUB_EVENT_NAME:-}" == "push" ]]; then', 'elif [[ "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]; then'),
        ("skipped-reconcile-negative", "python scripts/validate-memory-os-backup-restore-drill-request-reconcile-negative.py", "echo UNREVIEWED"),
        ("injected-shell", "          python -m py_compile", "          echo UNREVIEWED\n          python -m py_compile"),
        ("PR target", "  pull_request:\n    branches: [so]\n    paths:\n", "  pull_request:\n    branches: [main]\n    paths:\n"),
        ("PR base assertion", 'test "${GITHUB_BASE_REF:-}" = "so"', "true # bypass PR base"),
    )
    require(len(cases) == 12, "drill rollback CI source mutation inventory drift")
    for label, before, after in cases:
        require(source.count(before) == 1, f"drill rollback CI fixture anchor drift: {label}")
        mutated = source.replace(before, after, 1)
        require(mutated != source, f"drill rollback CI fixture unchanged: {label}")
        try:
            require_reviewed_rollback_workflow_blob(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"drill rollback CI source mutation accepted: {label}")

    # This dedicated rollback proof must run when its external permission
    # negative validator changes, independently of the broader permission CI.
    marker = '      - "scripts/validate-memory-os-backup-restore-drill-request-permission-negative.py"\n'
    require(source.count(marker) == 2,
            "drill rollback permission-validator trigger inventory drift")
    before_push, after_push = source.split("  push:\n", 1)
    trigger_mutations = (
        ("missing permission validator PR trigger",
         before_push.replace(marker, "", 1) + "  push:\n" + after_push),
        ("missing permission validator push trigger",
         before_push + "  push:\n" + after_push.replace(marker, "", 1)),
    )
    require(len(cases) + len(trigger_mutations) == 14, "drill rollback CI total mutation inventory drift")
    for label, mutated in trigger_mutations:
        require(mutated != source, f"drill rollback trigger fixture unchanged: {label}")
        try:
            require_reviewed_rollback_workflow_blob(mutated)
        except Fail:
            pass
        else:
            raise Fail(f"drill rollback CI trigger mutation accepted: {label}")


def prove_rollback_branch_guards_runtime(source: str) -> None:
    """Execute reviewed PR and push/dispatch predicates with synthetic refs."""
    pr_command = 'test "${GITHUB_BASE_REF:-}" = "so"'
    push_command = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
    require(source.count(pr_command) == 1, "drill rollback CI PR-base predicate drift")
    require(source.count(push_command) == 2, "drill rollback CI push/dispatch predicate drift")
    cases = (
        ("PR so", pr_command, "GITHUB_BASE_REF", "so", True),
        ("PR main", pr_command, "GITHUB_BASE_REF", "main", False),
        ("PR missing", pr_command, "GITHUB_BASE_REF", "", False),
        ("push so", push_command, "GITHUB_REF", "refs/heads/so", True),
        ("push main", push_command, "GITHUB_REF", "refs/heads/main", False),
        ("push tag", push_command, "GITHUB_REF", "refs/tags/v1", False),
    )
    for label, command, key, value, expected in cases:
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}
        result = subprocess.run(["bash", "-e", "-c", command], env=env, capture_output=True, check=False)
        require((result.returncode == 0) == expected, "drill rollback CI runtime branch drift: " + label)
    print("PASS: drill rollback CI PR/push branch guard runtime (6 cases)")


def require_diagnostic_privacy_source(source: str) -> None:
    """Reject raw validator output in committed diagnostics or public CI logs."""
    marker = "              'output': 'REDACTED: drill request validation failed; consult CI job logs',\n"
    suppressed = '          printf "Drill request validation exit code: %s (raw validator log suppressed)\\n" "$code"\n'
    require(source.count(marker) == 1, "drill diagnostic fixed-redaction marker drift")
    require(source.count(suppressed) == 1, "drill raw CI log suppression drift")
    require("text[-12000:]" not in source, "drill diagnostic raw output tail restored")
    require('          cat "$log"\n' not in source, "drill raw validator CI log echo restored")


def require_diagnostic_privacy_negatives(source: str) -> None:
    require_diagnostic_privacy_source(source)
    cases = (
        ("raw diagnostic", "              'output': 'REDACTED: drill request validation failed; consult CI job logs',\n",
         "              'output': Path('/tmp/backup-restore-drill-request.log').read_text(),\n"),
        ("raw CI log", '          printf "Drill request validation exit code: %s (raw validator log suppressed)\\n" "$code"\n',
         '          cat "$log"\n'),
        ("diagnostic removed", "              'output': 'REDACTED: drill request validation failed; consult CI job logs',\n", ""),
    )
    for label, old, new in cases:
        require(source.count(old) == 1, "drill diagnostic fixture anchor drift: " + label)
        mutated = source.replace(old, new, 1)
        require(mutated != source, "drill diagnostic fixture unchanged: " + label)
        try:
            require_diagnostic_privacy_source(mutated)
        except Fail:
            pass
        else:
            raise Fail("drill diagnostic accepted privacy regression: " + label)
    print(f"PASS: drill request diagnostic privacy negatives ({len(cases)} cases)")


def prove_diagnostic_redaction_runtime(source: str) -> None:
    """Execute the actual inline writer in an isolated temporary directory."""
    start = "          python - <<'PY'\n"
    end = "          PY\n"
    require(source.count(start) == 1 and source.count(end) == 1,
            "drill diagnostic inline writer must be uniquely reachable")
    inline = source.split(start, 1)[1].split(end, 1)[0]
    script = "\n".join(line[10:] for line in inline.splitlines()) + "\n"
    with tempfile.TemporaryDirectory(prefix="drill-request-diagnostic-redaction-") as tmpdir:
        env = os.environ.copy()
        env.update({
            "SOURCE_SHA": "b" * 40,
            "ADMISSION_EXIT_CODE": "13",
            "SENSITIVE_CANARY": "CANARY_DO_NOT_PERSIST_456",
        })
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=tmpdir, env=env,
            capture_output=True, text=True, check=False,
        )
        require(result.returncode == 0,
                "drill diagnostic isolated writer failed: " + result.stderr[:500])
        output = Path(tmpdir) / "docs/fixtures/memory-os-operability/backup-restore-drill-request-diagnostic.last.json"
        data = json.loads(output.read_text(encoding="utf-8"))
        require(data.get("output") == "REDACTED: drill request validation failed; consult CI job logs",
                "drill diagnostic persisted unreviewed validator output")
        require(data.get("sourceCommitSha") == "b" * 40 and data.get("exitCode") == 13,
                "drill diagnostic source/exit binding drift")
        require(data.get("containsSecrets") is False and data.get("requestCreated") is False,
                "drill diagnostic secret/request flags drift")
        require(data.get("productionEvidence") is False and data.get("productionReady") is False,
                "drill diagnostic evidence/readiness flags drift")
        require("CANARY_DO_NOT_PERSIST_456" not in output.read_text(encoding="utf-8"),
                "drill diagnostic persisted synthetic sensitive content")
        output.chmod(0o640)
        mode_positive = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                       capture_output=True, text=True, timeout=15, check=False)
        require(mode_positive.returncode == 0 and stat.S_IMODE(output.stat().st_mode) == 0o640,
                "drill diagnostic did not preserve existing mode")
        previous = output.read_bytes()
        for label, source, replacement in (
            ("replace", "os.replace(tmp_name, path)", "raise OSError('synthetic drill diagnostic replace failure')"),
            ("fsync", "os.fsync(handle.fileno())", "raise OSError('synthetic drill diagnostic fsync failure')"),
        ):
            require(script.count(source) == 1, "drill diagnostic failure anchor drift: " + label)
            failure = subprocess.run([sys.executable, "-c", script.replace(source, replacement, 1)],
                                     cwd=tmpdir, env=env, capture_output=True, text=True,
                                     timeout=15, check=False)
            require(failure.returncode != 0 and "synthetic drill diagnostic " + label + " failure" in failure.stderr,
                    "drill diagnostic intended failure not reached: " + label)
            require(output.read_bytes() == previous and stat.S_IMODE(output.stat().st_mode) == 0o640,
                    "drill diagnostic failure mutated prior bytes/mode: " + label)
            require(not list(output.parent.glob(".backup-restore-drill-request-diagnostic.last.json.*.tmp")),
                    "drill diagnostic failure left temporary file: " + label)
        outside = Path(tmpdir) / "external-drill-diagnostic-canary"
        outside.write_bytes(previous)
        output.unlink()
        output.symlink_to(outside)
        symlink = subprocess.run([sys.executable, "-c", script], cwd=tmpdir, env=env,
                                 capture_output=True, text=True, timeout=15, check=False)
        require(symlink.returncode != 0 and "target must not be a symlink" in symlink.stderr,
                "drill diagnostic accepted symlinked output")
        require(output.is_symlink() and outside.read_bytes() == previous,
                "drill diagnostic symlink altered external file")
        require(not list(output.parent.glob(".backup-restore-drill-request-diagnostic.last.json.*.tmp")),
                "drill diagnostic symlink rejection left temporary file")
    print("PASS: drill request diagnostic redaction and atomic runtime (5 cases)")


def main() -> int:
    require(ROLLBACK_WORKFLOW.is_file() and not ROLLBACK_WORKFLOW.is_symlink(),
            "drill rollback CI workflow missing or substituted")
    rollback_source = ROLLBACK_WORKFLOW.read_text(encoding="utf-8")
    require_rollback_workflow_source_negatives(rollback_source)
    prove_rollback_branch_guards_runtime(rollback_source)
    text = WORKFLOW.read_text(encoding="utf-8")
    require_root_event_negatives(text)
    require_trigger_path_negatives(text)
    require_run_body_negatives(text)
    require_diagnostic_privacy_negatives(text)
    prove_diagnostic_redaction_runtime(text)
    require("pull_request_target:" not in text, "drill-request authority must not use pull_request_target")
    require("\njobs:\n  validate-pr:\n" in text, "dedicated drill-request PR validation job missing")
    require("\n  validate:\n" in text, "drill-request non-PR authority job missing")

    _, jobs = text.split("\njobs:\n", 1)
    validate_pr, validate = jobs.split("\n  validate:\n", 1)
    require_bootstrap_negatives(validate_pr, pr=True)
    require_bootstrap_negatives(validate, pr=False)
    require_step_inventory_negatives(validate_pr, pr=True)
    require_step_inventory_negatives(validate, pr=False)
    require_step_key_negatives(validate_pr, pr=True)
    require_step_key_negatives(validate, pr=False)
    require_reviewed_controls(validate_pr, pr=True)
    require_control_negatives(validate)

    require("if: github.event_name == 'pull_request'" in validate_pr, "drill-request PR validator must be pull-request-only")
    require("permissions:\n      contents: read" in validate_pr, "drill-request PR validator must explicitly remain contents: read")
    require("ref: ${{ github.event.pull_request.head.sha }}" in validate_pr, "drill-request PR validator must checkout exact pull-request head")
    require("contents: write" not in validate_pr, "drill-request PR validator unexpectedly has write authority")
    require("test -z \"$(git status --porcelain)\"" in validate_pr, "drill-request PR validator must require a clean exact source")
    require("validate-memory-os-backup-restore-drill-request-writer-authority.py" in validate_pr, "drill-request PR validator must retain writer authority validation")
    require("validate-memory-os-backup-restore-drill-request-reconcile-negative.py" in validate_pr, "drill-request PR validator must retain reconcile negatives")
    require("validate-memory-os-backup-restore-drill-request-append-rollback-negative.py" in validate_pr, "drill-request PR validator must retain append rollback negatives")
    require("validate-memory-os-backup-restore-generation-evidence.py" in validate_pr, "drill-request PR validator must retain downstream generation-evidence validation")
    require("validate-memory-os-backup-restore-non-resurrection-admission.py" in validate_pr, "drill-request PR validator must retain downstream typed non-resurrection validation")
    require("validate-memory-os-operability.py" in validate_pr, "drill-request PR validator must retain aggregate Operability validation")
    require("git diff --exit-code" in validate_pr, "drill-request PR validator must reject deterministic authority drift")

    validate_header = validate.split("steps:", 1)[0]
    require_publication_scope(validate_header)
    approved_if = "    " + "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"
    mutations = (
        validate_header.replace(approved_if, "    if: github.event_name != 'pull_request'", 1),
        validate_header.replace("refs/heads/so", "refs/heads/main", 1),
        validate_header.replace(approved_if, approved_if + "\n    \"if\": true", 1),
        validate_header.replace("github.event_name == 'push'",
                                "github.event_name == 'pull_request_target'", 1),
    )
    for mutated in mutations:
        require(mutated != validate_header, "publisher scope negative fixture unchanged")
        try:
            require_publication_scope(mutated)
        except Fail:
            pass
        else:
            raise Fail("publisher scope negative mutation accepted")
    require("git rev-parse origin/so" in validate, "drill-request publisher must retain stale-source CAS")
    require("SOURCE_SHA" in validate, "drill-request publisher must remain source-bound")
    require("os.replace(tmp_name, path)" in validate, "drill-request failure diagnostic must retain atomic replacement")
    require("'requestCreated': False" in validate, "drill-request failure diagnostic must not fabricate a reviewed request")
    require("'restoreExecuted': False" in validate, "drill-request failure diagnostic must not claim restore execution")
    require("'productionEvidence': False" in validate, "drill-request failure diagnostic must remain non-production evidence")
    require("'productionReady': False" in validate, "drill-request failure diagnostic must not claim production readiness")

    print("PASS: restore-drill planning PR validation is exact-head and read-only")
    print("PASS: reviewed requests remain planning authority only and publication excludes pull requests")
    print("PASS: downstream generation/typed gates, rollback negatives, stale-source CAS and atomic diagnostics remain enforced")
    print("publisher event/ref negative mutations rejected: 4")
    print("immutable bootstrap/source/credential negative mutations rejected: 20")
    print("executable step header negative mutations rejected: 6")
    print("step-property negative mutations rejected: 14")
    print("step-control negative mutations rejected: 4")
    print("production evidence generated: false")
    print("workflow root/event negative mutations rejected: 6")
    print("workflow trigger-path negative mutations rejected: 7")
    print("complete workflow run-body negative mutations rejected: 3")
    print("independent drill rollback CI source mutations rejected: 14")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
