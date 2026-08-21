#!/usr/bin/env python3
"""Prove upload-completion proof reconcile authority identity and rollback are fail-closed."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-prefence-upload-completion.py"
ALTERNATE_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
ALTERNATE_CONTRACT = ROOT / "contracts/operations/production-operability-status.json"
ALTERNATE_RESULT = ROOT / "docs/fixtures/memory-os-operability/deletion-lease-recovery-results.sample.v1.json"
SOURCE_SHA = "1" * 40


def load_module():
    spec = importlib.util.spec_from_file_location("upload_completion_proof_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load upload-completion proof reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def expect_identity_rejection(module, attribute: str, replacement: Path, original_contract: bytes) -> None:
    original = getattr(module, attribute)
    setattr(module, attribute, replacement)
    try:
        try:
            module.validate_authority_identity()
        except module.Fail:
            pass
        else:
            raise AssertionError(f"{attribute} substitution was accepted")
        if module.CANONICAL_CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError(f"{attribute} rejection mutated canonical contract")
    finally:
        setattr(module, attribute, original)


def expect_post_write_rollback(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-upload-completion-proof-") as tmp:
        root = Path(tmp)
        contract = root / "contract.json"
        write_json(contract, {"readiness": {"productionReady": False}})
        before = contract.read_bytes()
        candidate = {"readiness": {"productionReady": False, "exactSourceResultCommitted": True}}

        original_contract_path = module.CONTRACT_PATH
        original_run_validator = module.run_validator
        original_atomic_write = module.atomic_write_bytes
        module.CONTRACT_PATH = contract

        def reject_post_write(_expected: str) -> None:
            raise RuntimeError("synthetic upload-completion post-write validation failure")

        module.run_validator = reject_post_write
        try:
            try:
                module.write_contract_transactionally(candidate, SOURCE_SHA)
            except RuntimeError as exc:
                if "synthetic upload-completion post-write validation failure" not in str(exc):
                    raise
            else:
                raise AssertionError("post-write validator rejection was accepted")
            if contract.read_bytes() != before:
                raise AssertionError("proof contract changed after rejected reconcile")
        finally:
            module.CONTRACT_PATH = original_contract_path
            module.run_validator = original_run_validator
            module.atomic_write_bytes = original_atomic_write


def main() -> int:
    module = load_module()
    original_contract = module.CANONICAL_CONTRACT_PATH.read_bytes()

    module.validate_authority_identity()
    expect_identity_rejection(module, "VALIDATOR", ALTERNATE_VALIDATOR, original_contract)
    expect_identity_rejection(module, "CONTRACT_PATH", ALTERNATE_CONTRACT, original_contract)
    expect_identity_rejection(module, "RESULT_PATH", ALTERNATE_RESULT, original_contract)
    expect_post_write_rollback(module)

    print("PASS: upload-completion proof reconcile authority and rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
