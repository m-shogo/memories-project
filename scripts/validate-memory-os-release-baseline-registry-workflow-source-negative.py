#!/usr/bin/env python3
"""Fail-closed release baseline publisher source, schedule and runtime negative proof."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/release-baseline-registry.yml"
INDEPENDENT = ".github/workflows/release-baseline-registry-source-negative.yml"
SELF = "scripts/validate-memory-os-release-baseline-registry-workflow-source-negative.py"
PUBLISHER_SHA = "e14c1c779228404a75ee03a2d0ec6d4a598764c5"
INDEPENDENT_SHA = "7c3e469bc58787cdcfdf5abbac33869604101588"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
WRITER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch' || github.event_name == 'schedule') && github.ref == 'refs/heads/so'"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
PR_SHA = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA = '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'
WRITER_EVENT = '[[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" || "${GITHUB_EVENT_NAME:-}" == "schedule" ]]'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("release baseline CI source guard: " + message)


def read(path: str) -> str:
    file = ROOT / path
    require(file.is_file() and not file.is_symlink(), "missing or symlinked source: " + path)
    require(file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() == path,
            "source escaped root: " + path)
    return file.read_text(encoding="utf-8")


def check_source(name: str, source: str, expected: str, required: tuple[tuple[str, int], ...]) -> None:
    for token, count in required:
        require(source.count(token) == count, name + " source inventory drift: " + token[:60])
    for forbidden in ("pull_request_target:", "secrets.", "actions/checkout@v4", "actions/setup-python@v5"):
        require(forbidden not in source, name + " unreviewed source")
    data = source.encode("utf-8")
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    require(digest == expected, name + " complete source drift")


PUBLISHER_REQUIRED = (
    ("  pull_request:\n    branches:\n      - so\n", 1),
    ("  push:\n    branches:\n      - so\n", 1),
    ('  schedule:\n    - cron: "23 3 * * 2"\n', 1),
    ("  workflow_dispatch:\n", 1),
    ('      - "' + PUBLISHER + '"\n', 2),
    ('      - "' + INDEPENDENT + '"\n', 2),
    ('      - "' + SELF + '"\n', 2),
    (CHECKOUT, 2),
    (SETUP, 2),
    ("persist-credentials: false", 1),
    ("persist-credentials: true", 1),
    (WRITER_SCOPE, 1),
    (PR_BASE, 1),
    (WRITER_REF, 1),
    (WRITER_EVENT, 1),
    (PR_SHA, 1),
    (WRITER_SHA, 1),
    ("python " + SELF, 2),
    ("permissions:\n  contents: read\n", 1),
    ("      contents: write\n", 1),
    ("      contents: read\n", 1),
)
INDEPENDENT_REQUIRED = (
    ("  pull_request:\n    branches:\n      - so\n", 1),
    ("  push:\n    branches:\n      - so\n", 1),
    ('      - "' + PUBLISHER + '"\n', 2),
    ('      - "' + INDEPENDENT + '"\n', 2),
    ('      - "' + SELF + '"\n', 2),
    (CHECKOUT, 1),
    (SETUP, 1),
    ("persist-credentials: false", 1),
    (PR_BASE, 1),
    (WRITER_REF, 1),
    (PR_SHA, 1),
    ("python " + SELF, 1),
    ("permissions:\n  contents: read\n", 1),
    ("      contents: read\n", 1),
)


def validate(publisher: str, independent: str) -> None:
    check_source("publisher", publisher, PUBLISHER_SHA, PUBLISHER_REQUIRED)
    check_source("independent", independent, INDEPENDENT_SHA, INDEPENDENT_REQUIRED)


def negatives(publisher: str, independent: str) -> None:
    cases = (
        ("publisher PR target", True, "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher writer scope", True, WRITER_SCOPE, "    if: github.event_name != 'pull_request'"),
        ("publisher writer event", True, WRITER_EVENT, "true"),
        ("publisher PR base", True, PR_BASE, "true"),
        ("publisher writer ref", True, WRITER_REF, "true"),
        ("publisher PR SHA", True, PR_SHA, 'test -n "$expected"'),
        ("publisher writer SHA", True, WRITER_SHA, 'test -n "$GITHUB_SHA"'),
        ("publisher checkout pin", True, CHECKOUT, "uses: actions/checkout@v4"),
        ("publisher credentials", True, "persist-credentials: false", "persist-credentials: true"),
        ("publisher self guard", True, "python " + SELF, "echo skip"),
        ("independent PR target", False, "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("independent ref", False, WRITER_REF, "true"),
        ("independent PR base", False, PR_BASE, "true"),
        ("independent SHA", False, PR_SHA, 'test -n "$expected"'),
        ("independent checkout", False, CHECKOUT, "uses: actions/checkout@v4"),
        ("independent self guard", False, "python " + SELF, "echo skip"),
    )
    for label, publisher_case, before, after in cases:
        original = publisher if publisher_case else independent
        require(before in original, "missing mutation anchor: " + label)
        changed = original.replace(before, after, 1)
        require(changed != original, "unchanged mutation: " + label)
        try:
            validate(changed, independent) if publisher_case else validate(publisher, changed)
        except SystemExit:
            continue
        raise SystemExit("release baseline source mutation accepted: " + label)
    print("PASS: release baseline source negatives (16 cases)")


def runtime() -> None:
    for script, key, value, allowed in (
        (PR_BASE, "GITHUB_BASE_REF", "so", True),
        (PR_BASE, "GITHUB_BASE_REF", "main", False),
        (WRITER_REF, "GITHUB_REF", "refs/heads/so", True),
        (WRITER_REF, "GITHUB_REF", "refs/heads/main", False),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "push", True),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "workflow_dispatch", True),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "schedule", True),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "pull_request", False),
        (WRITER_EVENT, "GITHUB_EVENT_NAME", "unexpected", False),
    ):
        result = subprocess.run(["bash", "-e", "-c", script],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                capture_output=True, check=False)
        require((result.returncode == 0) == allowed, "release baseline branch/event runtime drift")
    for predicate, variable in ((PR_SHA, "expected"), (WRITER_SHA, "GITHUB_SHA")):
        for value, allowed in (("a" * 40, True), ("0" * 40, True), ("A" * 40, False),
                               ("g" * 40, False), ("a" * 39, False), ("a" * 41, False), ("", False)):
            result = subprocess.run(["bash", "-e", "-c", predicate],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), variable: value},
                                    capture_output=True, check=False)
            require((result.returncode == 0) == allowed, "release baseline SHA runtime drift")
    print("PASS: release baseline branch/event/SHA runtime (23 cases)")


def main() -> int:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    validate(publisher, independent)
    negatives(publisher, independent)
    runtime()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
