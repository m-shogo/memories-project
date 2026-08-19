#!/usr/bin/env python3
"""Validate fail-closed admission for deletion-worker physical host/node failure evidence."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/deletion-worker-host-failure-contract.v1.json"
GENERATION = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GENERATION_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
NO_GENERATION_LIMITATION = "no production-equivalent environment generation is registered"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_generation_writer():
    try:
        resolved = GENERATION_WRITER.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail("canonical environment generation writer missing or escapes repository") from exc
    require(resolved == GENERATION_WRITER.relative_to(ROOT), "environment generation writer authority drift")
    require(GENERATION_WRITER.is_file(), "canonical environment generation writer must be a file")
    spec = importlib.util.spec_from_file_location(
        "memory_os_environment_generation_writer_for_host_failure",
        GENERATION_WRITER,
    )
    require(spec is not None and spec.loader is not None, "cannot load canonical environment generation writer")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - convert dependency failures into domain failure
        raise Fail(f"cannot load canonical environment generation writer: {exc}") from exc
    require(callable(getattr(module, "validate_registry_for_append", None)), "generation registry validator missing")
    return module


def canonical_generation_count() -> int:
    generation = load(GENERATION)
    registry = load(REGISTRY)
    generation_writer = load_generation_writer()
    try:
        generation_rows = generation_writer.validate_registry_for_append(registry)
    except Exception as exc:  # noqa: BLE001 - shared authority must fail closed
        raise Fail(f"environment generation registry authority invalid: {exc}") from exc

    registered = registry.get("registeredGenerationCount")
    require(isinstance(registered, int) and not isinstance(registered, bool) and registered >= 0, "registered generation count invalid")
    require(len(generation_rows) == registered, "generation registry row/count drift")

    generation_boundary = generation.get("currentBoundary")
    require(isinstance(generation_boundary, dict), "generation currentBoundary missing")
    boundary_count = generation_boundary.get("registeredGenerationCount")
    require(isinstance(boundary_count, int) and not isinstance(boundary_count, bool), "generation contract registered count invalid")
    require(boundary_count == registered, "generation contract/registry count drift")
    require(generation_boundary.get("productionEvidence") is False, "generation contract cannot claim production evidence")
    require(generation_boundary.get("productionReady") is False, "generation contract cannot claim production readiness")
    require(generation_boundary.get("productionDecision") == "NO_GO", "generation contract must remain NO_GO")
    return registered


def validate_generation_projection(contract: dict[str, Any], registered: int) -> None:
    require(isinstance(registered, int) and not isinstance(registered, bool) and registered >= 0, "registered generation count invalid")
    generation_available = registered > 0

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "currentBoundary required")
    require(boundary.get("environmentGenerationAvailable") is generation_available, "host-failure generation availability drift")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness required")
    require(readiness.get("environmentGenerationAvailable") is generation_available, "host-failure readiness generation availability drift")

    limitations = contract.get("limitations")
    require(isinstance(limitations, list) and all(isinstance(item, str) for item in limitations), "limitations required")
    if generation_available:
        require(NO_GENERATION_LIMITATION not in limitations, "registered generation cannot retain missing-generation limitation")
    else:
        require(NO_GENERATION_LIMITATION in limitations, "empty generation registry must retain missing-generation limitation")


def main() -> int:
    contract = load(CONTRACT)
    registered = canonical_generation_count()

    require(contract.get("schemaVersion") == "memory-os-deletion-worker-host-failure.v1", "contract schema drift")
    require(contract.get("failureClass") == "PHYSICAL_HOST_OR_VM_NODE_LOSS", "host failure class drift")
    require(contract.get("dependencyMode") == "PRODUCTION_EQUIVALENT_REQUIRED", "host proof must require production-equivalent dependencies")
    require(contract.get("environmentGenerationContract") == str(GENERATION.relative_to(ROOT)), "generation contract ref drift")
    require(contract.get("environmentGenerationRegistry") == str(REGISTRY.relative_to(ROOT)), "generation registry ref drift")

    validate_generation_projection(contract, registered)

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "currentBoundary required")
    for key in (
        "actualPhysicalHostOrVMNodeLossCovered",
        "externalFailureControllerCovered",
        "replacementDifferentNodeCovered",
        "leaseExclusionUntilExpiryCovered",
        "replacementAttempt2Covered",
        "dependencyReconnectCovered",
        "zeroOwnedRowsAfterRecoveryCovered",
        "zeroObjectVersionsAfterRecoveryCovered",
        "independentReviewCompleted",
        "deletionHostFailureRecoveryProven",
        "productionEquivalentEvidence",
        "productionEvidence",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"unexecuted host-failure boundary cannot enable {key}")
    require(boundary.get("productionDecision") == "NO_GO", "host-failure foundation cannot change production decision")

    prerequisites = contract.get("requiredPrerequisites")
    require(isinstance(prerequisites, dict), "requiredPrerequisites required")
    for key in (
        "registeredProductionEquivalentEnvironmentGeneration",
        "validatedEnvironmentManifest",
        "syntheticAccountsOnly",
        "productionTrafficForbidden",
        "productionCredentialsForbidden",
        "failureControllerOutsideTargetNode",
        "atLeastTwoDistinctWorkerNodeIdentities",
        "sharedPostgreSQLAndObjectStoreRemainReachableToReplacementNode",
        "sameEnvironmentGenerationForKilledAndReplacementWorkers",
        "appendOnlyResultEvidence",
        "independentReview",
    ):
        require(prerequisites.get(key) is True, f"host-failure prerequisite must remain true: {key}")

    required = contract.get("requiredAssertions")
    require(isinstance(required, dict), "requiredAssertions required")
    for key in (
        "targetNodeLossObservedOutsideTargetNode",
        "killedWorkerCannotExecuteCleanupOrRelease",
        "canonicalDeletionLedgerSurvivesNodeLoss",
        "noCompetingClaimBeforeLeaseExpiry",
        "replacementWorkerRunsOnDifferentNode",
        "replacementReceiptAttemptEquals2",
        "objectErasureIsIdempotentAcrossNodeLoss",
        "databaseSweepAndTombstoneConverge",
        "deletionBacklogConvergesToZero",
        "ownedRowsConvergeToZero",
        "objectVersionsConvergeToZero",
        "noResurrection",
    ):
        require(required.get(key) is True, f"host-failure assertion must remain true: {key}")

    forbidden = contract.get("forbiddenEvidenceSubstitutions")
    require(isinstance(forbidden, list) and forbidden, "forbiddenEvidenceSubstitutions required")
    lowered = "\n".join(str(item).lower() for item in forbidden)
    for phrase in ("process sigkill", "docker container kill", "same node", "local postgres", "local minio"):
        require(phrase in lowered, f"host-failure substitution guard missing: {phrase}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness required")
    require(readiness.get("contractDefined") is True, "contractDefined must be true")
    require(readiness.get("validatorImplemented") is True, "validatorImplemented must be true")
    require(isinstance(readiness.get("automaticWorkflowImplemented"), bool), "automaticWorkflowImplemented must be boolean")
    for key in (
        "hostFailureDrillExecuted",
        "hostFailureResultCommitted",
        "independentReviewCompleted",
        "deletionHostFailureRecoveryProven",
        "productionEquivalentEvidence",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"host-failure foundation cannot enable readiness.{key}")

    print("Memory OS deletion-worker physical host-failure admission PASS")
    print(f"registered production-equivalent generations: {registered}")
    print(f"environment generation available: {str(registered > 0).lower()}")
    print("process/container kill substitution: forbidden")
    print("physical host/node failure recovery: false")
    print("production-equivalent evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION HOST FAILURE ADMISSION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
