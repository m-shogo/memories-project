#!/usr/bin/env python3
"""Negative coverage for backup/restore admission-chain workflow permissions."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain-workflow-permissions.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_admission_chain_workflow_permissions", VALIDATOR_PATH)
    require(spec is not None and spec.loader is not None, "cannot load admission-chain permission validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_reject(module, label: str, mutated: str) -> None:
    original = module.exact_workflow
    module.exact_workflow = lambda: mutated
    try:
        try:
            module.main()
        except module.Fail:
            return
        raise Fail(f"permission validator accepted forbidden mutation: {label}")
    finally:
        module.exact_workflow = original


def replace_once(text: str, old: str, new: str, label: str) -> str:
    require(text.count(old) == 1, f"negative fixture boundary drift for {label}: expected exactly one match")
    return text.replace(old, new, 1)


def main() -> int:
    module = load_validator()
    canonical = module.exact_workflow()

    cases = (
        (
            "pull_request_target trigger",
            canonical.replace("  pull_request:\n", "  pull_request_target:\n", 1),
        ),
        (
            "workflow-level write permission",
            replace_once(canonical, "permissions:\n  contents: read\n", "permissions:\n  contents: write\n", "workflow-level permission"),
        ),
        (
            "PR write permission",
            replace_once(canonical, "permissions:\n      contents: read\n", "permissions:\n      contents: write\n", "PR job permission"),
        ),
        (
            "PR runtime event checkout",
            replace_once(canonical, "ref: ${{ github.event.pull_request.head.sha }}", "ref: ${{ github.sha }}", "PR exact-head checkout"),
        ),
        (
            "publication allowed on pull requests",
            replace_once(canonical, "if: github.event_name != 'pull_request'", "if: github.event_name == 'pull_request'", "publication PR exclusion"),
        ),
        (
            "publication source identity check removed",
            replace_once(canonical, "test \"$(git rev-parse HEAD)\" = \"$GITHUB_SHA\"", "echo \"source identity check removed\"", "publication source identity"),
        ),
        (
            "bounded stale-authority refusal removed",
            replace_once(canonical, "refusing stale derived authority", "allowing stale derived authority", "stale authority refusal"),
        ),
        (
            "stale diagnostic refusal removed",
            replace_once(canonical, "refusing stale failure diagnostic", "allowing stale failure diagnostic", "stale diagnostic refusal"),
        ),
    )

    for label, mutated in cases:
        require(mutated != canonical, f"negative mutation did not change workflow: {label}")
        expect_reject(module, label, mutated)

    require(module.exact_workflow() == canonical, "negative suite mutated canonical workflow authority")
    print("Backup/restore admission-chain workflow permission negative PASS")
    print(f"forbidden workflow mutations rejected: {len(cases)}")
    print("production evidence created: false")
    print("production traffic changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN WORKFLOW PERMISSION NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
