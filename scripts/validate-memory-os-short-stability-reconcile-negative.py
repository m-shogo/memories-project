#!/usr/bin/env python3
"""Prove short stability reconcile cannot downgrade repeated LOCAL_LONG_SOAK authority."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/reconcile-memory-os-short-stability-status.py"
CONTRACT = ROOT / "contracts/operations/short-stability-sample-contract.v1.json"
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json"
STALE_SOAK_GAP = (
    "60-minute-or-longer repeated soak over PostgreSQL, object storage, parser, queue, deletion and authentication paths with RSS/heap/goroutine slope review and independently approved leak/stability criteria"
)


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("short_stability_reconcile", SCRIPT)
    require(spec is not None and spec.loader is not None, "cannot load short stability reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected object: {path.relative_to(ROOT)}")
    return value


def run_preservation_case(module: ModuleType) -> None:
    originals = {path: path.read_bytes() for path in (CONTRACT, LOAD, STATUS)}
    previous_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    try:
        result = load_json(RESULT)
        source_sha = result.get("commitSha")
        require(isinstance(source_sha, str) and len(source_sha) == 40, "short stability result commitSha missing")
        os.environ["EXPECTED_COMMIT_SHA"] = source_sha
        code = module.main()
        require(code == 0, "short stability reconcile did not succeed")

        load_contract = load_json(LOAD)
        readiness = load_contract.get("readiness")
        require(isinstance(readiness, dict), "load readiness missing after reconcile")
        require(readiness.get("localSustainedSoakEvidence") is True,
                "short stability reconcile downgraded local sustained-soak evidence")
        deferred = load_contract.get("deferredScenarios")
        require(isinstance(deferred, list), "deferred scenarios missing after reconcile")
        soak = next((row for row in deferred if isinstance(row, dict) and row.get("scenarioId") == "soak"), None)
        require(isinstance(soak, dict), "canonical soak deferred row missing")
        reason = soak.get("reason")
        require(isinstance(reason, str) and "repeated LOCAL_LONG_SOAK execution" in reason,
                "short stability reconcile replaced repeated-soak authority with short-sample wording")

        status = load_json(STATUS)
        require(status.get("productionDecision") == "NO_GO", "productionDecision changed")
        gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-006"), None)
        require(isinstance(gate, dict), "OPS-P0-006 missing")
        missing = gate.get("missingEvidence")
        require(isinstance(missing, list), "OPS-P0-006 missingEvidence missing")
        require(STALE_SOAK_GAP not in missing,
                "completed repeated-soak gap was reintroduced by short stability reconcile")
    finally:
        for path, data in originals.items():
            path.write_bytes(data)
        if previous_sha is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = previous_sha


def run_rollback_case(module: ModuleType) -> None:
    originals = {path: path.read_bytes() for path in (CONTRACT, LOAD, STATUS)}
    contract = load_json(CONTRACT)
    load_contract = load_json(LOAD)
    status = load_json(STATUS)
    contract["_rollbackNegativeMarker"] = True
    load_contract["_rollbackNegativeMarker"] = True
    status["_rollbackNegativeMarker"] = True

    original_runner = module.run_validator

    def controlled_runner(path: Path, label: str, *args: str) -> None:
        if path == module.SOAK_RECONCILER:
            raise module.ReconcileFailure("controlled soak authority failure")
        return original_runner(path, label, *args)

    module.run_validator = controlled_runner
    try:
        try:
            module.write_and_validate_transactionally(
                contract,
                load_contract,
                status,
                load_json(RESULT)["commitSha"],
            )
        except module.ReconcileFailure as exc:
            require("controlled soak authority failure" in str(exc), f"unexpected rollback failure: {exc}")
        else:
            raise NegativeFailure("controlled soak authority failure was accepted")
    finally:
        module.run_validator = original_runner

    for path, data in originals.items():
        require(path.read_bytes() == data, f"rollback failed for {path.relative_to(ROOT)}")


def main() -> int:
    module = load_module()
    run_preservation_case(module)
    run_rollback_case(module)
    print("PASS: short stability reconcile preserves repeated soak authority and rolls back fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"SHORT STABILITY RECONCILE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
