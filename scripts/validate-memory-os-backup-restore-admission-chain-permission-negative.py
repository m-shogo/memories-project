#!/usr/bin/env python3
"""Fail closed if end-to-end backup/restore admission PR validation regains write authority."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-admission-chain.yml"


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


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    require_root_event_negatives(text)
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
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
