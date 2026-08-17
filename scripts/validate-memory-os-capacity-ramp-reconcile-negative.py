#!/usr/bin/env python3
"""Prove capacity-ramp multi-authority reconcile rolls back fail-closed."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reconcile-memory-os-capacity-ramp-status.py"
CONTRACT = ROOT / "contracts/operations/capacity-ramp-contract.v1.json"
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("capacity_ramp_reconcile", SCRIPT)
    require(spec is not None and spec.loader is not None, "cannot load capacity ramp reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    module = load_module()
    originals = {path: path.read_bytes() for path in (CONTRACT, LOAD, STATUS)}
    contract = load_json(CONTRACT)
    load_contract = load_json(LOAD)
    status = load_json(STATUS)
    contract["_rollbackNegativeMarker"] = True
    load_contract["_rollbackNegativeMarker"] = True
    status["_rollbackNegativeMarker"] = True

    original_runner = module.run_validator

    def controlled_runner(path: Path, label: str, *args: str) -> None:
        if path == module.OPERABILITY_VALIDATOR:
            raise module.ReconcileFailure("controlled post-write operability failure")
        return original_runner(path, label, *args)

    module.run_validator = controlled_runner
    try:
        try:
            module.write_and_validate_transactionally(contract, load_contract, status)
        except module.ReconcileFailure as exc:
            require("controlled post-write operability failure" in str(exc), f"unexpected failure: {exc}")
        else:
            raise NegativeFailure("controlled post-write failure was accepted")
    finally:
        module.run_validator = original_runner

    for path, data in originals.items():
        require(path.read_bytes() == data, f"rollback failed for {path.relative_to(ROOT)}")
    print("PASS: capacity ramp reconcile rolls back all canonical authority files after post-write failure")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"CAPACITY RAMP RECONCILE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
