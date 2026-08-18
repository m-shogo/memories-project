#!/usr/bin/env python3
"""Prove migration operation authority rollback and monotonic composition."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATOR = ROOT / "scripts/create-memory-os-migration-operation-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-migration-operation-evidence.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-operation-evidence.py"
CONTRACT = ROOT / "contracts/operations/migration-operation-evidence-contract.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prove_stronger_authority_is_preserved(module, lifecycle_payload: bytes) -> None:
    lifecycle = json.loads(lifecycle_payload.decode("utf-8"))
    readiness = lifecycle["readiness"]
    for field in module.STRONGER_LIFECYCLE_FIELDS:
        readiness[field] = True
    normalized = module.normalize_lifecycle(lifecycle)
    normalized_readiness = normalized["readiness"]
    for field in module.STRONGER_LIFECYCLE_FIELDS:
        require(normalized_readiness.get(field) is True,
                f"weaker operation evidence rolled back stronger lifecycle authority: {field}")


def prove_canonical_ledger_preappend_guard(tmp_path: Path) -> None:
    creator = load_module(CREATOR, "migration_operation_creator_negative")
    fail_validator = tmp_path / "ledger-fail.py"
    fail_validator.write_text("raise SystemExit(1)\n", encoding="utf-8")
    creator.VALIDATOR = fail_validator

    rejected = False
    try:
        creator.validate_canonical_ledger_before_append(creator.DEFAULT_LEDGER)
    except creator.EvidenceValidationError as exc:
        require("failed validation before append" in str(exc),
                f"unexpected canonical ledger rejection: {exc}")
        rejected = True
    require(rejected, "canonical append did not require current ledger validation")

    custom_ledger = tmp_path / "isolated-ledger"
    creator.validate_canonical_ledger_before_append(custom_ledger)


def prove_contract_guard_is_required(contract_payload: bytes) -> None:
    candidate = json.loads(contract_payload.decode("utf-8"))
    candidate["appendOnlyGuards"]["canonicalLedgerMustValidateBeforeAppend"] = False
    CONTRACT.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        require(completed.returncode != 0,
                "standalone validator accepted disabled canonical pre-append guard")
    finally:
        CONTRACT.write_bytes(contract_payload)


def main() -> int:
    originals = {
        CONTRACT: CONTRACT.read_bytes(),
        LIFECYCLE: LIFECYCLE.read_bytes(),
        STATUS: STATUS.read_bytes(),
    }
    module = load_module(RECONCILER, "migration_operation_reconciler")
    prove_stronger_authority_is_preserved(module, originals[LIFECYCLE])
    prove_contract_guard_is_required(originals[CONTRACT])

    candidates = [json.loads(payload.decode("utf-8")) for payload in originals.values()]
    for candidate in candidates:
        candidate["rollbackProbe"] = "must-not-persist"

    with tempfile.TemporaryDirectory(prefix="migration-operation-reconcile-negative-") as tmp:
        tmp_path = Path(tmp)
        prove_canonical_ledger_preappend_guard(tmp_path)
        pass_validator = tmp_path / "pass.py"
        fail_validator = tmp_path / "fail.py"
        pass_validator.write_text("raise SystemExit(0)\n", encoding="utf-8")
        fail_validator.write_text("raise SystemExit(1)\n", encoding="utf-8")
        module.POST_WRITE_VALIDATORS = (pass_validator, pass_validator, fail_validator)

        rejected = False
        try:
            module.commit_validated_triple(*candidates)
        except module.ReconcileFailure as exc:
            require("failed validation" in str(exc), f"unexpected rejection: {exc}")
            rejected = True

    require(rejected, "post-write validation failure was not rejected")
    for path, payload in originals.items():
        require(path.read_bytes() == payload,
                f"{path.name} changed after rejected migration operation reconcile")
    print("PASS: migration operation append and reconcile are fail-closed and rollback-safe")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
