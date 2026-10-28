#!/usr/bin/env python3
"""Fail closed on unreviewed restore-policy publisher or independent CI source."""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ".github/workflows/reconcile-backup-restore.yml"
INDEPENDENT = ".github/workflows/reconcile-backup-restore-source-negative.yml"
SELF = "scripts/validate-memory-os-reconcile-backup-restore-workflow-negative.py"

PUBLISHER_TRIGGER_PATHS = (
    ".github/workflows/reconcile-backup-restore.yml",
    "contracts/operations/backup-restore-contract.v1.json",
    "contracts/operations/local-logical-restore-contract.v1.json",
    "contracts/operations/local-object-version-restore-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "docs/runbooks/memory-os-backup-restore.md",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/validate-memory-os-backup-restore.py",
    "scripts/validate-memory-os-backup-restore-reconcile-negative.py",
    "scripts/reconcile-memory-os-backup-restore.py",
    "scripts/validate-memory-os-local-logical-restore.py",
    "scripts/validate-memory-os-local-object-version-restore.py",
    "scripts/validate-memory-os-operability.py",
    "scripts/validate-memory-os-entry-docs.py",
    ".github/workflows/reconcile-backup-restore-source-negative.yml",
    "scripts/validate-memory-os-reconcile-backup-restore-workflow-negative.py",
)
INDEPENDENT_TRIGGER_PATHS = (
    ".github/workflows/reconcile-backup-restore.yml",
    ".github/workflows/reconcile-backup-restore-source-negative.yml",
    "scripts/validate-memory-os-reconcile-backup-restore-workflow-negative.py",
)
REVIEWED_PUBLISHER = "555fa8cc639b18db691481f1b95fed879e280de4"
REVIEWED_INDEPENDENT = "f85ac3ffc1d2c3dc3db34189b23de5a68441d10a"
D = chr(36)
PR_BASE = 'test "' + D + '{GITHUB_BASE_REF:-}" = "so"'
PUSH_REF = 'test "' + D + '{GITHUB_REF:-}" = "refs/heads/so"'
EVENT = '[[ "' + D + '{GITHUB_EVENT_NAME:-}" == "push" || "' + D + '{GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]'
SHA_FORMAT = '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'
PUBLISHER_SCOPE = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n"
CHECKOUT = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
MAIN_REQUIRED = (
    ("PR target", "  pull_request:\n    branches:\n      - so\n    paths:\n", 1),
    ("script trigger", '      - "' + SELF + '"\n', 2),
    ("independent trigger", '      - "' + INDEPENDENT + '"\n', 2),
    ("checkout SHA", CHECKOUT, 2),
    ("setup SHA", SETUP, 2),
    ("PR no credentials", "          persist-credentials: false\n", 1),
    ("writer credentials", "          persist-credentials: true\n", 1),
    ("PR base", PR_BASE, 1),
    ("writer branch", PUSH_REF, 1),
    ("writer event", EVENT, 1),
    ("SHA format", SHA_FORMAT, 2),
    ("publisher scope", PUBLISHER_SCOPE, 1),
    ("PR/writer self execution", "\n          python " + SELF + "\n", 2),
    ("retry self execution", "\n            python " + SELF + "\n", 1),
    ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', 2),
    ("latest reset", "            git reset --hard origin/so\n", 1),
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
        raise SystemExit("restore policy CI source missing or substituted: " + relative) from exc



def validate_trigger_reachability(
    content: str, kind: str, *, trigger_paths: tuple[str, ...] | None = None
) -> None:
    """Require the full reviewed PR/push restore-policy trigger inventory without SHA."""
    if kind == "publisher":
        canonical = PUBLISHER_TRIGGER_PATHS
        end_marker = "  workflow_dispatch:\n"
    elif kind == "independent":
        canonical = INDEPENDENT_TRIGGER_PATHS
        end_marker = "\npermissions:\n"
    else:
        raise SystemExit("restore policy unrecognized CI trigger kind")
    if trigger_paths is None:
        trigger_paths = canonical
    if len(trigger_paths) != len(canonical) or len(set(trigger_paths)) != len(canonical):
        raise SystemExit("restore policy " + kind + " trigger inventory shortened or duplicated")
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    for marker in (pr_marker, push_marker, end_marker):
        if content.count(marker) != 1:
            raise SystemExit("restore policy " + kind + " CI event marker drift")
    pr = content.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push = content.split(push_marker, 1)[1].split(end_marker, 1)[0]
    approved = tuple('      - "' + path + '"' for path in trigger_paths)
    for event, block in (("pull_request", pr), ("push", push)):
        actual = tuple(
            line for line in block.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
        if actual != approved:
            raise SystemExit("restore policy " + kind + " " + event + " exact trigger inventory drift")


def prove_trigger_reachability_negatives(publisher: str, independent: str) -> None:
    push_marker = "  push:\n    branches:\n      - so\n    paths:\n"
    pr_marker = "  pull_request:\n    branches:\n      - so\n    paths:\n"
    for kind, content, paths in (
        ("publisher", publisher, PUBLISHER_TRIGGER_PATHS),
        ("independent", independent, INDEPENDENT_TRIGGER_PATHS),
    ):
        validate_trigger_reachability(content, kind)
        for event in ("pull_request", "push"):
            for path in paths:
                token = '      - "' + path + '"\n'
                if content.count(token) != 2:
                    raise SystemExit("restore policy " + kind + " mutation anchor drift: " + path)
                if event == "pull_request":
                    mutated = content.replace(token, "", 1)
                else:
                    prefix, suffix = content.split(push_marker, 1)
                    mutated = prefix + push_marker + suffix.replace(token, "", 1)
                try:
                    validate_trigger_reachability(mutated, kind)
                except SystemExit:
                    continue
                raise SystemExit("restore policy " + kind + " accepted missing " + event + " trigger: " + path)
            marker = pr_marker if event == "pull_request" else push_marker
            for label, injected in (
                ("quoted extra", '      - "unreviewed/**"\n'),
                ("quoted duplicate", '      - "' + paths[0] + '"\n'),
                ("unquoted extra", "      - unreviewed/**\n"),
                ("unquoted duplicate", "      - " + paths[0] + "\n"),
            ):
                if content.count(marker) != 1:
                    raise SystemExit("restore policy " + kind + " addition marker drift: " + event)
                mutated = content.replace(marker, marker + injected, 1)
                if mutated == content:
                    raise SystemExit("restore policy " + kind + " addition fixture unchanged")
                try:
                    validate_trigger_reachability(mutated, kind)
                except SystemExit:
                    continue
                raise SystemExit("restore policy " + kind + " accepted " + event + " addition: " + label)
        try:
            validate_trigger_reachability(content, kind, trigger_paths=paths[:-1])
        except SystemExit:
            pass
        else:
            raise SystemExit("restore policy " + kind + " shortened inventory accepted")
    print("PASS: restore policy publisher/independent CI event-specific triggers (38 removals; 16 additions; 2 shortened inventory negatives)")


def validate(
    publisher: str, independent: str, *,
    check_publisher_blob: bool = True, check_independent_blob: bool = True,
) -> None:
    validate_trigger_reachability(publisher, "publisher")
    validate_trigger_reachability(independent, "independent")
    for name, content, required, digest in (
        ("publisher", publisher, MAIN_REQUIRED, REVIEWED_PUBLISHER),
        ("independent", independent, INDEPENDENT_REQUIRED, REVIEWED_INDEPENDENT),
    ):
        for label, token, count in required:
            if content.count(token) != count:
                raise SystemExit("restore policy " + name + " source drift: " + label)
        if (name == "publisher" and check_publisher_blob) or (name == "independent" and check_independent_blob):
            data = content.encode("utf-8")
            blob = b"blob " + str(len(data)).encode("ascii") + b"\0" + data
            if hashlib.sha1(blob).hexdigest() != digest:
                raise SystemExit("restore policy " + name + " complete source drift")


def runtime(publisher: str, independent: str) -> None:
    for name, content in (("publisher", publisher), ("independent", independent)):
        for label, command, key, value, allow in (
            ("PR so", PR_BASE, "GITHUB_BASE_REF", "so", True),
            ("PR main", PR_BASE, "GITHUB_BASE_REF", "main", False),
            ("PR absent", PR_BASE, "GITHUB_BASE_REF", "", False),
            ("push so", PUSH_REF, "GITHUB_REF", "refs/heads/so", True),
            ("push main", PUSH_REF, "GITHUB_REF", "refs/heads/main", False),
            ("push tag", PUSH_REF, "GITHUB_REF", "refs/tags/v1", False),
        ):
            if content.count(command) != 1:
                raise SystemExit("restore policy " + name + " runtime command missing: " + label)
            result = subprocess.run(["bash", "-e", "-c", command],
                                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), key: value},
                                    capture_output=True, check=False)
            if (result.returncode == 0) != allow:
                raise SystemExit("restore policy " + name + " runtime branch drift: " + label)
    for event, allow in (("push", True), ("workflow_dispatch", True), ("pull_request", False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", EVENT],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GITHUB_EVENT_NAME": event},
                                capture_output=True, check=False)
        if (result.returncode == 0) != allow:
            raise SystemExit("restore policy writer event runtime drift: " + event)
    print("PASS: restore policy publisher/independent PR-push branch runtime (12 cases), writer event runtime (4 cases)")


