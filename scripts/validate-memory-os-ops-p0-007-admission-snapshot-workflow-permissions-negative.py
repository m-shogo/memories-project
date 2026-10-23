#!/usr/bin/env python3
"""Prove strict OPS-P0-007 snapshot PR validation is read-only and publication remains source-bound."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PR_WORKFLOW = ROOT / ".github/workflows/ops-p0-007-admission-snapshot-pr.yml"
PUBLISH_WORKFLOW = ROOT / ".github/workflows/ops-p0-007-admission-snapshot.yml"
FULL_ADMISSION_VALIDATORS = (
    "scripts/validate-memory-os-recovery-objectives.py",
    "scripts/validate-memory-os-backup-restore-drill-request.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_canonical_workflow(path: Path, relative: Path, root: Path = ROOT) -> None:
    try:
        lexical = path.relative_to(root)
        resolved = path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"strict snapshot workflow missing or escapes canonical root: {relative}") from exc
    require(
        lexical == relative and resolved == relative and path.is_file() and not path.is_symlink(),
        f"strict snapshot workflow path drift: {relative}",
    )


def prove_symlink_rejected() -> None:
    # Isolated outside the checkout: this proof cannot dirty source-bound CI.
    with tempfile.TemporaryDirectory(prefix="ops-p0-007-workflow-path-negative-") as tmp:
        root = Path(tmp)
        target = root / "target.yml"
        alias = root / "alias.yml"
        target.write_text("permissions: contents: read\n", encoding="utf-8")
        alias.symlink_to(target.name)
        require_canonical_workflow(target, Path("target.yml"), root)
        try:
            require_canonical_workflow(alias, Path("alias.yml"), root)
        except Fail as exc:
            require("workflow path drift" in str(exc), f"symlink rejected outside intended path guard: {exc}")
        else:
            raise Fail("strict snapshot workflow symlink alias unexpectedly accepted")


def validate_atomic_diagnostic_publication(publish: str) -> None:
    required_fragments = (
        "existing_mode = path.stat().st_mode & 0o7777 if path.exists() else None",
        "tempfile.mkstemp(",
        "dir=path.parent",
        "os.fchmod(fd, existing_mode)",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required_fragments if fragment not in publish]
    require(not missing, f"strict snapshot diagnostic publication is not crash-safe/mode-preserving: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in publish,
        "strict snapshot diagnostic publication regressed to direct write_text",
    )


def require_full_admission_chain(workflow: str, label: str) -> None:
    for validator in FULL_ADMISSION_VALIDATORS:
        require(validator in workflow, f"{label} missing full admission validator: {validator}")
        require(
            f"python {validator}" in workflow,
            f"{label} does not execute full admission validator: {validator}",
        )


def main() -> int:
    require_canonical_workflow(PR_WORKFLOW, Path(".github/workflows/ops-p0-007-admission-snapshot-pr.yml"))
    require_canonical_workflow(PUBLISH_WORKFLOW, Path(".github/workflows/ops-p0-007-admission-snapshot.yml"))
    prove_symlink_rejected()
    pr = PR_WORKFLOW.read_text(encoding="utf-8")
    publish = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    require("pull_request:" in pr, "read-only strict snapshot PR workflow must be pull-request scoped")
    require("contents: read" in pr, "strict snapshot PR workflow must use contents: read")
    require("contents: write" not in pr, "strict snapshot PR workflow must never receive contents: write")
    require("pull_request_target" not in pr, "strict snapshot PR workflow must not use pull_request_target")
    require("github.event.pull_request.head.sha" in pr, "strict snapshot PR workflow must bind checkout to exact PR head")
    require("git diff --exit-code -- contracts/operations/ops-p0-007-admission-snapshot.v1.json" in pr, "strict snapshot PR workflow must reject deterministic authority drift")
    require("git push" not in pr, "strict snapshot PR workflow must not publish authority")
    require_full_admission_chain(pr, "strict snapshot PR workflow")

    require("contents: write" in publish, "strict snapshot publication workflow requires explicit contents: write")
    require("pull_request:" not in publish, "strict snapshot publication workflow must not run on pull requests")
    require("pull_request_target" not in publish, "strict snapshot publication workflow must not use pull_request_target")
    require("ref: ${{ github.sha }}" in publish, "strict snapshot publication workflow must bind checkout to exact event SHA")
    require("SOURCE_SHA" in publish, "strict snapshot publication workflow must capture source authority")
    require("git rev-parse origin/so" in publish, "strict snapshot publication workflow must compare publication authority with origin/so")
    require("refusing stale strict snapshot" in publish, "strict snapshot publication workflow must fail closed on stale authority")
    require("refusing stale diagnostic" in publish, "strict snapshot publication workflow must fail closed on stale diagnostics")
    require("revalidate_latest_snapshot" in publish, "strict snapshot publication workflow must retain bounded full revalidation")
    require_full_admission_chain(publish, "strict snapshot publication workflow")
    validate_atomic_diagnostic_publication(publish)

    print("Memory OS OPS-P0-007 strict snapshot workflow permission negative PASS")
    print("pull request write token exposed: false")
    print("pull request authority publication allowed: false")
    print("full recovery objective admission validation required: true")
    print("full reviewed drill request admission validation required: true")
    print("full request-bound generation evidence validation required: true")
    print("full typed eight-domain admission validation required: true")
    print("exact-source publication CAS required: true")
    print("crash-safe mode-preserving diagnostic publication required: true")
    print("production evidence created: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError) as exc:
        print(f"OPS-P0-007 SNAPSHOT WORKFLOW PERMISSION NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
