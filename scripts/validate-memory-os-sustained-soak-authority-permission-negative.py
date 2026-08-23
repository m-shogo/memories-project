#!/usr/bin/env python3
"""Fail closed if repeated-soak PR validation regains repository write authority."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/reconcile-sustained-local-soak-authority.yml"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    require("pull_request_target:" not in text, "repeated-soak authority must not use pull_request_target")
    require("permissions:\n  contents: read\n" in text, "workflow default GITHUB_TOKEN authority must remain read-only")
    require("\njobs:\n  validate-pr:\n" in text, "dedicated pull-request validation job missing")
    require("\n  reconcile:\n" in text, "non-PR publication job missing")

    _, jobs = text.split("\njobs:\n", 1)
    validate_pr, reconcile = jobs.split("\n  reconcile:\n", 1)

    require("if: github.event_name == 'pull_request'" in validate_pr, "PR validator must be pull-request-only")
    require("permissions:\n      contents: read" in validate_pr, "PR validator must explicitly remain contents: read")
    require("ref: ${{ github.event.pull_request.head.sha }}" in validate_pr, "PR validator must checkout exact pull-request head")
    require("contents: write" not in validate_pr, "PR validator unexpectedly has write authority")
    require("git diff --exit-code" in validate_pr, "PR validator must reject deterministic authority drift")

    require("github.event_name != 'pull_request'" in reconcile, "publication job must explicitly exclude pull requests")
    require("permissions:\n      contents: write" in reconcile, "non-PR publisher must hold its write authority only at job scope")
    require("ref: ${{ github.sha }}" in reconcile, "non-PR publisher must checkout exact event SHA")
    require("github.event.pull_request.head.sha" not in reconcile, "non-PR publisher must not depend on pull-request authority")
    require("git rev-parse origin/so" in reconcile, "non-PR publisher must retain stale-source CAS")
    require("os.replace(tmp_name, path)" in reconcile, "failure diagnostic must retain atomic replacement")

    print("PASS: repeated-soak PR validation is exact-head and read-only")
    print("PASS: repeated-soak publication is non-PR-only with job-scoped write authority")
    print("PASS: stale-source CAS and atomic diagnostic publication remain enforced")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
