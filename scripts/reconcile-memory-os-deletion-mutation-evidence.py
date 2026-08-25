#!/usr/bin/env python3
"""Register Apply/upload-authorization pre-fence proof without overclaiming upload completion or production behavior."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MUTATION_CONTRACT_REL = Path("contracts/operations/deletion-prefence-mutation-linearization-contract.v1.json")
MUTATION_RESULT_REL = Path("docs/fixtures/memory-os-operability/deletion-prefence-mutation-linearization-results.sample.v1.json")
LOAD_REL = Path("contracts/operations/load-test-scenario-contract.v1.json")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
MUTATION_VALIDATOR_REL = Path("scripts/validate-memory-os-deletion-prefence-mutation-linearization.py")
LOAD_INDEX_VALIDATOR_REL = Path("scripts/validate-memory-os-load-evidence-index.py")
LOAD_VALIDATOR_REL = Path("scripts/validate-memory-os-load.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
MUTATION_CONTRACT = ROOT / MUTATION_CONTRACT_REL
MUTATION_RESULT = ROOT / MUTATION_RESULT_REL
LOAD_PATH = ROOT / LOAD_REL
STATUS_PATH = ROOT / STATUS_REL
MUTATION_VALIDATOR = ROOT / MUTATION_VALIDATOR_REL
LOAD_INDEX_VALIDATOR = ROOT / LOAD_INDEX_VALIDATOR_REL
LOAD_VALIDATOR = ROOT / LOAD_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL

REFS = (
    "contracts/operations/deletion-prefence-mutation-linearization-contract.v1.json",
    "services/import-api/internal/httpserver/deletion_prefence_mutation_linearization_test.go",
    "scripts/validate-memory-os-deletion-prefence-mutation-linearization.py",
    "scripts/reconcile-memory-os-deletion-prefence-mutation-linearization.py",
    ".github/workflows/deletion-prefence-mutation-linearization.yml",
    "docs/fixtures/memory-os-operability/deletion-prefence-mutation-linearization-results.sample.v1.json",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(path: Path, expected_relative: Path, label: str) -> None:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{label} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{label} authority drift",
    )


def enforce_runtime_authorities() -> None:
    for path, relative, label in (
        (MUTATION_CONTRACT, MUTATION_CONTRACT_REL, "mutation proof contract"),
        (MUTATION_RESULT, MUTATION_RESULT_REL, "mutation proof result"),
        (LOAD_PATH, LOAD_REL, "load contract"),
        (STATUS_PATH, STATUS_REL, "production operability status"),
        (MUTATION_VALIDATOR, MUTATION_VALIDATOR_REL, "mutation proof validator"),
        (LOAD_INDEX_VALIDATOR, LOAD_INDEX_VALIDATOR_REL, "load evidence-index validator"),
        (LOAD_VALIDATOR, LOAD_VALIDATOR_REL, "load validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
    ):
        require_exact_repo_file(path, relative, label)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def atomic_write_bytes(path: Path, data: bytes) -> None:
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write(path: Path, value: dict[str, Any]) -> None:
    atomic_write_bytes(path, (json.dumps(value, indent=2) + "\n").encode("utf-8"))


def run_validator(path: Path, *args: str) -> None:
    subprocess.run(["python", str(path), *args], cwd=ROOT, check=True)


def append_unique(values: list[Any], value: Any) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    enforce_runtime_authorities()
    run_validator(MUTATION_VALIDATOR, "--require-result")

    proof = load(MUTATION_CONTRACT)
    result = load(MUTATION_RESULT)
    readiness = proof.get("readiness")
    scenario = result.get("scenario")
    require(isinstance(readiness, dict), "mutation proof readiness missing")
    require(isinstance(scenario, dict), "mutation result scenario missing")
    require(readiness.get("exactSourceResultCommitted") is True, "mutation proof exact-source result is not committed")
    require(readiness.get("preFenceMutationLinearizationProven") is True, "mutation proof is not reconciled")
    require(scenario.get("result") == "PASS" and scenario.get("integrityResult") == "PASS", "mutation result is not PASS")
    require(scenario.get("authenticatedBeforeFence") == 32, "old-epoch session barrier incomplete")
    require(scenario.get("applyUnauthorizedAfterFence") == 16, "Apply rejection proof incomplete")
    require(scenario.get("uploadAuthorizationUnauthorizedAfterFence") == 16, "upload authorization rejection proof incomplete")
    for key in (
        "unexpectedStatusCount",
        "transportErrors",
        "preWorkerApplyConfirmationRows",
        "preWorkerMemoryItemRows",
        "preWorkerUploadAuthorizationRows",
        "preWorkerQuarantineRows",
        "finalOwnedRowCount",
    ):
        require(scenario.get(key) == 0, f"mutation evidence criterion drift: {key}")

    load_contract = load(LOAD_PATH)
    load_readiness = load_contract.get("readiness")
    evidence_refs = load_contract.get("evidenceRefs")
    deferred = load_contract.get("deferredScenarios")
    require(isinstance(load_readiness, dict), "load readiness missing")
    require(isinstance(evidence_refs, list), "load evidenceRefs missing")
    require(isinstance(deferred, list), "load deferredScenarios missing")
    require(load_readiness.get("productionEquivalentDependencies") is False, "local mutation proof cannot cross production-equivalent boundary")
    require(load_readiness.get("capacityBoundaryEstablished") is False, "local mutation proof cannot establish capacity boundary")
    require(load_readiness.get("sustainedSoakEvidence") is False, "local mutation proof cannot establish production-shaped soak")

    load_readiness["applyPreFenceInFlightLinearizationProven"] = True
    load_readiness["uploadAuthorizationPreFenceInFlightLinearizationProven"] = True
    load_readiness["uploadCompletionPreFenceInFlightLinearizationProven"] = False
    for ref in REFS:
        append_unique(evidence_refs, ref)

    deletion_deferred = next(
        (item for item in deferred if isinstance(item, dict) and item.get("scenarioId") == "deletion-under-load"),
        None,
    )
    require(isinstance(deletion_deferred, dict), "deletion-under-load deferred record missing")
    deletion_deferred["reason"] = (
        "post-fence former-session load, Preview requests authenticated before the fence, Apply and upload-authorization requests authenticated before the fence with zero pre-worker durable mutation, and bounded 24-account/four-worker deletion saturation now pass against local PostgreSQL and MinIO; "
        "upload-completion requests already in flight before the fence, host/process failure behavior, production dependency behavior and independently reviewed deletion-load thresholds remain deferred"
    )
    deletion_deferred["requiredDependencyMode"] = "PRODUCTION_EQUIVALENT"

    note = load_readiness.get("note")
    if isinstance(note, str):
        suffix = ". Apply and upload-authorization pre-fence mutation linearization are now proven locally with zero durable mutation; upload completion already in flight remains unproven."
        if not note.endswith(suffix):
            load_readiness["note"] = note.rstrip(".") + suffix

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO", "local mutation proof cannot reconcile into Production GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability areas missing")
    load_area = next((area for area in areas if isinstance(area, dict) and area.get("id") == "OPS-P0-006"), None)
    require(isinstance(load_area, dict), "OPS-P0-006 missing")
    require(load_area.get("status") == "PARTIAL", "local mutation proof cannot promote OPS-P0-006")
    existing = load_area.get("existingEvidence")
    missing = load_area.get("missingEvidence")
    refs = load_area.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-006 evidence structure invalid")

    append_unique(
        existing,
        "exact-source local pre-fence mutation proof pauses 16 Apply and 16 upload-authorization requests after epoch-1 session resolution, durably advances account deletion to epoch 2, then proves all 32 resume as 401 with zero transport errors and zero apply_confirmation, memory_item, upload_authorization or quarantine_object mutations before worker erasure",
    )
    old_fragments = (
        "pre-fence in-flight linearization for Apply and Upload authorization surfaces",
        "pre-fence in-flight linearization for Apply and Upload authorization surfaces,",
    )
    new_missing: list[Any] = []
    replaced = False
    for item in missing:
        if isinstance(item, str) and any(item.startswith(fragment) for fragment in old_fragments):
            new_missing.append(
                "pre-fence in-flight linearization for upload-completion requests, host/process failure behavior, production topology and independently reviewed deletion-load thresholds"
            )
            replaced = True
        else:
            new_missing.append(item)
    if not replaced:
        append_unique(
            new_missing,
            "pre-fence in-flight linearization for upload-completion requests, host/process failure behavior, production topology and independently reviewed deletion-load thresholds",
        )
    load_area["missingEvidence"] = new_missing
    for ref in REFS:
        append_unique(refs, ref)

    require(status.get("productionDecision") == "NO_GO", "production decision drift")
    require(load_area.get("status") == "PARTIAL", "OPS-P0-006 status drift")
    require(load_readiness.get("productionEquivalentDependencies") is False, "production equivalence drift")
    require(load_readiness.get("capacityBoundaryEstablished") is False, "capacity boundary drift")
    require(load_readiness.get("uploadCompletionPreFenceInFlightLinearizationProven") is False, "upload completion must remain unproven")

    original_load = LOAD_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    try:
        write(LOAD_PATH, load_contract)
        write(STATUS_PATH, status)
        run_validator(LOAD_INDEX_VALIDATOR)
        run_validator(LOAD_VALIDATOR)
        run_validator(OPERABILITY_VALIDATOR)
    except BaseException:
        atomic_write_bytes(LOAD_PATH, original_load)
        atomic_write_bytes(STATUS_PATH, original_status)
        raise

    print("Memory OS deletion mutation evidence reconciled")
    print("Apply pre-fence linearization: true")
    print("upload authorization pre-fence linearization: true")
    print("upload completion pre-fence linearization: false")
    print("OPS-P0-006: PARTIAL")
    print("Production: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION MUTATION EVIDENCE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
