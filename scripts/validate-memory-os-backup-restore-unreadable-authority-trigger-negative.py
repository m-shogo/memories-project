#!/usr/bin/env python3
"""Prove unreadable-authority readonly CI reaches every executed validator."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/backup-restore-unreadable-authority-readonly.yml"
SELF = "scripts/validate-memory-os-backup-restore-unreadable-authority-trigger-negative.py"
PROTECTED = (
    "scripts/validate-memory-os-*-load-negative.py",
    "scripts/validate-memory-os-*-writer-authority-negative.py",
    "scripts/validate-memory-os-backup-restore-generation-evidence-writer-authority.py",
    "scripts/validate-memory-os-backup-restore-non-resurrection-transport-negative.py",
    SELF,
)
PR_MARKER = "  pull_request:\n    paths:\n"
PUSH_MARKER = "  push:\n    branches: [so]\n    paths:\n"
PERMISSIONS_MARKER = "\npermissions:\n"


def validate(source: str) -> None:
    for marker in (PR_MARKER, PUSH_MARKER, PERMISSIONS_MARKER):
        if source.count(marker) != 1:
            raise SystemExit(f"unreadable readonly trigger marker drift: {marker.strip()}")
    pr = source.split(PR_MARKER, 1)[1].split(PUSH_MARKER, 1)[0]
    push = source.split(PUSH_MARKER, 1)[1].split(PERMISSIONS_MARKER, 1)[0]
    executed = re.findall(r"^          python (scripts/[A-Za-z0-9_-]+\.py)$", source, re.MULTILINE)
    if len(executed) != 11 or len(set(executed)) != 11 or SELF not in executed:
        raise SystemExit("unreadable readonly executable inventory drift")
    for event, block in (("pull_request", pr), ("push", push)):
        paths = re.findall(r'^      - "([^"]+)"$', block, re.MULTILINE)
        for path in PROTECTED:
            token = f'      - "{path}"\n'
            if block.count(token) != 1:
                raise SystemExit(f"unreadable readonly {event} missing or duplicate trigger: {path}")
        for executed_script in executed:
            if not any(fnmatch.fnmatchcase(executed_script, path) for path in paths):
                raise SystemExit(f"unreadable readonly {event} cannot reach executed script: {executed_script}")


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate(source)
    for event in ("pull_request", "push"):
        for path in PROTECTED:
            token = f'      - "{path}"\n'
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(PUSH_MARKER, 1)
                mutated = prefix + PUSH_MARKER + suffix.replace(token, "", 1)
            try:
                validate(mutated)
            except SystemExit:
                continue
            raise SystemExit(f"unreadable readonly accepted missing {event} trigger: {path}")
    print("PASS: unreadable readonly trigger reachability (10 removal negatives; 11 executable scripts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
