#!/usr/bin/env python3
"""Fail closed if the end-to-end backup/restore workflow leaks PR write authority."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_REL = Path(".github/workflows/backup-restore-admission-chain.yml")
WORKFLOW = ROOT / WORKFLOW_REL
INDEPENDENT_PERMISSION_WORKFLOW_REL = Path(".github/workflows/backup-restore-permission-boundary-negative.yml")
REVIEWED_INDEPENDENT_PERMISSION_WORKFLOW_BLOB_SHA = "02c8d1d2c8e7cc64dc61a6767f3c1cea79d454e3"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def exact_workflow() -> str:
    try:
        lexical = WORKFLOW.relative_to(ROOT)
        resolved = WORKFLOW.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail("admission-chain workflow missing or escapes repository") from exc
    require(lexical == WORKFLOW_REL and resolved == WORKFLOW_REL and WORKFLOW.is_file(), "admission-chain workflow authority drift")
    try:
        return WORKFLOW.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read admission-chain workflow: {exc}") from exc


def independent_permission_workflow() -> str:
    path = ROOT / INDEPENDENT_PERMISSION_WORKFLOW_REL
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
        require(resolved == INDEPENDENT_PERMISSION_WORKFLOW_REL and path.is_file()
                and not path.is_symlink(),
                "independent permission workflow authority substituted")
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, RuntimeError, ValueError, UnicodeDecodeError) as exc:
        raise Fail("independent permission workflow unreadable or escapes root") from exc


def require_reviewed_independent_permission_workflow_blob(source: str) -> None:
    """Bind the entire independent gate source, including event filters and shell bodies."""
    payload = source.encode("utf-8")
    blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    require(hashlib.sha1(blob).hexdigest() == REVIEWED_INDEPENDENT_PERMISSION_WORKFLOW_BLOB_SHA,
            "independent permission workflow complete source drift")


def validate_independent_permission_workflow(source: str) -> None:
    require("pull_request_target:" not in source,
            "independent permission workflow forbidden event")
    require(source.count("permissions:\n  contents: read\n") == 1,
            "independent permission workflow token scope drift")
    require(source.count("      - name: Checkout exact source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n        with:\n          ref: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.sha || github.sha }}\n          fetch-depth: 1\n          persist-credentials: false\n\n      - name: Set up Python\n        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n\n") == 1,
            "independent permission workflow checkout/setup source drift")
    require(source.count("      - name: Require exact clean source\n        env:\n          PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}\n        run: |\n          set -euo pipefail\n          test -z \"$(git status --porcelain)\"\n          if [[ \"${{ github.event_name }}\" == \"pull_request\" ]]; then\n            [[ \"$PR_HEAD_SHA\" =~ ^[0-9a-f]{40}$ ]]\n            test \"$(git rev-parse HEAD)\" = \"$PR_HEAD_SHA\"\n          else\n            test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\"\n          fi\n\n") == 1,
            "independent permission workflow PR source identity drift")
    jobs = source.split("\njobs:\n", 1)
    require(len(jobs) == 2, "independent permission workflow job boundary drift")
    step_headers = re.findall(r"(?m)^      - ([^\n]+)$", jobs[1])
    require(step_headers == ["name: Checkout exact source","name: Set up Python","name: Require exact clean source","name: Compile backup/restore permission negatives","name: Enforce end-to-end admission permission boundary","name: Enforce drill-request planning permission boundary","name: Enforce generation-evidence permission boundary","name: Enforce typed non-resurrection registry mode rollback","name: Enforce human-approved recovery-objective registry mode rollback","name: Prove read-only permission gate"],
            "independent permission workflow step inventory drift")
    require(source.count("        uses: ") == 2,
            "independent permission workflow unreviewed action step")
    require(source.count(
        "        run: python scripts/validate-memory-os-backup-restore-admission-chain-permission-negative.py\n"
    ) == 1, "independent permission workflow permission guard unreachable")


def job_block(text: str, name: str, next_name: str | None = None) -> str:
    marker = f"  {name}:\n"
    start = text.find(marker)
    require(start >= 0, f"workflow job missing: {name}")
    if next_name is None:
        return text[start:]
    end_marker = f"  {next_name}:\n"
    end = text.find(end_marker, start + len(marker))
    require(end > start, f"workflow job boundary missing: {name} -> {next_name}")
    return text[start:end]


def require_job_key_inventory(job: str, expected: tuple[str, ...], diagnostic: str) -> None:
    """Reject quoted, duplicate and unreviewed job-level YAML mapping keys."""
    keys = []
    for line in job.splitlines():
        if not line.startswith("    ") or line.startswith("     "):
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"    ([a-z][a-z-]*):(?:[ \t].*)?", line)
        require(match is not None, diagnostic)
        keys.append(match.group(1))
    require(tuple(keys) == expected, diagnostic)


def require_atomic_diagnostic_publication(publish: str) -> None:
    required = (
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
    )
    missing = [fragment for fragment in required if fragment not in publish]
    require(not missing, f"failure diagnostic publication is not crash-safe: missing {missing}")
    require(
        "path.write_text(json.dumps(value" not in publish,
        "failure diagnostic publication regressed to direct write_text",
    )


def main() -> int:
    text = exact_workflow()
    independent_source = independent_permission_workflow()
    validate_independent_permission_workflow(independent_source)
    require_reviewed_independent_permission_workflow_blob(independent_source)
    require("pull_request_target:" not in text, "pull_request_target must never control backup/restore admission publication")
    require("permissions:\n  contents: read\n" in text, "workflow-level contents permission must default to read")

    pr = job_block(text, "validate-pr", "validate-and-publish")
    publish = job_block(text, "validate-and-publish")

    require_job_key_inventory(
        pr, ("if", "permissions", "runs-on", "timeout-minutes", "steps"),
        "PR job key inventory drift",
    )
    require_job_key_inventory(
        publish, ("if", "permissions", "runs-on", "timeout-minutes", "steps"),
        "publication job key inventory drift",
    )

    # Bind both bootstrap actions and checkout credentials to reviewed job roles.
    require(pr.count("      - name: Checkout exact PR source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n          fetch-depth: 0\n          persist-credentials: false\n") == 1 and
            pr.count("        uses: actions/checkout@") == 1,
            "PR pinned checkout and credential boundary drift")
    require(pr.count("      - name: Set up Python\n        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n\n      - name: Verify exact clean PR authority source\n") == 1 and
            pr.count("        uses: actions/setup-python@") == 1 and
            pr.count("        uses: ") == 2,
            "PR pinned Python setup boundary drift")
    require(publish.count("      - name: Checkout exact publication source\n        uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262\n        with:\n          ref: ${{ github.sha }}\n          fetch-depth: 0\n          persist-credentials: true\n") == 1 and
            publish.count("        uses: actions/checkout@") == 1,
            "publication pinned checkout and credential boundary drift")
    require(publish.count("      - name: Set up Python\n        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065\n        with:\n          python-version: \"3.12\"\n\n      - name: Capture exact chain authority source\n") == 1 and
            publish.count("        uses: actions/setup-python@") == 1 and
            publish.count("        uses: ") == 2,
            "publication pinned Python setup boundary drift")

    require("if: github.event_name == 'pull_request'" in pr, "PR validation job must be pull-request-only")
    require("permissions:\n      contents: read\n" in pr, "PR validation job must explicitly retain read-only contents permission")
    require("contents: write" not in pr, "PR validation job must not receive contents: write")
    require("ref: ${{ github.event.pull_request.head.sha }}" in pr, "PR validation must checkout the exact PR head")
    require("python scripts/validate-memory-os-backup-restore-admission-chain-full.py" in pr, "PR validation must execute the canonical full chain runner")
    require("git diff --exit-code" in pr, "PR validation must reject deterministic derived-authority drift")
    require(
        'test -z "$(git status --porcelain --untracked-files=all)"' in pr,
        "PR validation must reject tracked or untracked workspace mutation",
    )

    approved_publish_condition = "if: (github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == 'refs/heads/so'"
    require(publish.startswith(
        "  validate-and-publish:\n    " + approved_publish_condition +
        "\n    permissions:\n      contents: write\n"
    ), "publication job event/ref authority drift")
    require(publish.count("\n    if: ") == 1,
            "publication job duplicate event condition")
    require("permissions:\n      contents: write\n" in publish, "publication job must own the only contents: write permission")
    require("ref: ${{ github.sha }}" in publish, "publication must checkout the exact event source")
    require("test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\"" in publish, "publication must verify exact source identity")
    require("python scripts/validate-memory-os-backup-restore-admission-chain-full.py" in publish, "publication must execute the same canonical full chain runner")
    require("assert_only_derived_chain_changes" in publish, "publication must reject unrelated workspace mutation")
    require("git reset --hard origin/so" in publish, "bounded retry must restart from latest canonical so")
    require("refusing stale derived authority" in publish, "bounded publication must fail closed on repeated source drift")
    require("refusing stale failure diagnostic" in publish, "failure diagnostic must reject stale source")
    require_atomic_diagnostic_publication(publish)

    require(text.count("contents: write") == 1, "exactly one contents: write grant is allowed in the admission-chain workflow")
    require(text.count("validate-memory-os-backup-restore-admission-chain-full.py") >= 3, "canonical full-chain runner must be shared by PR, publication and bounded revalidation")

    print("Backup/restore admission-chain workflow permission boundary PASS")
    print("PR contents write authority: false")
    print("PR exact-head validation: true")
    print("PR tracked/untracked mutation accepted: false")
    print("non-PR publication write authority: isolated")
    print("bounded latest-so revalidation and stale-source refusal: preserved")
    print("crash-safe failure diagnostic publication: required")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN WORKFLOW PERMISSION FAILED: {exc}")
        raise SystemExit(1)
