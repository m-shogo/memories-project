#!/usr/bin/env python3
"""Validate the partition between mock, local-live and deferred load scenarios."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MAX_JSON_BYTES = 1024 * 1024
INDEX_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CONTROLLED_CONTRACT_PATH = ROOT / "contracts/operations/controlled-saturation-ramp-contract.v1.json"
SOAK_CONTRACT_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
PREFENCE_CONTRACT_PATH = ROOT / "contracts/operations/deletion-prefence-linearization-contract.v1.json"
WORKER_SATURATION_CONTRACT_PATH = ROOT / "contracts/operations/deletion-worker-saturation-contract.v1.json"
CONTROLLED_SCENARIO_ID = "signed-upload-controlled-saturation-ramp-local-dependencies"
SOAK_SCENARIO_ID = "mixed-import-lifecycle-local-long-soak"
PREFENCE_SCENARIO_ID = "account-deletion-prefence-inflight-linearization-local-dependencies"
WORKER_SATURATION_SCENARIO_ID = "multi-account-deletion-worker-saturation-local-dependencies"
BASE_EXPECTED_EXTERNAL = {
    "authenticated-preview-local-postgres": (
        "LOCAL_POSTGRES",
        "contracts/operations/live-postgres-load-scenario-contract.v1.json",
        "scripts/validate-memory-os-live-load.py",
    ),
    "concurrent-idempotent-apply-local-postgres": (
        "LOCAL_POSTGRES",
        "contracts/operations/live-postgres-load-scenario-contract.v1.json",
        "scripts/validate-memory-os-live-load.py",
    ),
    "signed-upload-lifecycle-local-minio-postgres": (
        "LOCAL_POSTGRES_MINIO",
        "contracts/operations/live-object-load-scenario-contract.v1.json",
        "scripts/validate-memory-os-live-object-load.py",
    ),
    "authenticated-preview-capacity-ramp-local-postgres": (
        "LOCAL_POSTGRES",
        "contracts/operations/capacity-ramp-contract.v1.json",
        "scripts/validate-memory-os-capacity-ramp.py",
    ),
    "authenticated-preview-short-ci-stability-local-postgres": (
        "LOCAL_POSTGRES",
        "contracts/operations/short-stability-sample-contract.v1.json",
        "scripts/validate-memory-os-short-stability-sample.py",
    ),
    "account-deletion-post-fence-load-local-dependencies": (
        "LOCAL_POSTGRES_MINIO",
        "contracts/operations/deletion-under-load-contract.v1.json",
        "scripts/validate-memory-os-deletion-under-load.py",
    ),
}
CONTROLLED_EXPECTED_EXTERNAL = (
    "LOCAL_POSTGRES_MINIO",
    "contracts/operations/controlled-saturation-ramp-contract.v1.json",
    "scripts/validate-memory-os-controlled-saturation-ramp.py",
)
SOAK_EXPECTED_EXTERNAL = (
    "LOCAL_POSTGRES_MINIO",
    "contracts/operations/sustained-local-soak-contract.v1.json",
    "scripts/validate-memory-os-sustained-local-soak-aggregate.py",
)
PREFENCE_EXPECTED_EXTERNAL = (
    "LOCAL_POSTGRES_MINIO",
    "contracts/operations/deletion-prefence-linearization-contract.v1.json",
    "scripts/validate-memory-os-deletion-prefence-linearization.py",
)
WORKER_SATURATION_EXPECTED_EXTERNAL = (
    "LOCAL_POSTGRES_MINIO",
    "contracts/operations/deletion-worker-saturation-contract.v1.json",
    "scripts/validate-memory-os-deletion-worker-saturation.py",
)
BASE_EXPECTED_DEFERRED = {
    "capacity-ramp-local-postgres-minio",
    "deletion-worker-under-api-load",
    "soak-memory-leak",
    "production-equivalent",
    "soak",
    "deletion-under-load",
}
LIVE_RESULT_REFS = {
    "docs/fixtures/memory-os-operability/live-postgres-load-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/live-object-load-results.sample.v1.json",
}


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def reject_nonfinite_constant(value: str) -> None:
    raise ValidationFailure("non-finite load index JSON constant rejected")


def parse_finite_float(value: str) -> float:
    parsed = float(value)
    require(math.isfinite(parsed), "non-finite load index JSON number rejected")
    return parsed


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    document: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in document, "duplicate load index JSON key rejected")
        document[key] = value
    return document


def load(path: Path) -> dict[str, Any]:
    require(isinstance(path, Path), "load index JSON path must be Path")
    for candidate in (path, *path.parents):
        require(not candidate.is_symlink(), "load index JSON symlink path rejected")
    require(path.is_file(), "load index JSON file missing or unsafe")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError):
        raise ValidationFailure("load index JSON path escaped repository") from None
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_JSON_BYTES + 1)
        require(len(raw) <= MAX_JSON_BYTES, "load index JSON exceeds reviewed read limit")
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_nonfinite_constant,
            parse_float=parse_finite_float,
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, OverflowError):
        raise ValidationFailure("load index JSON unreadable or invalid") from None
    require(isinstance(value, dict), "load index JSON root must be object")
    return value


def safe_repo_ref(value: Any) -> bool:
    """Admit only regular, unsymlinked repository-relative evidence files."""
    if not isinstance(value, str) or not value:
        return False
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        return False
    path = ROOT / relative
    if any(candidate.is_symlink() for candidate in (path, *path.parents)):
        return False
    if not path.is_file():
        return False
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError):
        return False
    return True


def validate_evidence_refs(refs: Any) -> None:
    require(isinstance(refs, list) and all(isinstance(ref, str) for ref in refs),
            "evidenceRefs must be a list of strings")
    require(len(refs) == len(set(refs)), "evidenceRefs must be unique")
    for ref in refs:
        require(safe_repo_ref(ref), "contract evidence path missing or unsafe")


def unique_scenario_map(items: Any, field: str) -> dict[str, dict[str, Any]]:
    require(isinstance(items, list), f"{field} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        require(isinstance(item, dict), f"{field} entries must be objects")
        scenario_id = item.get("scenarioId")
        require(isinstance(scenario_id, str) and scenario_id, f"{field} scenarioId is required")
        require(scenario_id not in result, f"duplicate {field} scenarioId: {scenario_id}")
        result[scenario_id] = item
    return result


def readiness_bool(contract: dict[str, Any], field: str, label: str) -> bool:
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), f"{label} readiness must be object")
    value = readiness.get(field)
    require(isinstance(value, bool), f"{label}.{field} must be boolean")
    return value


def main() -> int:
    contract = load(INDEX_PATH)

    controlled_contract = load(CONTROLLED_CONTRACT_PATH)
    controlled_committed = readiness_bool(
        controlled_contract, "exactSourceResultCommitted", "controlled saturation readiness"
    )

    soak_contract = load(SOAK_CONTRACT_PATH)
    soak_readiness = soak_contract.get("readiness")
    require(isinstance(soak_readiness, dict), "LOCAL_LONG_SOAK readiness must be object")
    first_soak_run = soak_readiness.get("firstLongRunCommitted")
    local_soak_evidence = soak_readiness.get("localSustainedSoakEvidence")
    require(isinstance(first_soak_run, bool), "firstLongRunCommitted must be boolean")
    require(isinstance(local_soak_evidence, bool), "localSustainedSoakEvidence must be boolean")
    if local_soak_evidence:
        require(
            first_soak_run is True and soak_readiness.get("secondIndependentLongRunCommitted") is True,
            "local sustained-soak evidence requires repeated long runs",
        )
        require(
            soak_readiness.get("trendReviewCompleted") is True,
            "local sustained-soak evidence requires trend review",
        )

    prefence_contract = load(PREFENCE_CONTRACT_PATH)
    prefence_committed = readiness_bool(
        prefence_contract, "exactSourceResultCommitted", "pre-fence linearization readiness"
    )
    prefence_proven = readiness_bool(
        prefence_contract, "preFenceInFlightLinearizationProven", "pre-fence linearization readiness"
    )
    require(prefence_proven is prefence_committed, "pre-fence proof/result readiness drift")

    worker_contract = load(WORKER_SATURATION_CONTRACT_PATH)
    worker_committed = readiness_bool(
        worker_contract, "exactSourceResultCommitted", "worker saturation readiness"
    )
    worker_proven = readiness_bool(
        worker_contract, "multiAccountWorkerSaturationProven", "worker saturation readiness"
    )
    require(worker_proven is worker_committed, "worker saturation proof/result readiness drift")

    expected_external = dict(BASE_EXPECTED_EXTERNAL)
    if controlled_committed:
        expected_external[CONTROLLED_SCENARIO_ID] = CONTROLLED_EXPECTED_EXTERNAL
    if first_soak_run:
        expected_external[SOAK_SCENARIO_ID] = SOAK_EXPECTED_EXTERNAL
    if prefence_committed:
        expected_external[PREFENCE_SCENARIO_ID] = PREFENCE_EXPECTED_EXTERNAL
    if worker_committed:
        expected_external[WORKER_SATURATION_SCENARIO_ID] = WORKER_SATURATION_EXPECTED_EXTERNAL

    expected_deferred = set(BASE_EXPECTED_DEFERRED)
    if worker_committed:
        expected_deferred.remove("deletion-worker-under-api-load")

    modes = contract.get("dependencyModes")
    require(
        isinstance(modes, list) and len(modes) == len(set(modes)),
        "dependencyModes must be a unique list",
    )
    mode_set = set(modes)
    require("LOCAL_POSTGRES_MINIO" in mode_set, "dependencyModes must include LOCAL_POSTGRES_MINIO")
    require("PRODUCTION_EQUIVALENT" in mode_set, "dependencyModes must include PRODUCTION_EQUIVALENT")

    executed = unique_scenario_map(contract.get("executedScenarios"), "executedScenarios")
    external = unique_scenario_map(contract.get("externalExecutedScenarios"), "externalExecutedScenarios")
    deferred = unique_scenario_map(contract.get("deferredScenarios"), "deferredScenarios")

    executed_ids = set(executed)
    external_ids = set(external)
    deferred_ids = set(deferred)
    require(executed_ids.isdisjoint(external_ids), f"mock and live scenario overlap: {sorted(executed_ids & external_ids)}")
    require(executed_ids.isdisjoint(deferred_ids), f"executed scenario marked deferred: {sorted(executed_ids & deferred_ids)}")
    require(external_ids.isdisjoint(deferred_ids), f"live scenario marked deferred: {sorted(external_ids & deferred_ids)}")

    require(external_ids == set(expected_external), f"external live scenario set drift: {sorted(external_ids)}")
    require(deferred_ids == expected_deferred, f"deferred scenario set drift: {sorted(deferred_ids)}")

    for scenario_id, (mode, contract_ref, validator_ref) in expected_external.items():
        item = external[scenario_id]
        require(item.get("dependencyMode") == mode, f"{scenario_id}: dependencyMode drift")
        require(item.get("productionEvidence") is False, f"{scenario_id}: local scenario cannot claim production evidence")
        require(item.get("contractRef") == contract_ref, f"{scenario_id}: contractRef drift")
        require(item.get("validatorRef") == validator_ref, f"{scenario_id}: validatorRef drift")
        require(safe_repo_ref(contract_ref), f"{scenario_id}: contractRef missing or unsafe")
        require(safe_repo_ref(validator_ref), f"{scenario_id}: validatorRef missing or unsafe")

    capacity = external["authenticated-preview-capacity-ramp-local-postgres"]
    require(capacity.get("capacityBoundaryEstablished") is False, "bounded local capacity ramp cannot establish the capacity boundary")

    stability = external["authenticated-preview-short-ci-stability-local-postgres"]
    require(stability.get("classification") == "SHORT_CI_STABILITY_SAMPLE", "short stability sample classification drift")
    require(stability.get("sustainedSoakEvidence") is False, "short CI stability sample cannot claim sustained-soak evidence")
    require(stability.get("leakProof") is False, "short CI stability sample cannot claim leak proof")

    deletion = external["account-deletion-post-fence-load-local-dependencies"]
    require(
        deletion.get("requestsStartedBeforeFenceCovered") is False,
        "post-fence deletion checkpoint cannot claim pre-fence request coverage",
    )

    if controlled_committed:
        controlled = external[CONTROLLED_SCENARIO_ID]
        require(controlled.get("classification") == "BOUNDED_LOCAL_CAPACITY_RAMP", "controlled saturation classification drift")
        for key in ("capacityBoundaryEstablished", "operationalThresholdApproved", "repeatabilityEstablished"):
            require(controlled.get(key) is False, f"one controlled local ramp cannot enable {key}")
    else:
        require(CONTROLLED_SCENARIO_ID not in external, "controlled saturation scenario cannot enter the load index before exact-source reconciliation")

    if first_soak_run:
        soak = external[SOAK_SCENARIO_ID]
        require(soak.get("classification") == "LOCAL_LONG_SOAK", "LOCAL_LONG_SOAK classification drift")
        require(soak.get("localSustainedSoakEvidence") is local_soak_evidence, "LOCAL_LONG_SOAK local evidence flag drift")
        for key in (
            "productionSustainedSoakEvidence",
            "leakProof",
            "capacityBoundaryEstablished",
            "operationalThresholdApproved",
        ):
            require(soak.get(key) is False, f"LOCAL_LONG_SOAK cannot enable {key}")
    else:
        require(SOAK_SCENARIO_ID not in external, "LOCAL_LONG_SOAK cannot enter executed evidence before one exact-source 60-minute run")

    if prefence_committed:
        prefence = external[PREFENCE_SCENARIO_ID]
        require(prefence.get("classification") == "LOCAL_PREFENCE_LINEARIZATION", "pre-fence classification drift")
        require(prefence.get("surfaceCoverage") == "PREVIEW_READ_ONLY", "pre-fence surface coverage must remain Preview-only")
        require(prefence.get("preFenceInFlightLinearizationProven") is True, "reconciled pre-fence proof flag required")
        require(prefence.get("requestsStartedBeforeFenceCovered") is True, "scenario-specific pre-fence coverage required")
        require(prefence.get("productionEquivalentDependencies") is False, "local pre-fence proof cannot become production-equivalent")
    else:
        require(PREFENCE_SCENARIO_ID not in external, "pre-fence scenario cannot enter the load index before exact-source reconciliation")

    if worker_committed:
        worker = external[WORKER_SATURATION_SCENARIO_ID]
        require(worker.get("classification") == "BOUNDED_LOCAL_WORKER_SATURATION", "worker saturation classification drift")
        require(worker.get("multiAccountWorkerSaturationProven") is True, "reconciled worker saturation flag required")
        for key in ("capacityBoundaryEstablished", "operationalThresholdApproved", "productionEquivalentDependencies"):
            require(worker.get(key) is False, f"local worker saturation cannot enable {key}")
    else:
        require(WORKER_SATURATION_SCENARIO_ID not in external, "worker saturation scenario cannot enter load index before exact-source reconciliation")

    for scenario_id, item in deferred.items():
        reason = item.get("reason")
        mode = item.get("requiredDependencyMode")
        require(isinstance(reason, str) and reason.strip(), f"{scenario_id}: deferred reason is required")
        require(mode in mode_set, f"{scenario_id}: unknown requiredDependencyMode {mode!r}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    require(readiness.get("localLivePostgresCheckpointImplemented") is True, "localLivePostgresCheckpointImplemented must remain true")
    require(readiness.get("localLiveObjectStoreCheckpointImplemented") is True, "localLiveObjectStoreCheckpointImplemented must remain true")
    for local_only_false in (
        "productionShapedWorkload",
        "capacityBoundaryEstablished",
        "sustainedSoakEvidence",
        "operationalThresholds",
        "productionEquivalentDependencies",
    ):
        require(readiness.get(local_only_false) is False, f"local evidence cannot enable readiness.{local_only_false}")
    if controlled_committed:
        require(readiness.get("controlledLocalDependencySaturationRampExecuted") is True, "reconciled controlled saturation result must be reflected in load readiness")
    if soak_readiness.get("runnerImplemented") is True:
        require(readiness.get("localLongSoakFoundationImplemented") is True, "implemented LOCAL_LONG_SOAK runner must be reflected in load readiness")
    if first_soak_run:
        require(readiness.get("localLongSoakRunCount", 0) >= 1, "committed LOCAL_LONG_SOAK result must be reflected in load readiness")
        require(readiness.get("localSustainedSoakEvidence") is local_soak_evidence, "load readiness local soak evidence drift")
    if prefence_committed:
        require(readiness.get("previewPreFenceInFlightLinearizationProven") is True, "pre-fence proof must be reflected in load readiness")
    if worker_committed:
        require(readiness.get("multiAccountDeletionWorkerSaturationProven") is True, "worker saturation proof must be reflected in load readiness")
    if readiness.get("productionEquivalentAdmissionContractDefined") is not None:
        require(readiness.get("productionEquivalentAdmissionContractDefined") is True, "production-equivalent admission foundation flag drift")
        require(readiness.get("productionEquivalentEnvironmentProvisioned") is False, "admission foundation cannot provision environment")

    results_committed = readiness.get("exactHeadLiveResultsCommitted")
    require(isinstance(results_committed, bool), "readiness.exactHeadLiveResultsCommitted must be boolean")
    result_presence = {ref: safe_repo_ref(ref) for ref in LIVE_RESULT_REFS}
    if results_committed:
        require(all(result_presence.values()), f"live results marked committed but files are missing: {result_presence}")
    elif any(result_presence.values()):
        require(all(result_presence.values()), f"partial live result pair exists: {result_presence}")

    validate_evidence_refs(contract.get("evidenceRefs"))

    print("Memory OS load evidence index PASS")
    print(f"mock executed: {len(executed)}")
    print(f"local/live external: {len(external)}")
    print(f"deferred: {len(deferred)}")
    print(f"live results committed flag: {results_committed}")
    print(f"controlled saturation committed flag: {controlled_committed}")
    print(f"LOCAL_LONG_SOAK first run committed: {first_soak_run}")
    print(f"LOCAL_LONG_SOAK local sustained evidence: {local_soak_evidence}")
    print(f"Preview pre-fence proof committed: {prefence_committed}")
    print(f"multi-account worker saturation committed: {worker_committed}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"LOAD EVIDENCE INDEX FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
