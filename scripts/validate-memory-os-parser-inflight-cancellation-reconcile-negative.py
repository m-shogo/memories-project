#!/usr/bin/env python3
"""Negative coverage for parser in-flight cancellation authority reconciliation."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-parser-inflight-cancellation.py"


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_parser_inflight_cancellation_reconcile_negative", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load parser in-flight cancellation reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_reconcile_failure(module, expected: str) -> None:
    try:
        module.main()
    except module.ReconcileFailure as exc:
        if expected not in str(exc):
            raise AssertionError(f"unexpected reconcile rejection: {exc}") from exc
    else:
        raise AssertionError(f"parser cancellation reconcile accepted invalid authority: {expected}")


def main() -> int:
    source_sha = "0" * 40

    module = load_reconciler()
    canonical_status_bytes = module.CANONICAL_STATUS_PATH.read_bytes()
    canonical_source_check = module.source_is_ancestor
    try:
        # This case isolates executable-authority rejection. Shallow CI checkouts
        # need not contain the historical exact-source result commit, so ancestry
        # is fixed true here rather than allowing it to mask the intended check.
        module.source_is_ancestor = lambda _sha: True
        with tempfile.TemporaryDirectory(prefix="memory-os-parser-cancel-authority-") as tmp:
            substitute = Path(tmp) / "validator.py"
            substitute.write_text("raise SystemExit(0)\n", encoding="utf-8")
            module.OPERABILITY_VALIDATOR = substitute
            expect_reconcile_failure(module, "operability validator authority drift")
    finally:
        module.source_is_ancestor = canonical_source_check
    if module.CANONICAL_STATUS_PATH.read_bytes() != canonical_status_bytes:
        raise AssertionError("authority substitution mutated canonical Production Status")

    module = load_reconciler()
    with tempfile.TemporaryDirectory(prefix="memory-os-parser-cancel-rollback-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        status_path = root / "status.json"
        result_path.write_text(json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8")

        # Start from the real conservative authority so stronger unresolved
        # production gaps stay present. Then make only the in-flight slice stale
        # enough to force a write before injecting the post-write failure.
        status = module.load(module.CANONICAL_STATUS_PATH)
        gate = next(
            item for item in status.get("areas", [])
            if isinstance(item, dict) and item.get("id") == "OPS-P0-009"
        )
        missing = gate.get("missingEvidence")
        existing = gate.get("existingEvidence")
        if not isinstance(missing, list) or not isinstance(existing, list):
            raise RuntimeError("OPS-P0-009 arrays missing for rollback fixture")
        if module.OLD_MISSING not in missing:
            missing.append(module.OLD_MISSING)
        for item in module.NEW_EXISTING:
            while item in existing:
                existing.remove(item)

        original_bytes = json.dumps(status, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
        status_path.write_bytes(original_bytes)

        module.RESULT_PATH = result_path
        module.STATUS_PATH = status_path
        module.source_is_ancestor = lambda _sha: True
        module.load_normalizer = lambda *_args, **_kwargs: (lambda value: value)
        calls: list[str] = []

        def fail_after_write(validated_sha: str) -> None:
            if validated_sha != source_sha:
                raise AssertionError("unexpected source SHA passed to authority chain")
            calls.append(validated_sha)
            if len(calls) == 2:
                raise module.ReconcileFailure("synthetic post-write aggregate rejection")

        module.validate_authority_chain = fail_after_write
        expect_reconcile_failure(module, "synthetic post-write aggregate rejection")
        if calls != [source_sha, source_sha]:
            raise AssertionError(f"authority chain call order drift: {calls}")
        if status_path.read_bytes() != original_bytes:
            raise AssertionError("parser cancellation reconcile did not roll back Production Status")

    print("PASS: parser in-flight cancellation reconcile rejects authority substitution and rolls back post-write aggregate rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
