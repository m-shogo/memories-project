#!/usr/bin/env python3
"""Negative proof for v2 chaos authority transaction."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-chaos-failure-drills-v2.py"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_chaos_v2_reconcile_negative", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v2 chaos reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_reconcile_failure(module, expected: str) -> None:
    try:
        module.main()
    except module.ReconcileFailure as exc:
        if expected not in str(exc):
            raise RuntimeError(f"unexpected v2 reconcile rejection: {exc}") from exc
    else:
        raise RuntimeError(f"v2 chaos reconcile accepted invalid authority: {expected}")


def stale_status_bytes() -> bytes:
    status = {
        "productionDecision": "NO_GO",
        "areas": [
            {
                "id": "OPS-P0-009",
                "status": "PARTIAL",
                "existingEvidence": [],
                "missingEvidence": ["object-store outage drill"],
                "evidenceRefs": [],
            }
        ],
    }
    return json.dumps(status, indent=2).encode("utf-8") + b"\n"


def main() -> int:
    module = load_module()
    source_sha = "0" * 40

    canonical_result = module.RESULT_PATH
    canonical_status = module.STATUS_PATH
    try:
        module.RESULT_PATH = ROOT / "README.md"
        module.STATUS_PATH = ROOT / "SECURITY.md"
        expect_reconcile_failure(module, "fixture must remain outside repository")
    finally:
        module.RESULT_PATH = canonical_result
        module.STATUS_PATH = canonical_status

    with tempfile.TemporaryDirectory(prefix="memory-os-chaos-v2-negative-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        status_path = root / "status.json"
        result_path.write_text(json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8")
        original_bytes = stale_status_bytes()
        status_path.write_bytes(original_bytes)

        module.RESULT_PATH = result_path
        module.STATUS_PATH = status_path
        module.source_is_ancestor = lambda _sha: True
        module.load_canonical_normalizer = lambda: (lambda value: value)
        module.NEW_REFS = ()

        calls: list[str] = []
        atomic_calls: list[tuple[Path, bytes]] = []
        canonical_atomic_write = module.atomic_write_bytes

        def tracked_atomic_write(path: Path, payload: bytes) -> None:
            atomic_calls.append((path, bytes(payload)))
            canonical_atomic_write(path, payload)

        def reject_after_write(validated_sha: str) -> None:
            calls.append(validated_sha)
            if len(calls) == 2:
                raise module.ReconcileFailure("synthetic post-write aggregate rejection")

        module.atomic_write_bytes = tracked_atomic_write
        module.validate_authority_chain = reject_after_write
        expect_reconcile_failure(module, "synthetic post-write aggregate rejection")

        if calls != [source_sha, source_sha]:
            raise RuntimeError(f"v2 authority validation order drift: {calls}")
        if len(atomic_calls) != 2:
            raise RuntimeError(f"v2 atomic publish/rollback call count drift: {len(atomic_calls)}")
        if any(path != status_path for path, _payload in atomic_calls):
            raise RuntimeError("v2 atomic authority wrote an unexpected path")
        if atomic_calls[-1][1] != original_bytes:
            raise RuntimeError("v2 atomic rollback did not restore original bytes")
        if status_path.read_bytes() != original_bytes:
            raise RuntimeError("v2 chaos reconcile did not roll back Production Status")

    module = load_module()
    with tempfile.TemporaryDirectory(prefix="memory-os-chaos-v2-replace-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        status_path = root / "status.json"
        result_path.write_text(json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8")
        original_bytes = stale_status_bytes()
        status_path.write_bytes(original_bytes)

        module.RESULT_PATH = result_path
        module.STATUS_PATH = status_path
        module.source_is_ancestor = lambda _sha: True
        module.load_canonical_normalizer = lambda: (lambda value: value)
        module.NEW_REFS = ()
        module.validate_authority_chain = lambda _sha: None
        canonical_replace = module.os.replace

        def reject_replace(_source, _target) -> None:
            raise OSError("synthetic atomic replacement rejection")

        try:
            module.os.replace = reject_replace
            expect_reconcile_failure(module, "cannot atomically write authority")
        finally:
            module.os.replace = canonical_replace
        if status_path.read_bytes() != original_bytes:
            raise RuntimeError("v2 atomic replacement failure mutated Production Status")
        residues = list(root.glob(f".{status_path.name}.*.tmp"))
        if residues:
            raise RuntimeError(f"v2 atomic replacement failure left temp authority residue: {residues}")

    print("PASS: v2 chaos reconcile pins data authority, publishes atomically, and rolls back after aggregate rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