def negatives(publisher: str, independent: str) -> None:
    publisher_cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("script trigger", '      - "' + SELF + '"\n', ""),
        ("independent trigger", '      - "' + INDEPENDENT + '"\n', ""),
        ("floating checkout", CHECKOUT, "uses: actions/checkout@v4"),
        ("floating setup", SETUP, "uses: actions/setup-python@v5"),
        ("PR credentials", "          persist-credentials: false\n", "          persist-credentials: true\n"),
        ("writer credentials", "          persist-credentials: true\n", ""),
        ("PR base", PR_BASE, ""),
        ("writer branch", PUSH_REF, ""),
        ("writer event", EVENT, ""),
        ("SHA format", SHA_FORMAT, 'test -n "$expected"'),
        ("broad publisher scope", PUBLISHER_SCOPE, "    if: github.event_name != 'pull_request'\n"),
        ("PR self guard", "\n          python " + SELF + "\n", ""),
        ("retry self guard", "\n            python " + SELF + "\n", ""),
        ("HEAD identity", 'test "$(git rev-parse HEAD)" = "$expected"', "true"),
        ("latest reset", "            git reset --hard origin/so\n", ""),
        ("root write token", "permissions:\n  contents: read\n", "permissions:\n  contents: write\n"),
        ("writer token removed", "      contents: write\n", "      contents: read\n"),
        ("unreviewed Action", "      - name: Confirm exact source state\n", "      - uses: unreviewed/action@v1\n      - name: Confirm exact source state\n"),
        ("unreviewed shell", "      - name: Confirm exact source state\n", "      - run: echo unreviewed\n      - name: Confirm exact source state\n"),
        ("appended command", '          echo "SOURCE_SHA=$SOURCE_SHA" >> "$GITHUB_ENV"\n', '          echo "SOURCE_SHA=$SOURCE_SHA" >> "$GITHUB_ENV"\n          echo unreviewed\n'),
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
        ("injected Action", "      - name: Prove restore policy source admission\n", "      - uses: unreviewed/action@v1\n      - name: Prove restore policy source admission\n"),
        ("injected shell", "      - name: Prove restore policy source admission\n", "      - run: echo unreviewed\n      - name: Prove restore policy source admission\n"),
    )
    publisher_blob_only = {"unreviewed Action", "unreviewed shell", "appended command"}
    independent_blob_only = {"injected Action", "injected shell"}
    if (len(publisher_cases), len(independent_cases)) != (21, 13):
        raise SystemExit("restore policy source negative population drift")
    if sum(label in publisher_blob_only for label, _, _ in publisher_cases) != 3 or sum(label in independent_blob_only for label, _, _ in independent_cases) != 2:
        raise SystemExit("restore policy digest-only negative population drift")
    for target, cases in (("publisher", publisher_cases), ("independent", independent_cases)):
        for label, old, new in cases:
            original = publisher if target == "publisher" else independent
            if old not in original:
                raise SystemExit("restore policy negative fixture missing: " + target + " " + label)
            mutated = original.replace(old, new, 1)
            if mutated == original:
                raise SystemExit("restore policy negative fixture unchanged: " + target + " " + label)
            try:
                if target == "publisher":
                    validate(mutated, independent, check_publisher_blob=label in publisher_blob_only)
                else:
                    validate(publisher, mutated, check_independent_blob=label in independent_blob_only)
            except SystemExit:
                continue
            raise SystemExit("restore policy accepted source mutation: " + target + " " + label)
    print(f"PASS: restore policy publisher source admission ({len(publisher_cases) - 3} semantic + 3 blob-only negatives), independent source admission ({len(independent_cases) - 2} semantic + 2 blob-only negatives)")


def main() -> int:
    publisher = source(PUBLISHER)
    independent = source(INDEPENDENT)
    validate(publisher, independent)
    prove_trigger_reachability_negatives(publisher, independent)
    runtime(publisher, independent)
    negatives(publisher, independent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
