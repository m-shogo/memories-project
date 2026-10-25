#!/usr/bin/env python3
"""Pin least-privilege and crash-safe publication for host-failure admission."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/deletion-worker-host-failure-admission.yml"


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


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    require("pull_request_target:" not in text, "pull_request_target must never carry host-failure authority")
    require("permissions:\n  contents: read\n" in text, "workflow default must remain contents: read")

    require("  pull_request:\n    branches:\n      - so\n" in text, "pull requests must target so")
    require(text.count("uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262") == 2, "both checkouts must be immutable")
    require(text.count("uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065") == 2, "both Python setups must be immutable")
    pr = section(text, "  validate-pr:\n", "  reconcile:\n")
    require("if: github.event_name == 'pull_request'" in pr, "pull request validation job must be PR-only")
    require("permissions:\n      contents: read" in pr, "pull request validation must remain contents: read")
    require("ref: ${{ github.event.pull_request.head.sha }}" in pr, "pull request validation must checkout exact PR head")
    require("git diff --exit-code" in pr, "pull request validation must reject deterministic authority drift")
    require("contents: write" not in pr, "pull request validation must not receive write authority")
    require("persist-credentials: false" in pr, "PR checkout must not persist credentials")
    require('test "${GITHUB_EVENT_NAME:-}" = "pull_request"' in pr, "PR event identity missing")
    require('test "${GITHUB_BASE_REF:-}" = "so"' in pr, "PR base identity missing")
    require('[[ "$PR_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]' in pr, "PR head SHA format missing")

    reconcile = section(text, "  reconcile:\n")
    require("if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'" in reconcile, "publication job must be scoped to so push/dispatch")
    require("permissions:\n      contents: write" in reconcile, "non-PR publication job must retain bounded write authority")
    require("ref: ${{ github.sha }}" in reconcile, "publication must checkout exact event source")
    require("persist-credentials: true" in reconcile, "writer checkout credentials missing")
    require('[[ "${GITHUB_EVENT_NAME:-}" == "push" || "${GITHUB_EVENT_NAME:-}" == "workflow_dispatch" ]]' in reconcile, "writer event identity missing")
    require('test "${GITHUB_REF:-}" = "refs/heads/so"' in reconcile, "writer branch identity missing")
    require('[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]]' in reconcile, "writer SHA format missing")
    require("Host-failure authority source is stale" in reconcile, "derived authority publication must fail closed on source drift")
    require("Host-failure diagnostic source is stale before publication" in reconcile, "diagnostic pre-publication CAS missing")
    require("Host-failure diagnostic source is stale before push" in reconcile, "diagnostic pre-push CAS missing")
    require("tempfile.mkstemp" in reconcile, "failure diagnostic must use same-directory temporary file")
    require("os.fsync" in reconcile, "failure diagnostic must fsync temporary bytes")
    require("os.replace" in reconcile, "failure diagnostic must publish with atomic replace")
    require("'actualPhysicalHostOrVMNodeLossCovered': False" in reconcile, "diagnostic must not fabricate physical host loss coverage")
    require("'deletionHostFailureRecoveryProven': False" in reconcile, "diagnostic must not fabricate host-failure recovery proof")
    require("'productionEquivalentEvidence': False" in reconcile, "diagnostic must not fabricate production-equivalent evidence")
    require("'productionEvidence': False" in reconcile, "diagnostic must not fabricate production evidence")
    require("'productionReady': False" in reconcile, "diagnostic must not fabricate production readiness")

    print("Memory OS deletion host-failure permission negative PASS")
    print("pull request contents write authority: false")
    print("non-PR publication source-bound: true")
    print("diagnostic publication atomic: true")
    print("physical host failure evidence fabricated: false")
    print("production evidence fabricated: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION HOST-FAILURE PERMISSION NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
