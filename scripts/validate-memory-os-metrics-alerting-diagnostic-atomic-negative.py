#!/usr/bin/env python3
"""Prove metrics alerting diagnostics remain source-bound and crash-safe."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/diagnose-metrics-alerting.yml"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def main() -> int:
    require(WORKFLOW.is_file(), "metrics alerting diagnostic workflow missing")
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "ref: ${{ github.sha }}",
        "test \"$(git rev-parse HEAD)\" = \"${{ github.sha }}\"",
        "tempfile.mkstemp(",
        "dir=path.parent",
        "handle.flush()",
        "os.fsync(handle.fileno())",
        "os.replace(tmp_name, path)",
        "os.unlink(tmp_name)",
        "if [[ \"$(git rev-parse origin/so)\" != \"$SOURCE_SHA\" ]]",
    )
    missing = [fragment for fragment in required if fragment not in text]
    require(not missing, f"metrics diagnostic crash/source boundary drift: missing {missing}")
    require(
        "path.write_text(json.dumps(result" not in text,
        "metrics alerting diagnostic regressed to direct write_text",
    )
    print("PASS: metrics alerting diagnostic is exact-source and atomic")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"METRICS ALERTING DIAGNOSTIC ATOMIC NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
