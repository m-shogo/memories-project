#!/usr/bin/env python3
"""Negative proof for database commit outage authority transaction."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-database-commit-outage.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_database_outage_reconcile_negative", RECONCILER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load database outage reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    source_sha = "0" * 40
    with tempfile.TemporaryDirectory(prefix="memory-os-database-outage-negative-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        status_path = root / "status.json"
        result_path.write_text(json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8")
        status = {
            "productionDecision": "NO_GO",
            "areas": [
                {
                    "id": "OPS-P0-009",
                    "status": "PARTIAL",
                    "existingEvidence": [],
                    "missingEvidence": [
                        module.OLD_MISSING,
                        "mixed-version failure",
                        "production multi-instance",
                        "production-shaped object-store",
                        "production-shaped PostgreSQL",
                        "host or container restart",
                        "expired sessions",
                    ],
                    "evidenceRefs": [],
                }
            ],
        }
        original_bytes = json.dumps(status, indent=2).encode("utf-8") + b"\n"
        status_path.write_bytes(original_bytes)

        module.RESULT_PATH = result_path
        module.STATUS_PATH = status_path
        module.source_is_ancestor = lambda _sha: True

        calls: list[str] = []

        def reject_after_write(validated_sha: str) -> None:
            calls.append(validated_sha)
            if len(calls) == 2:
                raise module.ReconcileFailure("synthetic post-write aggregate rejection")

        module.validate_authority_chain = reject_after_write
        try:
            module.main()
        except module.ReconcileFailure as exc:
            if "synthetic post-write aggregate rejection" not in str(exc):
                raise RuntimeError(f"unexpected database outage rejection: {exc}") from exc
        else:
            raise RuntimeError("database outage reconcile accepted post-write aggregate rejection")

        if calls != [source_sha, source_sha]:
            raise RuntimeError(f"database outage validator order drift: {calls}")
        if status_path.read_bytes() != original_bytes:
            raise RuntimeError("database outage reconcile did not roll back Production Status")

    print("PASS: database outage reconcile delegates canonical authority and rolls back after aggregate rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
