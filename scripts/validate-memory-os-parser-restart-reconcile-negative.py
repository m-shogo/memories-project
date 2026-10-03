#!/usr/bin/env python3
"""Negative coverage for parser restart authority reconciliation."""

from __future__ import annotations

import importlib.util
import json
import stat
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


def expect_reconcile_failure(module, expected: str) -> None:
    try:
        module.main()
    except module.ReconcileFailure as exc:
        if expected not in str(exc):
            raise AssertionError(f"unexpected reconcile rejection: {exc}") from exc
    else:
        raise AssertionError(f"parser restart reconcile accepted invalid authority: {expected}")


def stale_status_bytes(module) -> bytes:
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
    return json.dumps(original_status, indent=2).encode("utf-8") + b"\n"



def prove_transport_binding(module) -> None:
    canonical_run = module.subprocess.run
    canonical_replace = module.os.replace

    def reject_mutable_run(*_args, **_kwargs):
        raise RuntimeError("mutable subprocess.run transport was invoked")

    def reject_mutable_replace(*_args, **_kwargs):
        raise RuntimeError("mutable os.replace transport was invoked")

    module.subprocess.run = reject_mutable_run
    module.os.replace = reject_mutable_replace
    try:
        if not module.source_is_ancestor("HEAD"):
            raise AssertionError("bound parser restart ancestry transport rejected HEAD")
        module.run_validator(module.CANONICAL_PARSER_VALIDATOR)
        with tempfile.TemporaryDirectory(prefix="parser-restart-transport-negative-") as tmp:
            target = Path(tmp) / "authority.json"
            target.write_bytes(b"before\\n")
            target.chmod(0o640)
            module.atomic_write_bytes(target, b"after\\n")
            if target.read_bytes() != b"after\\n":
                raise AssertionError("bound parser restart atomic transport did not publish payload")
            if stat.S_IMODE(target.stat().st_mode) != 0o640:
                raise AssertionError("bound parser restart atomic transport did not preserve mode")
    finally:
        module.subprocess.run = canonical_run
        module.os.replace = canonical_replace


def main() -> int:
    source_sha = "0" * 40

    module = load_reconciler()
    prove_transport_binding(module)
    with tempfile.TemporaryDirectory(prefix="memory-os-parser-restart-negative-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        status_path = root / "status.json"
        result_path.write_text(
            json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8"
        )
        original_bytes = stale_status_bytes(module)
        status_path.write_bytes(original_bytes)
        status_path.chmod(0o640)
        original_mode = stat.S_IMODE(status_path.stat().st_mode)

        module.RESULT_PATH = result_path
        module.STATUS_PATH = status_path
        module.source_is_ancestor = lambda _sha: True
        module.load_canonical_normalizer = lambda: (lambda value: value)

        calls: list[str] = []
        atomic_calls: list[tuple[Path, bytes]] = []
        canonical_atomic_write = module.atomic_write_bytes

        def tracked_atomic_write(path: Path, payload: bytes) -> None:
            atomic_calls.append((path, bytes(payload)))
            canonical_atomic_write(path, payload)

        def fail_after_write(validated_sha: str) -> None:
            if validated_sha != source_sha:
                raise AssertionError("unexpected source SHA passed to authority chain")
            calls.append(validated_sha)
            if len(calls) == 2:
                raise module.ReconcileFailure("synthetic post-write aggregate rejection")

        module.atomic_write_bytes = tracked_atomic_write
        module.validate_authority_chain = fail_after_write
        expect_reconcile_failure(module, "synthetic post-write aggregate rejection")

        if calls != [source_sha, source_sha]:
            raise AssertionError(f"authority chain call order drift: {calls}")
        if len(atomic_calls) != 2:
            raise AssertionError(f"atomic publish/rollback call count drift: {len(atomic_calls)}")
        if any(path != status_path for path, _payload in atomic_calls):
            raise AssertionError("atomic parser restart authority wrote an unexpected path")
        if atomic_calls[-1][1] != original_bytes:
            raise AssertionError("atomic parser restart rollback did not restore original bytes")
        if status_path.read_bytes() != original_bytes:
            raise AssertionError("parser restart reconcile did not roll back Production Status")
        if stat.S_IMODE(status_path.stat().st_mode) != original_mode:
            raise AssertionError("parser restart atomic publish/rollback did not preserve file mode")

    module = load_reconciler()
    with tempfile.TemporaryDirectory(prefix="memory-os-parser-restart-replace-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        status_path = root / "status.json"
        result_path.write_text(
            json.dumps({"commitSha": source_sha}) + "\n", encoding="utf-8"
        )
        original_bytes = stale_status_bytes(module)
        status_path.write_bytes(original_bytes)

        module.RESULT_PATH = result_path
        module.STATUS_PATH = status_path
        module.source_is_ancestor = lambda _sha: True
        module.load_canonical_normalizer = lambda: (lambda value: value)
        module.validate_authority_chain = lambda _sha: None
        canonical_atomic_write = module.atomic_write_bytes

        def reject_replace(_source, _target) -> None:
            raise OSError("synthetic atomic replacement rejection")

        def reject_atomic_write(path: Path, payload: bytes) -> None:
            canonical_atomic_write(path, payload, _replace=reject_replace)

        module.atomic_write_bytes = reject_atomic_write
        expect_reconcile_failure(module, "cannot atomically write authority")
        if status_path.read_bytes() != original_bytes:
            raise AssertionError("atomic replacement failure mutated parser restart authority")
        residues = list(root.glob(f".{status_path.name}.*.tmp"))
        if residues:
            raise AssertionError(f"atomic replacement failure left temp authority residue: {residues}")

    print("PASS: parser restart reconcile publishes atomically, preserves mode, and rolls back post-write authority rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
