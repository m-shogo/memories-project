#!/usr/bin/env python3
"""Fail closed if restore-drill planning PR validation regains repository write authority."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-drill-request.yml"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    require("pull_request_target:" not in text, "drill-request authority must not use pull_request_target")
    require("\njobs:\n  validate-pr:\n" in text, "dedicated drill-request PR validation job missing")
    require("\n  validate:\n" in text, "drill-request non-PR authority job missing")

    _, jobs = text.split("\njobs:\n", 1)
    validate_pr, validate = jobs.split("\n  validate:\n", 1)

    require("if: github.event_name == 'pull_request'" in validate_pr, "drill-request PR validator must be pull-request-only")
    require("permissions:\n      contents: read" in validate_pr, "drill-request PR validator must explicitly remain contents: read")
    require("ref: ${{ github.event.pull_request.head.sha }}" in validate_pr, "drill-request PR validator must checkout exact pull-request head")
    require("contents: write" not in validate_pr, "drill-request PR validator unexpectedly has write authority")
    require("test -z \"$(git status --porcelain)\"" in validate_pr, "drill-request PR validator must require a clean exact source")
    require("validate-memory-os-backup-restore-drill-request-writer-authority.py" in validate_pr, "drill-request PR validator must retain writer authority validation")
    require("validate-memory-os-backup-restore-drill-request-reconcile-negative.py" in validate_pr, "drill-request PR validator must retain reconcile negatives")
    require("validate-memory-os-backup-restore-drill-request-append-rollback-negative.py" in validate_pr, "drill-request PR validator must retain append rollback negatives")
    require("validate-memory-os-backup-restore-generation-evidence.py" in validate_pr, "drill-request PR validator must retain downstream generation-evidence validation")
    require("validate-memory-os-backup-restore-non-resurrection-admission.py" in validate_pr, "drill-request PR validator must retain downstream typed non-resurrection validation")
    require("validate-memory-os-operability.py" in validate_pr, "drill-request PR validator must retain aggregate Operability validation")
    require("git diff --exit-code" in validate_pr, "drill-request PR validator must reject deterministic authority drift")

    validate_header = validate.split("steps:", 1)[0]
    require("if: github.event_name != 'pull_request'" in validate_header, "drill-request publication job must explicitly exclude pull requests")
    require("git rev-parse origin/so" in validate, "drill-request publisher must retain stale-source CAS")
    require("SOURCE_SHA" in validate, "drill-request publisher must remain source-bound")
    require("os.replace(tmp_name, path)" in validate, "drill-request failure diagnostic must retain atomic replacement")
    require("'requestCreated': False" in validate, "drill-request failure diagnostic must not fabricate a reviewed request")
    require("'restoreExecuted': False" in validate, "drill-request failure diagnostic must not claim restore execution")
    require("'productionEvidence': False" in validate, "drill-request failure diagnostic must remain non-production evidence")
    require("'productionReady': False" in validate, "drill-request failure diagnostic must not claim production readiness")

    print("PASS: restore-drill planning PR validation is exact-head and read-only")
    print("PASS: reviewed requests remain planning authority only and publication excludes pull requests")
    print("PASS: downstream generation/typed gates, rollback negatives, stale-source CAS and atomic diagnostics remain enforced")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
