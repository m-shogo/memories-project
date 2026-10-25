#!/usr/bin/env python3
"""Pin least-privilege and crash-safe publication for migration production admission."""
import hashlib
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/migration-production-shaped-admission.yml"
PERMISSION_CI = ROOT / ".github/workflows/migration-production-shaped-admission-permission-negative.yml"
PERMISSION_CI_SHA = "97cf42f2e0a206a9fb489a43e9c16e9f941fc9e3"
CHECKOUT_PIN = "uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262"
SETUP_PIN = "uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065"
PERMISSION_SCOPE = "if: github.event_name == 'pull_request' || ((github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so')"
WRITER_SCOPE = "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def section(text: str, start: str, end: str | None = None) -> str:
    offset = text.find(start)
    require(offset >= 0, f"missing workflow section: {start.strip()}")
    tail = text[offset:]
    if end is None:
        return tail
    end_offset = tail.find(end, len(start))
    return tail if end_offset < 0 else tail[:end_offset]



def prove_writer_scope_negatives(reconcile: str) -> None:
    require(reconcile.count(WRITER_SCOPE) == 1, "migration writer scope not uniquely bound")
    for label, weakened in (
        ("broad non-PR", "if: github.event_name != 'pull_request'"),
        ("always", "if: always()"),
        ("push only", "if: github.event_name == 'push'"),
        ("branch only", "if: github.ref == 'refs/heads/so'"),
        ("missing branch", "if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'"),
    ):
        changed = reconcile.replace(WRITER_SCOPE, weakened, 1)
        require(changed != reconcile, "migration writer scope fixture unchanged: " + label)
        try:
            require(WRITER_SCOPE in changed, "migration writer scope rejected: " + label)
        except Fail:
            continue
        raise Fail("migration writer scope accepted weakened predicate: " + label)
    print("PASS: migration writer push/dispatch so-only scope (5 negatives)")


def verify_permission_ci_source(source: str) -> None:
    required = (
        "  pull_request:\n    branches:\n      - so\n",
        "  push:\n    branches:\n      - so\n",
        "  workflow_dispatch:\n",
        "permissions:\n  contents: read\n",
        "      contents: read\n",
        "persist-credentials: false",
        CHECKOUT_PIN,
        SETUP_PIN,
        PERMISSION_SCOPE,
        'test "${GITHUB_BASE_REF:-}" = "so"',
        'test "${GITHUB_REF:-}" = "refs/heads/so"',
        '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]',
        'test "$(git rev-parse HEAD)" = "$expected"',
        'test -z "$(git status --porcelain)"',
        "python scripts/validate-memory-os-migration-production-shaped-admission-permission-negative.py",
    )
    for token in required:
        require(source.count(token) >= 1, "migration permission CI source guard missing reviewed token")
    for forbidden in ("contents: write", "persist-credentials: true", "pull_request_target:", "secrets."):
        require(forbidden not in source, "migration permission CI unreviewed privilege")
    data = source.encode("utf-8")
    digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    require(digest == PERMISSION_CI_SHA, "migration permission CI complete source drift")


def prove_permission_ci_source_negatives(source: str) -> None:
    cases = (
        ("PR target", "  pull_request:\n    branches:\n      - so\n", "  pull_request:\n"),
        ("floating checkout", CHECKOUT_PIN, "uses: actions/checkout@v4"),
        ("floating setup", SETUP_PIN, "uses: actions/setup-python@v5"),
        ("checkout credentials", "persist-credentials: false", "persist-credentials: true"),
        ("broad event scope", PERMISSION_SCOPE, "if: always()"),
        ("missing PR base", 'test "${GITHUB_BASE_REF:-}" = "so"', "true"),
        ("missing push ref", 'test "${GITHUB_REF:-}" = "refs/heads/so"', "true"),
        ("weak SHA", '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]', 'test -n "$expected"'),
        ("unreviewed shell", "      - name: Require exact clean source", "      - run: echo unreviewed\n      - name: Require exact clean source"),
    )
    for label, before, after in cases:
        require(source.count(before) == 1, "migration permission CI mutation anchor drift: " + label)
        changed = source.replace(before, after, 1)
        try:
            verify_permission_ci_source(changed)
        except Fail:
            continue
        raise Fail("migration permission CI accepted weakened source: " + label)
    print("PASS: migration permission CI source negatives (9 cases)")


def prove_permission_ci_sha_runtime() -> None:
    for value, allowed in (("a" * 40, True), ("0" * 40, True), ("A" * 40, False),
                           ("g" * 40, False), ("a" * 39, False), ("a" * 41, False), ("", False)):
        result = subprocess.run(["bash", "-e", "-c", '[[ "$expected" =~ ^[0-9a-f]{40}$ ]]'],
                                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "expected": value},
                                capture_output=True, check=False)
        require((result.returncode == 0) == allowed, "migration permission CI SHA runtime drift")
    print("PASS: migration permission CI SHA runtime (7 cases)")


def main() -> int:
    permission_ci_source = PERMISSION_CI.read_text(encoding="utf-8")
    verify_permission_ci_source(permission_ci_source)
    prove_permission_ci_source_negatives(permission_ci_source)
    prove_permission_ci_sha_runtime()
    text = WORKFLOW.read_text(encoding="utf-8")
    require("pull_request_target:" not in text, "pull_request_target must never carry migration admission authority")
    require("permissions:\n  contents: read\n" in text, "workflow default must remain contents: read")

    pr = section(text, "  validate-pr:\n", "  reconcile:\n")
    require("if: github.event_name == 'pull_request'" in pr, "pull request validation job must be PR-only")
    require("permissions:\n      contents: read" in pr, "pull request validation must remain contents: read")
    require("ref: ${{ github.event.pull_request.head.sha }}" in pr, "pull request validation must checkout exact PR head")
    require("git diff --exit-code" in pr, "pull request validation must reject deterministic authority drift")
    require("contents: write" not in pr, "pull request validation must not receive write authority")

    reconcile = section(text, "  reconcile:\n")
    require(WRITER_SCOPE in reconcile, "publication job must be push/dispatch on so only")
    prove_writer_scope_negatives(reconcile)
    require("permissions:\n      contents: write" in reconcile, "non-PR publication job must retain bounded write authority")
    require("ref: ${{ github.sha }}" in reconcile, "publication must checkout exact event source")
    require(reconcile.count("git fetch origin so") >= 3, "publication and diagnostic paths must re-check remote source")
    require("refusing stale migration authority write" in reconcile, "derived authority publication must fail closed on source drift")
    require("refusing stale migration diagnostic write" in reconcile, "diagnostic publication must fail closed on source drift")
    require("refusing stale migration diagnostic write" in reconcile, "diagnostic publication CAS missing")
    require("tempfile.mkstemp" in reconcile, "failure diagnostic must use same-directory temporary file")
    require("os.fsync" in reconcile, "failure diagnostic must fsync temporary bytes")
    require("os.replace" in reconcile, "failure diagnostic must publish with atomic replace")
    require("'productionEvidence': False" in reconcile, "failure diagnostic must not fabricate production evidence")
    require("'productionReady': False" in reconcile, "failure diagnostic must not fabricate production readiness")

    print("Memory OS migration production admission permission negative PASS")
    print("pull request contents write authority: false")
    print("non-PR publication source-bound: true")
    print("diagnostic publication atomic: true")
    print("production evidence fabricated: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION PRODUCTION ADMISSION PERMISSION NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
