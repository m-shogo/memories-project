#!/usr/bin/env python3
"""Fail-closed source/permission admission for derived operability inventory writer."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/operability-admission-inventory.yml"
INDEPENDENT = ".github/workflows/operability-admission-inventory-source-negative.yml"
SELF = "scripts/validate-memory-os-operability-admission-inventory-workflow-negative.py"
REVIEWED_PUBLISHER = "3b8bfd146bdbbafebc92e9941870b2007c51a3af"
REVIEWED_INDEPENDENT = "1cc32e55bcfca0d8d1d2be6f4d4222260a327123"
D = chr(36)
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
PUBLISHER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
CAPTURE = "      - name: Capture exact inventory source\n"
MAIN_REQUIRED = (
    ("push branch", "  push:\n    branches:\n      - so\n    paths:\n", 1),
    ("dispatch", "  workflow_dispatch:\n", 1),
    ("script trigger", '      - "' + SELF + '"\n', 1),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 1),
    ("checkout SHA", CHECKOUT, 1),
    ("setup SHA", SETUP, 1),
    ("writer credentials", "          persist-credentials: true\n", 1),
    ("writer branch", PUSH_REF, 1),
    ("writer event", EVENT, 1),
    ("SHA format", SHA_FORMAT, 1),
    ("publisher scope", PUBLISHER_SCOPE, 1),
    ("writer self execution", "\n          python " + SELF + "\n", 1),
    ("retry self execution", "\n            python " + SELF + "\n", 1),
    ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', 1),
    ("writer SHA source", 'expected="' + D + '{GITHUB_SHA:-}"', 1),
    ("latest reset", "            git reset --hard origin/so\n", 1),
    ("capture step", CAPTURE, 1),
    ("root read token", "permissions:\n  contents: read\n", 1),
    ("writer write token", "      contents: write\n", 1),
)
INDEPENDENT_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("publisher trigger", '      - "' + PUBLISHER + '"\n', 2),
    ("self trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("script trigger", '      - "' + SELF + '"\n', 2),
    ("checkout SHA", CHECKOUT, 1),
    ("setup SHA", SETUP, 1),
    ("no credentials", "          persist-credentials: false\n", 1),
    ("PR base", PR_BASE, 1),
    ("push branch", PUSH_REF, 1),
    ("SHA format", SHA_FORMAT, 1),
    ("self execution", "          python " + SELF + "\n", 1),
    ("read token", "  contents: read\n", 2),
    ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", 1),
    ("clean source", '          test -z "$(git status --porcelain)"\n', 2),
)


def source(relative: str) -> str:
    path = ROOT / relative
    try:
        if not path.is_file() or path.is_symlink():
            raise ValueError("not regular")
        if path.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() != relative:
            raise ValueError("escaped root")
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        raise SystemExit("operability inventory CI source missing or substituted: " + relative) from exc


def validate(publisher: str, independent: str) -> None:
    for name, content, required, digest in (
        ("publisher", publisher, MAIN_REQUIRED, REVIEWED_PUBLISHER),
        ("independent", independent, INDEPENDENT_REQUIRED, REVIEWED_INDEPENDENT),
    ):
        for label, token, count in required:
            if content.count(token) != count:
                raise SystemExit("operability inventory " + name + " source drift: " + label)
        data = content.encode("utf-8")
        blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        if hashlib.sha1(blob).hexdigest() != digest:
            raise SystemExit("operability inventory " + name + " complete source drift")


def runtime(publisher: str, independent: str) -> None:
    for name, content, cases in (
        ("publisher", publisher, (
            ("push so", PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
            ("push main", PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
            ("push tag", PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
        )),
        ("independent", independent, (
            ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
            ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
            ("PR absent", PR_BASE, "GITHUB_BASE_REF", "", False),
            ("push so", PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
            ("push main", PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
            ("push tag", PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
        )),
    ):
        for label, command, key, value, allow in cases:
            if content.count(command) != 1:
                raise SystemExit("operability inventory " + name + " runtime command missing: " + label)
            result = subprocess.run(["bash", "-e", "-c", command],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                    capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("operability inventory " + name + " runtime branch drift: " + label)
    for event, allow in (("push", True), ("workflow_dispatch", True), ("pull_request", False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", EVENT],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("operability inventory writer event runtime drift: " + event)
    print("PASS: operability inventory writer/independent branch runtime (9 cases), writer event runtime (4 cases)")


def negatives(publisher: str, independent: str) -> None:
    publisher_cases = (
        ("push target", "  push:\n    branches:\n      - so\n", "  push:\n"),
        ("dispatch", "  workflow_dispatch:\n", ""),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("writer credentials", "          persist-credentials: true\n", ""),
        ("writer branch", PUSH_REF, ""),
        ("writer event", EVENT, ""),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("broad publisher scope", PUBLISHER_SCOPE, "    if: always()\n"),
        ("writer self guard", "\n          python " + SELF + "\n", ""),
        ("retry self guard", "\n            python " + SELF + "\n", ""),
        ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', "true"),
        ("writer SHA source", 'expected="' + D + '{GITHUB_SHA:-}"', 'expected="$PR_HEAD_SHA"'),
        ("latest reset", "            git reset --hard origin/so\n", ""),
        ("root write token", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("writer token removed", "      contents: write\n", "      contents: read\n"),
        ("capture step removed", CAPTURE, ""),
        ("unreviewed Action", CAPTURE, "      - uses: unreviewed/action@v1\n" + CAPTURE),
        ("unreviewed shell", CAPTURE, "      - run: echo unreviewed\n" + CAPTURE),
    )
    independent_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("publisher trigger", '      - "' + PUBLISHER + '"\n', ""),
        ("self trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("persist credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("PR base", PR_BASE, ""),
        ("push branch", PUSH_REF, ""),
        ("event scope", "    if: github.event_name == 'pull_request' || (github.event_name == 'push' && github.ref == 'refs/heads/so')\n", "    if: always()\n"),
        ("self execution", "          python " + SELF + "\n", ""),
        ("injected Action", "      - name: Prove inventory source admission\n", "      - uses: unreviewed/action@v1\n      - name: Prove inventory source admission\n"),
        ("injected shell", "      - name: Prove inventory source admission\n", "      - run: echo unreviewed\n      - name: Prove inventory source admission\n"),
    )
    for target, cases in (("publisher", publisher_cases), ("independent", independent_cases)):
        for label, old, new in cases:
            original = publisher if target == "publisher" else independent
            if old not in original:
                raise SystemExit("operability inventory negative fixture missing: " + target + " " + label)
            mutated = original.replace(old, new, 1)
            if mutated == original:
                raise SystemExit("operability inventory negative fixture unchanged: " + target + " " + label)
            try:
                validate(mutated, independent) if target == "publisher" else validate(publisher, mutated)
            except SystemExit:
                continue
            raise SystemExit("operability inventory accepted source mutation: " + target + " " + label)
    print(f"PASS: operability inventory publisher source admission ({len(publisher_cases)} negatives), independent source admission ({len(independent_cases)} negatives)")


def main() -> int:
    publisher = source(PUBLISHER)
    independent = source(INDEPENDENT)
    validate(publisher, independent)
    runtime(publisher, independent)
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
