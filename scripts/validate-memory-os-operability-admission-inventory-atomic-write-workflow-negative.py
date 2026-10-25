#!/usr/bin/env python3
"""Independent complete-source and runtime admission for atomic-write inventory CI."""
from __future__ import annotations
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ".github/workflows/operability-admission-inventory-atomic-write-negative.yml"
GUARD = ".github/workflows/operability-admission-inventory-atomic-write-source-negative.yml"
SELF = "scripts/validate-memory-os-operability-admission-inventory-atomic-write-workflow-negative.py"
MAIN_BLOB = "7e6bf84e53d7406eb345e0835d1d7f346474dc89"
GUARD_BLOB = "53354e802a173c637e227818b8da4501918b6c55"
D = chr(36)
BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
SHA = '[[ "' + D + 'expected" =~ ^[0-9a-f]{40}$ ]]'
HEAD = 'test "$(git rev-parse HEAD)" = "$expected"'
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"

def read(path: str) -> str:
    target = ROOT / path
    try:
        if target.is_symlink() or not target.is_file():
            raise ValueError("not a regular source file")
        if target.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != path:
            raise ValueError("source path escapes repository")
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeError, RuntimeError, ValueError) as exc:
        raise SystemExit("atomic-write CI source unavailable: " + path) from exc

def validate(main: str, guard: str) -> None:
    common = ((CHECKOUT, 1), (SETUP, 1), (BASE, 1), (REF, 1), (SHA, 1),
              (HEAD, 1), ("          persist-credentials: false\n", 1),
              ("          python " + SELF + "\n", 1),
              ('          test -z "$(git status --porcelain)"\n', 2),
              ("    permissions:\n      contents: read\n", 1))
    main_checks = common + (
        ("  pull_request:\n    branches: [so]\n", 1),
        ("  push:\n    branches:\n      - so\n", 1),
        ("  workflow_dispatch:\n", 1),
        ("  contents: read\n", 2),
        ("      - \"" + GUARD + "\"\n", 2),
        ("      - \"" + SELF + "\"\n", 2),
        ("          PR_HEAD_SHA: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
        ("          ref: " + D + "{{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
        ("    if: github.event_name == 'pull_request' || ((github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so')\n", 1),
    )
    guard_checks = common + (
        ("  pull_request:\n    branches: [so]\n", 1),
        ("  push:\n    branches: [so]\n", 1),
        ("  contents: read\n", 2),
        ("      - \"" + MAIN + "\"\n", 2),
        ("      - \"" + GUARD + "\"\n", 2),
        ("      - \"" + SELF + "\"\n", 2),
        ("          PR_HEAD_SHA: " + D + "{{ github.event.pull_request.head.sha }}\n", 1),
        ("          ref: " + D + "{{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n", 1),
        ("    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    )
    for label, content, expected_blob, checks in (
        ("atomic publisher", main, MAIN_BLOB, main_checks),
        ("atomic independent", guard, GUARD_BLOB, guard_checks),
    ):
        for token, count in checks:
            if content.count(token) != count:
                raise SystemExit(label + " anchor drift: " + repr(token[:75]))
        payload = content.encode("utf-8")
        git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
        if hashlib.sha1(git_blob).hexdigest() != expected_blob:
            raise SystemExit(label + " complete source drift")

def runtime(main: str, guard: str) -> None:
    for label, source in (("publisher", main), ("independent", guard)):
        for token in (BASE, REF, SHA, HEAD):
            if source.count(token) != 1:
                raise SystemExit("atomic runtime predicate unreachable: " + label)
        for key, command, values in (
            ("GITHUB_BASE_REF", BASE, (("so", True), ("main", False), ("", False))),
            ("GITHUB_REF", REF, (("refs/heads/so", True), ("refs/heads/main", False), ("refs/tags/v1", False), ("", False))),
        ):
            for value, allowed in values:
                p = subprocess.run(["bash", "-e", "-c", command], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value}, capture_output=True, check=False)
                if (p.returncode == 0) != allowed:
                    raise SystemExit("atomic branch predicate drift: " + label + " " + key)
        for value, allowed in (("a" * 40, True), ("0" * 40, True), ("a" * 39, False), ("A" * 40, False), ("g" * 40, False), ("", False), ("$(echo bypass)", False)):
            script = 'expected="' + D + '{PROBE_SHA:-}"\n' + SHA
            p = subprocess.run(["bash", "-e", "-c", script], env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PROBE_SHA": value}, capture_output=True, check=False)
            if (p.returncode == 0) != allowed:
                raise SystemExit("atomic SHA predicate drift: " + label)
    print("PASS: atomic source runtime branch (14) and SHA (14) cases")

def negatives(main: str, guard: str) -> None:
    cases = (
        ("main", CHECKOUT, "uses: actions/checkout@v4"),
        ("main", SETUP, "uses: actions/setup-python@v5"),
        ("main", BASE, "true"),
        ("main", REF, "true"),
        ("main", SHA, 'test -n "$expected"'),
        ("main", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("main", "  workflow_dispatch:\n", ""),
        ("main", "  pull_request:\n    branches: [so]\n", "  pull_request:\n"),
        ("main", "          python " + SELF + "\n", "          true\n"),
        ("main", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("guard", CHECKOUT, "uses: actions/checkout@v4"),
        ("guard", SETUP, "uses: actions/setup-python@v5"),
        ("guard", BASE, "true"),
        ("guard", REF, "true"),
        ("guard", SHA, 'test -n "$expected"'),
        ("guard", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("guard", "  pull_request:\n    branches: [so]\n", "  pull_request:\n"),
        ("guard", "          python " + SELF + "\n", "          true\n"),
        ("guard", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("guard", '          PR_HEAD_SHA: ' + D + '{{ github.event.pull_request.head.sha }}\n', '          PR_HEAD_SHA: ' + D + '{{ github.sha }}\n'),
    )
    for label, old, new in cases:
        source = main if label == "main" else guard
        if source.count(old) != 1:
            raise SystemExit("atomic negative fixture ambiguous: " + label + " " + old[:60])
        mutated = source.replace(old, new, 1)
        if mutated == source:
            raise SystemExit("atomic negative unchanged: " + label)
        try:
            validate(mutated, guard) if label == "main" else validate(main, mutated)
        except SystemExit:
            continue
        raise SystemExit("atomic source accepted negative: " + label)
    print("PASS: atomic source 20 negative mutations")

def main() -> int:
    main_source, guard_source = read(MAIN), read(GUARD)
    validate(main_source, guard_source)
    runtime(main_source, guard_source)
    negatives(main_source, guard_source)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
