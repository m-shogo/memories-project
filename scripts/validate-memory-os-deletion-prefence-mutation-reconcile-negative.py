#!/usr/bin/env python3
"""Prove pre-fence mutation proof reconcile rolls back after canonical rejection."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-prefence-mutation-linearization.py"
SOURCE_SHA = "2" * 40


def load_module():
    spec = importlib.util.spec_from_file_location("mutation_proof_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load mutation proof reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    module = load_module()
    module.validate_authority_identity()
    before = module.CANONICAL_CONTRACT_PATH.read_bytes()
    candidate = json.loads(before.decode("utf-8"))
    readiness = candidate.setdefault("readiness", {})
    readiness["preFenceMutationLinearizationProven"] = not bool(
        readiness.get("preFenceMutationLinearizationProven", False)
    )
    candidate_bytes = (json.dumps(candidate, indent=2) + "\n").encode("utf-8")
    if candidate_bytes == before:
        raise AssertionError("rollback fixture did not change canonical contract candidate")

    original_run_validator = module.run_validator

    def reject_post_write(_expected: str) -> None:
        raise RuntimeError("synthetic post-write pre-fence mutation rejection")

    module.run_validator = reject_post_write
    try:
        try:
            module.write_contract_transactionally(candidate, SOURCE_SHA)
        except RuntimeError as exc:
            if "synthetic post-write pre-fence mutation rejection" not in str(exc):
                raise
        else:
            raise AssertionError("canonical post-write rejection must fail mutation proof reconcile")

        if module.CANONICAL_CONTRACT_PATH.read_bytes() != before:
            raise AssertionError("canonical mutation proof contract changed after rejected reconcile")
        if list(module.CANONICAL_CONTRACT_PATH.parent.glob(f".{module.CANONICAL_CONTRACT_PATH.name}.*.tmp")):
            raise AssertionError("canonical mutation proof rollback left atomic temp residue")
    finally:
        module.run_validator = original_run_validator
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != before:
            module.CANONICAL_ATOMIC_WRITE_BYTES(module.CANONICAL_CONTRACT_PATH, before)

    print("PASS: pre-fence mutation proof reconcile rolls back after canonical rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
