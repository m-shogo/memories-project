#!/usr/bin/env python3
"""Fail closed if end-to-end backup/restore admission PR validation regains write authority."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-admission-chain.yml"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    require("pull_request_target:" not in text, "backup/restore admission chain must not use pull_request_target")
    require("permissions:\n  contents: read\n" in text, "admission-chain workflow default token must remain read-only")
    require("\njobs:\n  validate-pr:\n" in text, "dedicated admission-chain PR validation job missing")
    require("\n  validate-and-publish:\n" in text, "dedicated admission-chain non-PR publication job missing")

    _, jobs = text.split("\njobs:\n", 1)
    validate_pr, publish = jobs.split("\n  validate-and-publish:\n", 1)

    require("if: github.event_name == 'pull_request'" in validate_pr, "admission-chain PR validator must be pull-request-only")
    require("permissions:\n      contents: read" in validate_pr, "admission-chain PR validator must explicitly remain contents: read")
    require("ref: ${{ github.event.pull_request.head.sha }}" in validate_pr, "admission-chain PR validator must checkout exact pull-request head")
    require("contents: write" not in validate_pr, "admission-chain PR validator unexpectedly has write authority")
    require("test -z \"$(git status --porcelain)\"" in validate_pr, "admission-chain PR validator must require a clean source")
    require("validate-memory-os-backup-restore-admission-chain-full.py" in validate_pr, "admission-chain PR validator must execute the full authority chain")
    require("git diff --exit-code" in validate_pr, "admission-chain PR validator must reject deterministic authority drift")

    publish_header = publish.split("steps:", 1)[0]
    require("if: github.event_name != 'pull_request'" in publish_header, "admission-chain publisher must explicitly exclude pull requests")
    require("permissions:\n      contents: write" in publish_header, "admission-chain publisher must hold write authority only at job scope")
    require("ref: ${{ github.sha }}" in publish, "admission-chain publisher must checkout exact event SHA")
    require("git rev-parse origin/so" in publish, "admission-chain publisher must retain stale-source CAS")
    require("revalidate_latest_chain" in publish, "admission-chain publisher must retain bounded latest-so full revalidation")
    require("os.replace(tmp_name, path)" in publish, "admission-chain failure diagnostic must retain atomic replacement")
    require("productionDecision" in publish and "NO_GO" in publish, "admission-chain failure diagnostic must retain NO_GO boundary")

    print("PASS: end-to-end admission PR validation is exact-head and read-only")
    print("PASS: admission publication is non-PR-only with job-scoped write authority")
    print("PASS: bounded full revalidation, stale-source CAS and atomic failure diagnostics remain enforced")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
