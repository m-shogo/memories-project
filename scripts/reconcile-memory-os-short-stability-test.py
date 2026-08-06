#!/usr/bin/env python3
"""Apply deterministic source fixes before the short stability workflow runs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "services/import-api/internal/httpserver/short_stability_sample_test.go"


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    old = '\t"fmt"\n\t"os"\n'
    new = '\t"fmt"\n\t"net/http"\n\t"os"\n'
    if new in text:
        print("Short stability source already reconciled")
        return 0
    if text.count(old) != 1:
        print("SHORT STABILITY SOURCE RECONCILE FAILED: import authority drift", file=sys.stderr)
        return 1
    PATH.write_text(text.replace(old, new), encoding="utf-8")
    print("Added the short stability HTTP import")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
