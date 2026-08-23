#!/usr/bin/env python3
"""Prove compatibility diagnostic PR validation cannot receive publication authority."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/reconcile-compatibility-authority-diagnostic.yml"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def main() -> int:
    require(WORKFLOW.is_file(), "compatibility authority diagnostic workflow missing")
    text = WORKFLOW.read_text(encoding="utf-8")

    require("pull_request_target:" not in text, "pull_request_target must remain forbidden")
    require("permissions:\n  contents: read\n" in text, "workflow default permissions must remain read-only")
    require("  validate-pr:\n    if: github.event_name == 'pull_request'\n    permissions:\n      contents: read\n" in text,
            "PR validation must remain an explicit read-only job")
    require("ref: ${{ github.event.pull_request.head.sha }}" in text,
            "PR validation must checkout the exact PR head")
    require("  reconcile:\n    if: >-\n      github.event_name != 'pull_request'" in text,
            "publication job must remain excluded from pull requests")
    require("    permissions:\n      contents: write\n" in text,
            "non-PR reconcile job must retain explicit publication permission")
    require("ref: ${{ github.sha }}" in text,
            "non-PR publication must remain source-bound to the event SHA")
    require("os.replace(tmp_name, path)" in text,
            "failure diagnostic must remain atomic")
    require("path.write_text(json.dumps(value" not in text,
            "failure diagnostic must not regress to direct write_text")

    print("PASS: compatibility diagnostic PR validation is read-only and exact-head")
    print("PASS: non-PR publication authority remains isolated and source-bound")
    print("PASS: compatibility failure diagnostic publication remains atomic")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"COMPATIBILITY DIAGNOSTIC PERMISSION NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
