#!/usr/bin/env python3
"""Apply deterministic source corrections for deletion-under-load."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "services/import-api/internal/httpserver/deletion_under_load_test.go"


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    if new in text:
        return text, False
    if text.count(old) != 1:
        raise RuntimeError(f"{label} authority drift")
    return text.replace(old, new), True


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    changed = False

    text, replaced = replace_once(
        text,
        '"memory-os-import-api/internal/accountdelete"',
        '"github.com/m-shogo/memories-project/services/import-api/internal/accountdelete"',
        "accountdelete import",
    )
    changed = changed or replaced

    text, replaced = replace_once(
        text,
        '\t"fmt"\n\t"net/http"',
        '\t"fmt"\n\t"io"\n\t"net/http"',
        "io import",
    )
    changed = changed or replaced

    text, replaced = replace_once(
        text,
        '''\t\t\t\t_ = response.Body.Close()
\t\t\t\tsamples[index] = liveHTTPSample{Status: response.StatusCode, Duration: time.Since(started)}
''',
        '''\t\t\t\t_, copyErr := io.Copy(io.Discard, response.Body)
\t\t\t\tcloseErr := response.Body.Close()
\t\t\t\tif copyErr != nil {
\t\t\t\t\tsamples[index] = liveHTTPSample{Duration: time.Since(started), Err: copyErr}
\t\t\t\t\tcontinue
\t\t\t\t}
\t\t\t\tif closeErr != nil {
\t\t\t\t\tsamples[index] = liveHTTPSample{Duration: time.Since(started), Err: closeErr}
\t\t\t\t\tcontinue
\t\t\t\t}
\t\t\t\tsamples[index] = liveHTTPSample{Status: response.StatusCode, Duration: time.Since(started)}
''',
        "response drain",
    )
    changed = changed or replaced

    if not changed:
        print("Deletion-under-load source already reconciled")
        return 0
    PATH.write_text(text, encoding="utf-8")
    print("Reconciled deletion-under-load source and HTTP connection reuse")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"DELETION LOAD SOURCE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
