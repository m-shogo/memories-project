#!/usr/bin/env python3
"""Fail closed if restore-drill planning PR validation regains repository write authority."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-drill-request.yml"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_publication_scope(header: str) -> None:
    expected = "    if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'\n    permissions:\n      contents: write\n"
    require(header.startswith(expected),
            "drill publication event/ref authority drift")
    keys = []
    for line in header.splitlines():
        if not line.startswith("    ") or line.startswith("     "):
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"    ([a-z][a-z-]*):(?:[ \t].*)?", line)
        require(match is not None, "publication job key inventory drift")
        keys.append(match.group(1))
    require(tuple(keys) == ("if", "permissions", "runs-on", "timeout-minutes"),
            "publication job key inventory drift")



def require_reviewed_bootstrap(job: str, *, pr: bool) -> tuple[str, str]:
    """Bind both immutable actions, exact checkout source, and credential persistence."""
    name = "Checkout exact pull request source" if pr else "Checkout exact source"
    source = (
        "ref: ${{ github.event.pull_request.head.sha }}"
        if pr else "ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}"
    )
    checkout = (
        f"      - name: {name}\n"
        "        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n"
        "        with:\n"
        f"          {source}\n"
        "          fetch-depth: 0\n"
        f"          persist-credentials: {'false' if pr else 'true'}\n"
    )
    setup = (
        "      - name: Set up Python\n"
        "        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n"
        "        with:\n"
        '          python-version: "3.12"\n'
    )
    require(job.count(checkout) == 1, "drill bootstrap checkout source or credentials drift")
    require(job.count(setup) == 1, "drill bootstrap Python action drift")
    uses = re.findall(r"(?m)^\s*uses:\s*([^\n]+)$", job)
    require(uses == [
        "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    ], "drill bootstrap action inventory drift")
    return checkout, setup


def require_bootstrap_negatives(job: str, *, pr: bool) -> None:
    checkout, setup = require_reviewed_bootstrap(job, pr=pr)
    credential = "false" if pr else "true"
    mutations = (
        job.replace("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@v4", 1),
        job.replace("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", "actions/checkout@11d5960a326750d5838078e36cf38b85af677260", 1),
        job.replace("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "actions/setup-python@v5", 1),
        job.replace("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87060", 1),
        job.replace(f"          persist-credentials: {credential}\n",
                    f"          persist-credentials: {'true' if pr else 'false'}\n", 1),
        job.replace(f"          persist-credentials: {credential}\n", "", 1),
        job.replace(checkout, checkout.replace("fetch-depth: 0", "fetch-depth: 1"), 1),
        job.replace(checkout, checkout + "      - uses: actions/checkout@v4\n", 1),
    )
    for mutated in mutations:
        require(mutated != job, "drill bootstrap negative fixture did not mutate")
        try:
            require_reviewed_bootstrap(mutated, pr=pr)
        except Fail:
            pass
        else:
            raise Fail("drill bootstrap negative mutation accepted")

def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    require("pull_request_target:" not in text, "drill-request authority must not use pull_request_target")
    require("\njobs:\n  validate-pr:\n" in text, "dedicated drill-request PR validation job missing")
    require("\n  validate:\n" in text, "drill-request non-PR authority job missing")

    _, jobs = text.split("\njobs:\n", 1)
    validate_pr, validate = jobs.split("\n  validate:\n", 1)
    require_bootstrap_negatives(validate_pr, pr=True)
    require_bootstrap_negatives(validate, pr=False)

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
    require_publication_scope(validate_header)
    approved_if = "    " + "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"
    mutations = (
        validate_header.replace(approved_if, "    if: github.event_name != 'pull_request'", 1),
        validate_header.replace("refs/heads/so", "refs/heads/main", 1),
        validate_header.replace(approved_if, approved_if + "\n    \"if\": true", 1),
        validate_header.replace("github.event_name == 'push'",
                                "github.event_name == 'pull_request_target'", 1),
    )
    for mutated in mutations:
        require(mutated != validate_header, "publisher scope negative fixture unchanged")
        try:
            require_publication_scope(mutated)
        except Fail:
            pass
        else:
            raise Fail("publisher scope negative mutation accepted")
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
    print("publisher event/ref negative mutations rejected: 4")
    print("immutable bootstrap/source/credential negative mutations rejected: 16")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
