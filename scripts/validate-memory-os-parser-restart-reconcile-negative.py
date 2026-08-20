#!/usr/bin/env python3
"""Negative coverage for parser restart authority reconciliation."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-parser-restart-matrix.py"


def load_reconciler():
    spec = importlib.util.spec_from_file_location(
        "memory_os_parser_restart_reconcile_negative", RECONCILER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load parser restart reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_reconciler()
    source_sha = "0" * 40
    with tempfile.TemporaryDirectory(prefix="memory-os-parser-restart-negative-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        status_path = root / "status.json"
        result_path.write_text(
            json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8"
        )
        original_status = {
            "productionDecision": "NO_GO",
            "areas": [
                {
                    "id": "OPS-P0-009",
                    "status": "PARTIAL",
                    "existingEvidence": [],
                    "missingEvidence": [module.OLD_MISSING],
                    "evidenceRefs": [],
                }
            ],
        }
        original_bytes = json.dumps(original_status, indent=2) .encode("utf-8") + b"\n"
        status_path.write_bytes(original_bytes)

        module.RESULT_PATH = result_path
        module.STATUS_PATH = status_path
        module.source_is_ancestor = lambda _sha: True
        module.load_canonical_normalizer = lambda: (lambda value: value)

        calls: list[str] = []

        def fail_after_write(validated_sha: str) -> None:
            if validated_sha != source_sha:
                raise AssertionError("unexpected source SHA passed to authority chain")
            calls.append(validated_sha)
            if len(calls) == 2:
                raise module.ReconcileFailure("synthetic post-write aggregate rejection")

        module.validate_authority_chain = fail_after_write

        try:
            module.main()
        except module.ReconcileFailure as exc:
            if "synthetic post-write aggregate rejection" not in str(exc):
                raise AssertionError(f"unexpected reconcile rejection: {exc}") from exc
        else:
            raise AssertionError("parser restart reconcile accepted post-write validator failure")

        if calls != [source_sha, source_sha]:
            raise AssertionError(f"authority chain call order drift: {calls}")
        if status_path.read_bytes() != original_bytes:
            raise AssertionError("parser restart reconcile did not roll back Production Status")

    print("PASS: parser restart reconcile rolls back after post-write authority rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
