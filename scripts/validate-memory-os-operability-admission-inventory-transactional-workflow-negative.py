#!/usr/bin/env python3
"""Independent immutable workflow and runtime boundary proof for transactional inventory."""

from __future__ import annotations
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ".github/workflows/operability-admission-inventory-transactional.yml"
GUARD = ".github/workflows/operability-admission-inventory-transactional-source-negative.yml"
SELF = "scripts/validate-memory-os-operability-admission-inventory-transactional-workflow-negative.py"
MAIN_BLOB = "8a829f858b451d39355c584a31ba762d53ccdf4e"
GUARD_BLOB = "66252d5fbfb205460335772534898aa02e39fe81"
D = chr(36)
REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA = '[[ "' + D + '{GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'
BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
PR_SHA = '[[ "' + D + 'expected" =~ ^[0-9a-f]{40}$ ]]'
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"


def source(path: str) -> str:
    target = ROOT / path
    try:
        if target.is_symlink() or not target.is_file():
            raise ValueError("not a regular source")
        if target.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
            raise ValueError("source path escapes repository")
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
        raise SystemExit("transactional source unavailable: " + path) from exc


def validate(main: str, guard: str) -> None:
    for label, content, blob, checks in (
        ("publisher", main, MAIN_BLOB, (
            (CHECKOUT, 1), (SETUP, 1), (REF, 1), (EVENT, 1), (SHA, 1),
            ("          persist-credentials: false\n", 1),
            ("    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n", 1),
            ("          python " + SELF + "\n", 1),
            ('      - "' + GUARD + '"\n', 1),
            ('      - "' + SELF + '"\n', 1),
            ("permissions:\n  contents: read\n", 1),
            ('test "$(git rev-parse HEAD)" = "$GITHUB_SHA"', 1),
        )),
        ("independent", guard, GUARD_BLOB, (
            (CHECKOUT, 1), (SETUP, 1), (BASE, 1), (REF, 1), (PR_SHA, 1),
            ("          persist-credentials: false\n", 1),
            ("    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
            ("  contents: read\n", 2),
            ("          python " + SELF + "\n", 1),
            ('      - "' + MAIN + '"\n', 2),
            ('      - "' + GUARD + '"\n', 2),
            ('      - "' + SELF + '"\n', 2),
        )),
    ):
        for token, count in checks:
            if content.count(token) != count:
                raise SystemExit("transactional " + label + " anchor drift: " + token[:70])
        payload = content.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != blob:
            raise SystemExit("transactional " + label + " complete source drift")


def runtime(main: str, guard: str) -> None:
    for label, content in (("publisher", main), ("independent", guard)):
        if content.count(REF) != 1:
            raise SystemExit("transactional ref predicate unreachable: " + label)
        for value, allowed in (("refs/heads/so", True), ("refs/heads/main", False), ("refs/tags/v1", False), ("", False)):
            p = subprocess.run(["bash", "-e", "-c", REF], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_REF": value}, capture_output=True, check=False)
            if (p.returncode == 0) != allowed:
                raise SystemExit("transactional ref predicate drift: " + label)
    for event, allowed in (("push", True), ("workflow_dispatch", True), ("pull_request", False), ("", False)):
        p = subprocess.run(["bash", "-e", "-c", EVENT], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event}, capture_output=True, check=False)
        if (p.returncode == 0) != allowed:
            raise SystemExit("transactional event predicate drift")
    for sha, allowed in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False), ("A" * 40, False), ("g" * 40, False), ("", False)):
        p = subprocess.run(["bash", "-e", "-c", SHA], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_SHA": sha}, capture_output=True, check=False)
        if (p.returncode == 0) != allowed:
            raise SystemExit("transactional SHA predicate drift")
    if guard.count(BASE) != 1 or guard.count(PR_SHA) != 1:
        raise SystemExit("transactional independent PR predicates unreachable")
    for value, allowed in (("so", True), ("main", False), ("", False)):
        p = subprocess.run(["bash", "-e", "-c", BASE], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_BASE_REF": value}, capture_output=True, check=False)
        if (p.returncode == 0) != allowed:
            raise SystemExit("transactional independent PR base predicate drift")
    for value, allowed in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False), ("A" * 40, False), ("g" * 40, False), ("", False)):
        script = 'expected="${PROBE_SHA:-}"' + chr(10) + PR_SHA
        p = subprocess.run(["bash", "-e", "-c", script], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}, capture_output=True, check=False)
        if (p.returncode == 0) != allowed:
            raise SystemExit("transactional independent PR SHA predicate drift")
    print("PASS: transactional source branch (8), event (4), SHA (12), PR base (3) runtime cases")


def negatives(main: str, guard: str) -> None:
    cases = (
        ("publisher", main, CHECKOUT, "uses: actions/checkout@v4"),
        ("publisher", main, SETUP, "uses: actions/setup-python@v5"),
        ("publisher", main, REF, "true"),
        ("publisher", main, EVENT, "true"),
        ("publisher", main, SHA, 'test -n "$GITHUB_SHA"'),
        ("publisher", main, "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("publisher", main, "          python " + SELF + "\n", "          true\n"),
        ("publisher", main, "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("independent", guard, CHECKOUT, "uses: actions/checkout@v4"),
        ("independent", guard, SETUP, "uses: actions/setup-python@v5"),
        ("independent", guard, BASE, "true"),
        ("independent", guard, PR_SHA, 'test -n "$expected"'),
        ("independent", guard, 'PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}', 'PR_HEAD_SHA: ${{ github.sha }}'),
        ("independent", guard, REF, "true"),
        ("independent", guard, "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("independent", guard, "          python " + SELF + "\n", "          true\n"),
        ("independent", guard, "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
    )
    for label, content, old, new in cases:
        if old not in content:
            raise SystemExit("transactional negative fixture missing: " + label + " " + old[:40])
        mutated = content.replace(old, new, 1)
        try:
            validate(mutated, guard) if label == "publisher" else validate(main, mutated)
        except SystemExit:
            continue
        raise SystemExit("transactional source accepted mutation: " + label)
    print("PASS: transactional source 17 negative mutations")


def main() -> int:
    main_content, guard_content = source(MAIN), source(GUARD)
    validate(main_content, guard_content)
    runtime(main_content, guard_content)
    negatives(main_content, guard_content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
