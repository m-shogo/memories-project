#!/usr/bin/env python3
"""Prove load-foundation reconciles preserve authority and roll back fail-closed."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHORT_SCRIPT = ROOT / "scripts/reconcile-memory-os-short-stability-status.py"
CAPACITY_SCRIPT = ROOT / "scripts/reconcile-memory-os-capacity-ramp-status.py"
CONTROLLED_SCRIPT = ROOT / "scripts/reconcile-memory-os-controlled-saturation-ramp-status.py"
DELETION_SCRIPT = ROOT / "scripts/reconcile-memory-os-deletion-under-load-status.py"
SHORT_CONTRACT = ROOT / "contracts/operations/short-stability-sample-contract.v1.json"
CAPACITY_CONTRACT = ROOT / "contracts/operations/capacity-ramp-contract.v1.json"
CONTROLLED_CONTRACT = ROOT / "contracts/operations/controlled-saturation-ramp-contract.v1.json"
DELETION_CONTRACT = ROOT / "contracts/operations/deletion-under-load-contract.v1.json"
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
SHORT_RESULT = ROOT / "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json"
CONTROLLED_RESULT = ROOT / "docs/fixtures/memory-os-operability/controlled-saturation-ramp-results.sample.v1.json"
DELETION_RESULT = ROOT / "docs/fixtures/memory-os-operability/deletion-under-load-results.sample.v1.json"
STALE_SOAK_GAP = (
    "60-minute-or-longer repeated soak over PostgreSQL, object storage, parser, queue, deletion and authentication paths with RSS/heap/goroutine slope review and independently approved leak/stability criteria"
)
WEAK_SATURATION_GAP_PREFIXES = (
    "repeatability of the observed local PostgreSQL plus MinIO saturation signal",
    "repeatable local PostgreSQL plus MinIO saturation runs",
)


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected object: {path.relative_to(ROOT)}")
    return value


def run_short_preservation_case(module: ModuleType) -> None:
    originals = {path: path.read_bytes() for path in (SHORT_CONTRACT, LOAD, STATUS)}
    previous_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    try:
        result = load_json(SHORT_RESULT)
        source_sha = result.get("commitSha")
        require(isinstance(source_sha, str) and len(source_sha) == 40, "short stability result commitSha missing")
        os.environ["EXPECTED_COMMIT_SHA"] = source_sha
        require(module.main() == 0, "short stability reconcile did not succeed")

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


def run_short_rollback_case(module: ModuleType) -> None:
    originals = {path: path.read_bytes() for path in (SHORT_CONTRACT, LOAD, STATUS)}
    contract = load_json(SHORT_CONTRACT)
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
                contract, load_contract, status, load_json(SHORT_RESULT)["commitSha"]
            )
        except module.ReconcileFailure as exc:
            require("controlled soak authority failure" in str(exc), f"unexpected rollback failure: {exc}")
        else:
            raise NegativeFailure("controlled soak authority failure was accepted")
    finally:
        module.run_validator = original_runner

    for path, data in originals.items():
        require(path.read_bytes() == data, f"short rollback failed for {path.relative_to(ROOT)}")


def run_capacity_rollback_case(module: ModuleType) -> None:
    originals = {path: path.read_bytes() for path in (CAPACITY_CONTRACT, LOAD, STATUS)}
    contract = load_json(CAPACITY_CONTRACT)
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
            require("controlled post-write operability failure" in str(exc), f"unexpected capacity rollback failure: {exc}")
        else:
            raise NegativeFailure("controlled capacity post-write failure was accepted")
    finally:
        module.run_validator = original_runner

    for path, data in originals.items():
        require(path.read_bytes() == data, f"capacity rollback failed for {path.relative_to(ROOT)}")


def run_controlled_saturation_preservation_case(module: ModuleType) -> None:
    originals = {path: path.read_bytes() for path in (CONTROLLED_CONTRACT, LOAD, STATUS)}
    previous_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    original_validator = module.validate_post_write
    result = load_json(CONTROLLED_RESULT)
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and len(source_sha) == 40, "controlled saturation result commitSha missing")

    def no_op_validator(expected_sha: str) -> None:
        require(expected_sha == source_sha, "controlled saturation preservation used wrong source SHA")

    try:
        os.environ["EXPECTED_COMMIT_SHA"] = source_sha
        module.validate_post_write = no_op_validator
        require(module.main() == 0, "controlled saturation reconcile did not succeed")
        load_contract = load_json(LOAD)
        readiness = load_contract.get("readiness")
        require(isinstance(readiness, dict), "load readiness missing after controlled saturation reconcile")
        require(readiness.get("repeatableLocalDegradationSignalObserved") is True,
                "single controlled ramp downgraded established repeatability authority")
        status = load_json(STATUS)
        gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-006"), None)
        require(isinstance(gate, dict), "OPS-P0-006 missing after controlled saturation reconcile")
        missing = gate.get("missingEvidence")
        require(isinstance(missing, list), "OPS-P0-006 missingEvidence missing after controlled saturation reconcile")
        for item in missing:
            require(not (isinstance(item, str) and item.startswith(WEAK_SATURATION_GAP_PREFIXES)),
                    "single controlled ramp reintroduced a superseded repeatability blocker")
        require(status.get("productionDecision") == "NO_GO", "controlled saturation reconcile changed productionDecision")
    finally:
        module.validate_post_write = original_validator
        for path, data in originals.items():
            path.write_bytes(data)
        if previous_sha is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = previous_sha


def run_controlled_saturation_rollback_case(module: ModuleType) -> None:
    originals = {path: path.read_bytes() for path in (CONTROLLED_CONTRACT, LOAD, STATUS)}
    controlled = load_json(CONTROLLED_CONTRACT)
    load_contract = load_json(LOAD)
    status = load_json(STATUS)
    controlled["_rollbackNegativeMarker"] = True
    load_contract["_rollbackNegativeMarker"] = True
    status["_rollbackNegativeMarker"] = True
    result = load_json(CONTROLLED_RESULT)
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and len(source_sha) == 40, "controlled saturation result commitSha missing")
    original_validator = module.validate_post_write

    def controlled_validator(expected_sha: str) -> None:
        require(expected_sha == source_sha, "controlled saturation rollback used wrong source SHA")
        raise RuntimeError("controlled post-write saturation validation failure")

    module.validate_post_write = controlled_validator
    try:
        try:
            module.write_transactionally(controlled, load_contract, status, source_sha)
        except RuntimeError as exc:
            require("controlled post-write saturation validation failure" in str(exc),
                    f"unexpected controlled saturation rollback failure: {exc}")
        else:
            raise NegativeFailure("controlled saturation post-write failure was accepted")
    finally:
        module.validate_post_write = original_validator

    for path, data in originals.items():
        require(path.read_bytes() == data, f"controlled saturation rollback failed for {path.relative_to(ROOT)}")


def run_deletion_preservation_case(module: ModuleType) -> None:
    originals = {path: path.read_bytes() for path in (DELETION_CONTRACT, LOAD, STATUS)}
    previous_sha = os.environ.get("EXPECTED_COMMIT_SHA")
    result = load_json(DELETION_RESULT)
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and len(source_sha) == 40, "deletion load result commitSha missing")
    load_before = load_json(LOAD)
    deferred_before = load_before.get("deferredScenarios")
    readiness_before = load_before.get("readiness")
    require(isinstance(deferred_before, list) and isinstance(readiness_before, dict),
            "canonical deletion load authority missing")
    deletion_before = next(
        (row for row in deferred_before if isinstance(row, dict) and row.get("scenarioId") == "deletion-under-load"),
        None,
    )
    require(isinstance(deletion_before, dict), "canonical deletion-under-load deferred row missing")
    reason_before = deletion_before.get("reason")
    note_before = readiness_before.get("note")
    require(isinstance(reason_before, str) and reason_before, "canonical deletion reason missing")
    require(isinstance(note_before, str) and note_before, "canonical load note missing")

    try:
        os.environ["EXPECTED_COMMIT_SHA"] = source_sha
        require(module.main() == 0, "deletion-under-load reconcile did not succeed")
        load_after = load_json(LOAD)
        readiness_after = load_after.get("readiness")
        deferred_after = load_after.get("deferredScenarios")
        require(isinstance(readiness_after, dict) and isinstance(deferred_after, list),
                "load authority missing after deletion reconcile")
        deletion_after = next(
            (row for row in deferred_after if isinstance(row, dict) and row.get("scenarioId") == "deletion-under-load"),
            None,
        )
        require(isinstance(deletion_after, dict), "deletion deferred row missing after reconcile")
        require(deletion_after.get("reason") == reason_before,
                "deletion reconcile downgraded stronger deferred authority wording")
        require(readiness_after.get("note") == note_before,
                "deletion reconcile overwrote stronger aggregate load note")
        require(module.stronger_deletion_authority_present(readiness_after),
                "stronger deletion authority disappeared during reconcile")

        status = load_json(STATUS)
        gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-006"), None)
        require(isinstance(gate, dict), "OPS-P0-006 missing after deletion reconcile")
        missing = gate.get("missingEvidence")
        require(isinstance(missing, list), "OPS-P0-006 missingEvidence missing after deletion reconcile")
        require(module.LEGACY_DELETION_GAP not in missing,
                "deletion reconcile reintroduced superseded pre-fence/saturation blocker")
        require(status.get("productionDecision") == "NO_GO", "deletion reconcile changed productionDecision")
    finally:
        for path, data in originals.items():
            path.write_bytes(data)
        if previous_sha is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = previous_sha


def run_deletion_rollback_case(module: ModuleType) -> None:
    originals = {path: path.read_bytes() for path in (DELETION_CONTRACT, LOAD, STATUS)}
    contract = load_json(DELETION_CONTRACT)
    load_contract = load_json(LOAD)
    status = load_json(STATUS)
    contract["_rollbackNegativeMarker"] = True
    load_contract["_rollbackNegativeMarker"] = True
    status["_rollbackNegativeMarker"] = True
    original_runner = module.run_validator

    def controlled_runner(path: Path, label: str, *args: str) -> None:
        if path == module.OPERABILITY_VALIDATOR:
            raise module.ReconcileFailure("controlled deletion post-write operability failure")
        return None

    module.run_validator = controlled_runner
    try:
        try:
            module.write_and_validate_transactionally(contract, load_contract, status)
        except module.ReconcileFailure as exc:
            require("controlled deletion post-write operability failure" in str(exc),
                    f"unexpected deletion rollback failure: {exc}")
        else:
            raise NegativeFailure("controlled deletion post-write failure was accepted")
    finally:
        module.run_validator = original_runner

    for path, data in originals.items():
        require(path.read_bytes() == data, f"deletion rollback failed for {path.relative_to(ROOT)}")


def main() -> int:
    short = load_module("short_stability_reconcile", SHORT_SCRIPT)
    capacity = load_module("capacity_ramp_reconcile", CAPACITY_SCRIPT)
    controlled = load_module("controlled_saturation_reconcile", CONTROLLED_SCRIPT)
    deletion = load_module("deletion_load_reconcile", DELETION_SCRIPT)
    run_short_preservation_case(short)
    run_short_rollback_case(short)
    run_capacity_rollback_case(capacity)
    run_controlled_saturation_preservation_case(controlled)
    run_controlled_saturation_rollback_case(controlled)
    run_deletion_preservation_case(deletion)
    run_deletion_rollback_case(deletion)
    print("PASS: load-foundation reconciles preserve stronger authority and roll back fail-closed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"LOAD FOUNDATION RECONCILE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
