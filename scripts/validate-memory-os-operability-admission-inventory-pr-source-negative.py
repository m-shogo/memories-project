#!/usr/bin/env python3
"""Independent full-source and runtime negative guard for inventory PR validation."""
from __future__ import annotations
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PR = ".github/workflows/operability-admission-inventory-pr.yml"
GUARD = ".github/workflows/operability-admission-inventory-pr-source-negative.yml"
SELF = "scripts/validate-memory-os-operability-admission-inventory-pr-source-negative.py"
PR_BLOB = "def6b2891a2c6f6ccda57dece11190ceb19b3cbf"
GUARD_BLOB = "457095582ad5f5c2be7c63f0124a4e1721b78c3d"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
D = chr(36)
BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
EVENT = 'test "' + D + '{GITHUB_EVENT_NAME:-}" = "pull_request"'
SHA = '[[ "' + D + 'expected" =~ ^[0-9a-f]{40}' + D + ' ]]'
HEAD = 'test "$(git rev-parse HEAD)" = "$expected"'


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if path.is_symlink() or not path.is_file():
            raise ValueError("not a regular file")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped repository")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        raise SystemExit("inventory PR source unavailable: " + relative) from exc


def validate(pr: str, guard: str) -> None:
    checks = (
        ("PR", pr, PR_BLOB, (
            (CHECKOUT, 1), (SETUP, 1), ("  pull_request:\n    branches:\n      - so\n", 1),
            ("    if: github.event_name == 'pull_request' && github.base_ref == 'so'\n", 1),
            ("permissions:\n  contents: read\n", 1), ("    permissions:\n      contents: read\n", 1),
            ("          persist-credentials: false\n", 1),
            ("          ref: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
            ("          PR_HEAD_SHA: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
            (EVENT, 1), (BASE, 1), (SHA, 1), (HEAD, 1),
            ("          python " + SELF + "\n", 1),
            ('          test -z "$(git status --porcelain)"\n', 2),
            ('      - "' + GUARD + '"\n', 1),
            ('      - "' + SELF + '"\n', 1),
        )),
        ("independent", guard, GUARD_BLOB, (
            (CHECKOUT, 1), (SETUP, 1), ("  pull_request:\n    branches: [so]\n", 1),
            ("  push:\n    branches: [so]\n", 1),
            ("permissions:\n  contents: read\n", 1), ("    permissions:\n      contents: read\n", 1),
            ("          persist-credentials: false\n", 1),
            ("          ref: " + D + "{{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
            ("          PR_HEAD_SHA: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
            (BASE, 1), (SHA, 1), (HEAD, 1),
            ('test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"', 1),
            ("    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
            ("          python " + SELF + "\n", 1),
            ('      - "' + PR + '"\n', 2), ('      - "' + GUARD + '"\n', 2), ('      - "' + SELF + '"\n', 2),
            ('          test -z "$(git status --porcelain)"\n', 2),
        )),
    )
    for label, content, expected, anchors in checks:
        for token, count in anchors:
            if content.count(token) != count:
                raise SystemExit("inventory PR " + label + " anchor drift: " + repr(token[:80]))
        data = content.encode("utf-8")
        blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        if hashlib.sha1(blob).hexdigest() != expected:
            raise SystemExit("inventory PR " + label + " complete source drift")


def runtime() -> None:
    cases = (
        (EVENT, "GITHUB_EVENT_NAME", (("pull_request", True), ("push", False), ("", False))),
        (BASE, "GITHUB_BASE_REF", (("so", True), ("main", False), ("", False))),
    )
    for command, key, values in cases:
        for value, allow in values:
            result = subprocess.run(["bash", "-e", "-c", command],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                    capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("inventory PR runtime event/base drift: " + key + " " + value)
    for value, allow in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False),
                         ("A" * 40, False), ("g" * 40, False), ("", False)):
        command = 'expected="' + D + '{PROBE_SHA:-}"\n' + SHA
        result = subprocess.run(["bash", "-e", "-c", command],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("inventory PR runtime SHA drift: " + value)
    print("PASS: inventory PR runtime event/base (6) and SHA (6) cases")


def negatives(pr: str, guard: str) -> None:
    cases = (
        ("PR", CHECKOUT, "uses: actions/checkout@v4"),
        ("PR", SETUP, "uses: actions/setup-python@v5"),
        ("PR", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("PR", EVENT, "true"), ("PR", BASE, "true"),
        ("PR", SHA, 'test -n "$expected"'),
        ("PR", HEAD, "true"),
        ("PR", "          python " + SELF + "\n", "          true\n"),
        ("PR", "    if: github.event_name == 'pull_request' && github.base_ref == 'so'\n", "    if: always()\n"),
        ("PR", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("independent", CHECKOUT, "uses: actions/checkout@v4"),
        ("independent", SETUP, "uses: actions/setup-python@v5"),
        ("independent", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("independent", "  pull_request:\n    branches: [so]\n", "  pull_request:\n"),
        ("independent", BASE, "true"), ("independent", SHA, 'test -n "$expected"'),
        ("independent", HEAD, "true"),
        ("independent", "          python " + SELF + "\n", "          true\n"),
        ("independent", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
    )
    for label, old, new in cases:
        original = pr if label == "PR" else guard
        if original.count(old) != 1:
            raise SystemExit("inventory PR negative fixture ambiguous: " + label + " " + old[:60])
        mutated = original.replace(old, new, 1)
        try:
            validate(mutated, guard) if label == "PR" else validate(pr, mutated)
        except SystemExit:
            continue
        raise SystemExit("inventory PR accepted source mutation: " + label)
    print("PASS: inventory PR source negative mutations (20 cases)")


def main() -> int:
    pr, guard = source(PR), source(GUARD)
    validate(pr, guard)
    runtime()
    negatives(pr, guard)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
