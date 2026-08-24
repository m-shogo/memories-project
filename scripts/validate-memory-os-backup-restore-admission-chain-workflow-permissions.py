#!/usr/bin/env python3
"""Fail closed if the end-to-end backup/restore workflow leaks PR write authority."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_REL = Path(".github/workflows/backup-restore-admission-chain.yml")
WORKFLOW = ROOT / WORKFLOW_REL


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
    require("pull_request_target:" not in text, "pull_request_target must never control backup/restore admission publication")
    require("permissions:\n  contents: read\n" in text, "workflow-level contents permission must default to read")

    pr = job_block(text, "validate-pr", "validate-and-publish")
    publish = job_block(text, "validate-and-publish")

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

    require("if: github.event_name != 'pull_request'" in publish, "publication job must exclude pull requests")
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
