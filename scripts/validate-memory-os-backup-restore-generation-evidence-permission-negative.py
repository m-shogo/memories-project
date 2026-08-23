#!/usr/bin/env python3
"""Fail closed if generation-evidence PR validation regains repository write authority."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-evidence.yml"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    require("pull_request_target:" not in text, "generation-evidence authority must not use pull_request_target")
    require("\njobs:\n  validate-pr:\n" in text, "dedicated generation-evidence PR validation job missing")
    require("\n  validate:\n" in text, "generation-evidence non-PR authority job missing")

    _, jobs = text.split("\njobs:\n", 1)
    validate_pr, validate = jobs.split("\n  validate:\n", 1)

    require("if: github.event_name == 'pull_request'" in validate_pr, "generation-evidence PR validator must be pull-request-only")
    require("permissions:\n      contents: read" in validate_pr, "generation-evidence PR validator must explicitly remain contents: read")
    require("ref: ${{ github.event.pull_request.head.sha }}" in validate_pr, "generation-evidence PR validator must checkout exact pull-request head")
    require("contents: write" not in validate_pr, "generation-evidence PR validator unexpectedly has write authority")
    require("test -z \"$(git status --porcelain)\"" in validate_pr, "generation-evidence PR validator must require a clean exact source")
    require("git diff --exit-code" in validate_pr, "generation-evidence PR validator must reject deterministic authority drift")
    require("validate-memory-os-backup-restore-generation-evidence-writer-authority.py" in validate_pr, "generation-evidence PR validator must retain writer authority validation")
    require("validate-memory-os-backup-restore-generation-evidence-writer-authority-negative.py" in validate_pr, "generation-evidence PR validator must retain writer authority substitution negatives")
    require("validate-memory-os-operability.py" in validate_pr, "generation-evidence PR validator must retain aggregate Operability validation")

    require("if: github.event_name != 'pull_request'" in validate, "generation-evidence publication job must explicitly exclude pull requests")
    require("contents: read" not in validate.split("steps:", 1)[0], "generation-evidence non-PR job unexpectedly overrides publication authority to read-only")
    require("github.event_name == 'pull_request'" not in validate.split("steps:", 1)[0], "generation-evidence non-PR job condition must not admit pull requests")
    require("git rev-parse origin/so" in validate, "generation-evidence publisher must retain stale-source CAS")
    require("SOURCE_SHA" in validate, "generation-evidence publisher must remain source-bound")
    require("os.replace(tmp_name, path)" in validate, "generation-evidence failure diagnostic must retain atomic replacement")

    print("PASS: generation-evidence PR validation is exact-head and read-only")
    print("PASS: generation-evidence publication remains non-PR-only and source-bound")
    print("PASS: writer authority negatives, Operability validation, stale-source CAS and atomic diagnostic publication remain enforced")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
