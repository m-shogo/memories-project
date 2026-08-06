#!/usr/bin/env python3
"""Apply deterministic source corrections for deletion-under-load."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "services/import-api/internal/httpserver/deletion_under_load_test.go"


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    old = '"memory-os-import-api/internal/accountdelete"'
    new = '"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"'
    if new in text:
        print("Deletion-under-load source already reconciled")
        return 0
    if text.count(old) != 1:
        print("DELETION LOAD SOURCE RECONCILE FAILED: import authority drift", file=sys.stderr)
        return 1
    PATH.write_text(text.replace(old, new), encoding="utf-8")
    print("Reconciled deletion-under-load import authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
