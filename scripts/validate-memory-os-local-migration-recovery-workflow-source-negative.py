#!/usr/bin/env python3
"""Read-only exact-source and runtime negative proof for local migration recovery CI."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/local-migration-recovery-artifact.yml"
INDEPENDENT = ".github/workflows/local-migration-recovery-source-negative.yml"
SELF = "scripts/validate-memory-os-local-migration-recovery-workflow-source-negative.py"
PUBLISHER_SHA = "b41c62ea91abd8539a8154968e15403e8e99371d"
INDEPENDENT_SHA = "094d794db2d11846a4a174ac7ab976b4f81e304a"
LOCAL_NEGATIVE = "scripts/validate-memory-os-local-migration-recovery-artifact-reconcile-negative.py"
LOCAL_NEGATIVE_SHA = "a718111cfe880860c96d7784afdab2dd61fb9495"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
WRITER_SCOPE = "    if: >-\n      (github.event_name == 'push' || github.event_name == 'workflow_dispatch') &&\n      github.ref == 'refs/heads/so' &&\n      (github.event_name != 'push' ||\n       (!contains(github.event.head_commit.message, 'test(migration): record local recovery artifact rehearsal') &&\n        !contains(github.event.head_commit.message, 'docs(migration): register local recovery artifact rehearsal')))"
PR_BASE = 'test "${GITHUB_BASE_REF:-}" = "so"'
WRITER_REF = 'test "${GITHUB_REF:-}" = "refs/heads/so"'
PR_SHA = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
WRITER_SHA = '[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]'


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("local migration recovery CI source guard: " + message)


def read(path: str) -> str:
    file = ROOT / path
    require(file.is_file() and not file.is_symlink(), "missing or symlinked source: " + path)
    require(file.resolve(strict=True).relative_to(ROOT.resolve(strict=True)).as_posix() == path,
            "source escaped root: " + path)
    return file.read_text(encoding="utf-8")


def check_source(name: str, source: str, expected: str, required: tuple[tuple[str, int], ...]) -> None:
    for token, count in required:
        require(source.count(token) == count, name + " required source inventory drift: " + token[:55])
    for forbidden in ("pull_request_target:", "secrets.", "actions/checkout@v4", "actions/setup-python@v5"):
        require(forbidden not in source, name + " unreviewed source")
    data = source.encode("utf-8")
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    require(digest == expected, name + " complete Git blob drift")


PUBLISHER_REQUIRED = (
    ("  pull_request:\n    branches:\n      - so\n", 1),
    ("  push:\n    branches:\n      - so\n", 1),
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
    (PR_SHA, 1),
    (WRITER_SHA, 1),
    ("ref: so", 1),
    ("'output': 'REDACTED: local migration recovery failed; raw output withheld'", 1),
    ("raw log suppressed", 1),
    ('cat "$log"', 0),
    ("text[-10000:]", 0),
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
    ('      - "' + LOCAL_NEGATIVE + '"\n', 2),
    ('      - "scripts/reconcile-memory-os-local-migration-recovery-artifact.py"\n', 2),
    (CHECKOUT, 1),
    (SETUP, 1),
    ("persist-credentials: false", 1),
    (PR_BASE, 1),
    (WRITER_REF, 1),
    (PR_SHA, 1),
    ("python " + SELF, 1),
    ("python " + LOCAL_NEGATIVE, 1),
    ('git clone --no-hardlinks --no-checkout . "$temp/repo"', 1),
    ('git -C "$temp/repo" checkout --detach "$(git rev-parse HEAD)"', 1),
    ('test -z "$(git -C "$temp/repo" status --porcelain)"', 2),
    ("permissions:\n  contents: read\n", 1),
    ("      contents: read\n", 1),
)


def validate(publisher: str, independent: str) -> None:
    check_source("publisher", publisher, PUBLISHER_SHA, PUBLISHER_REQUIRED)
    check_source("independent", independent, INDEPENDENT_SHA, INDEPENDENT_REQUIRED)
    check_source("local reconcile negative", read(LOCAL_NEGATIVE), LOCAL_NEGATIVE_SHA, ())


def negative_proofs(publisher: str, independent: str) -> None:
    cases = (
        ("publisher PR base", True, PR_BASE, "true"),
        ("publisher writer ref", True, WRITER_REF, "true"),
        ("publisher writer scope", True, WRITER_SCOPE, "    if: always()"),
        ("publisher PR SHA", True, PR_SHA, 'test -n "$expected"'),
        ("publisher writer SHA", True, WRITER_SHA, 'test -n "$GITHUB_SHA"'),
        ("publisher checkout pin", True, CHECKOUT, "uses: actions/checkout@v4"),
        ("publisher setup pin", True, SETUP, "uses: actions/setup-python@v5"),
        ("publisher event scope", True, "  workflow_dispatch:\n", "  pull_request_target:\n"),
        ("publisher digest-only drift", True, "\n", "\n# unauthorized publisher source drift\n"),
        ("publisher credentials", True, "persist-credentials: false", "persist-credentials: true"),
        ("publisher self guard", True, "python " + SELF, "echo skip"),
        ("publisher checkout ref", True, "ref: so", "ref: main"),
        ("publisher redaction", True, "'output': 'REDACTED: local migration recovery failed; raw output withheld'", "'output': text[-10000:]"),
        ("publisher log suppression", True, "raw log suppressed", "raw log exposed"),
        ("independent PR base", False, PR_BASE, "true"),
        ("independent writer ref", False, WRITER_REF, "true"),
        ("independent SHA", False, PR_SHA, 'test -n "$expected"'),
        ("independent checkout pin", False, CHECKOUT, "uses: actions/checkout@v4"),
        ("independent setup pin", False, SETUP, "uses: actions/setup-python@v5"),
        ("independent event scope", False, "  push:\n    branches:\n      - so\n", "  workflow_dispatch:\n"),
        ("independent digest-only drift", False, "\n", "\n# unauthorized independent source drift\n"),
        ("independent credentials", False, "persist-credentials: false", "persist-credentials: true"),
        ("independent self guard", False, "python " + SELF, "echo skip"),
        ("independent local negative invocation", False, "python " + LOCAL_NEGATIVE, "echo skip"),
        ("independent clone exact checkout", False, 'git -C "$temp/repo" checkout --detach "$(git rev-parse HEAD)"', 'git -C "$temp/repo" checkout so'),
        ("independent clone cleanliness", False, 'test -z "$(git -C "$temp/repo" status --porcelain)"', "true"),
    )
    for label, publisher_case, before, after in cases:
        original = publisher if publisher_case else independent
        require(before in original, "mutation anchor missing: " + label)
        changed = original.replace(before, after, 1)
        require(changed != original, "mutation unchanged: " + label)
        try:
            validate(changed, independent) if publisher_case else validate(publisher, changed)
        except SystemExit as exc:
            # Require the actual source guard to reject for the expected reason.
            expected = ("complete Git blob drift" if "digest-only" in label
                        else "required source inventory drift")
            reason = str(exc)
            require(reason.startswith("local migration recovery CI source guard: ")
                    and expected in reason,
                    "negative rejected for wrong reason: " + label + ": " + reason)
            continue
        raise SystemExit("local migration recovery source negative accepted: " + label)
    suite = read(LOCAL_NEGATIVE)
    try:
        check_source("local reconcile negative", suite + "\n# unauthorized local negative suite drift\n",
                     LOCAL_NEGATIVE_SHA, ())
    except SystemExit as exc:
        require("local reconcile negative complete Git blob drift" in str(exc),
                "local negative suite mutation rejected for wrong reason")
    else:
        raise SystemExit("local negative suite complete source drift accepted")
    print(f"PASS: local migration recovery CI source negatives ({len(cases) + 1} cases)")


def runtime_proofs() -> None:
    for label, script, key, value, expected in (
        ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
        ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
        ("writer so", WRITER_REF, "GITHUB_REF", "refs/heads/so", True),
        ("writer main", WRITER_REF, "GITHUB_REF", "refs/heads/main", False),
    ):
        result = subprocess.run(["bash", "-e", "-c", script],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                capture_output=True, check=False)
        require((result.returncode == 0) == expected, "runtime branch drift: " + label)
    for predicate, variable in ((PR_SHA, "expected"), (WRITER_SHA, "GITHUB_SHA")):
        for value, allowed in (("a" * 40, True), ("0" * 40, True), ("A" * 40, False),
                               ("g" * 40, False), ("a" * 39, False), ("a" * 41, False), ("", False)):
            result = subprocess.run(["bash", "-e", "-c", predicate],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), variable: value},
                                    capture_output=True, check=False)
            require((result.returncode == 0) == allowed, "runtime SHA drift")
    print("PASS: local migration recovery branch/SHA runtime (18 cases)")


def main() -> int:
    publisher, independent = read(PUBLISHER), read(INDEPENDENT)
    validate(publisher, independent)
    negative_proofs(publisher, independent)
    runtime_proofs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
