#!/usr/bin/env python3
"""Validate the partition between mock, local-live and deferred load scenarios."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CONTROLLED_CONTRACT_PATH = ROOT / "contracts/operations/controlled-saturation-ramp-contract.v1.json"
CONTROLLED_SCENARIO_ID = "signed-upload-controlled-saturation-ramp-local-dependencies"
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
EXPECTED_DEFERRED = {
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


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


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


def main() -> int:
    contract = load(INDEX_PATH)
    controlled_contract = load(CONTROLLED_CONTRACT_PATH)
    controlled_readiness = controlled_contract.get("readiness")
    require(isinstance(controlled_readiness, dict), "controlled saturation readiness must be object")
    controlled_committed = controlled_readiness.get("exactSourceResultCommitted")
    require(isinstance(controlled_committed, bool), "controlled saturation exactSourceResultCommitted must be boolean")

    expected_external = dict(BASE_EXPECTED_EXTERNAL)
    if controlled_committed:
        expected_external[CONTROLLED_SCENARIO_ID] = CONTROLLED_EXPECTED_EXTERNAL

    modes = contract.get("dependencyModes")
    require(isinstance(modes, list) and len(modes) == len(set(modes)),
            "dependencyModes must be a unique list")
    mode_set = set(modes)
    require("LOCAL_POSTGRES_MINIO" in mode_set,
            "dependencyModes must include LOCAL_POSTGRES_MINIO")

    executed = unique_scenario_map(contract.get("executedScenarios"), "executedScenarios")
    external = unique_scenario_map(
        contract.get("externalExecutedScenarios"),
        "externalExecutedScenarios",
    )
    deferred = unique_scenario_map(contract.get("deferredScenarios"), "deferredScenarios")

    executed_ids = set(executed)
    external_ids = set(external)
    deferred_ids = set(deferred)
    require(executed_ids.isdisjoint(external_ids),
            f"mock and live scenario overlap: {sorted(executed_ids & external_ids)}")
    require(executed_ids.isdisjoint(deferred_ids),
            f"executed scenario marked deferred: {sorted(executed_ids & deferred_ids)}")
    require(external_ids.isdisjoint(deferred_ids),
            f"live scenario marked deferred: {sorted(external_ids & deferred_ids)}")

    require(external_ids == set(expected_external),
            f"external live scenario set drift: {sorted(external_ids)}")
    require(deferred_ids == EXPECTED_DEFERRED,
            f"deferred scenario set drift: {sorted(deferred_ids)}")

    for scenario_id, (mode, contract_ref, validator_ref) in expected_external.items():
        item = external[scenario_id]
        require(item.get("dependencyMode") == mode,
                f"{scenario_id}: dependencyMode drift")
        require(item.get("productionEvidence") is False,
                f"{scenario_id}: local live scenario cannot claim production evidence")
        require(item.get("contractRef") == contract_ref,
                f"{scenario_id}: contractRef drift")
        require(item.get("validatorRef") == validator_ref,
                f"{scenario_id}: validatorRef drift")
        require((ROOT / contract_ref).is_file(), f"{scenario_id}: contractRef missing")
        require((ROOT / validator_ref).is_file(), f"{scenario_id}: validatorRef missing")

    capacity = external["authenticated-preview-capacity-ramp-local-postgres"]
    require(capacity.get("capacityBoundaryEstablished") is False,
            "bounded local capacity ramp cannot establish the capacity boundary")

    stability = external["authenticated-preview-short-ci-stability-local-postgres"]
    require(stability.get("classification") == "SHORT_CI_STABILITY_SAMPLE",
            "short stability sample classification drift")
    require(stability.get("sustainedSoakEvidence") is False,
            "short CI stability sample cannot claim sustained-soak evidence")
    require(stability.get("leakProof") is False,
            "short CI stability sample cannot claim leak proof")

    deletion = external["account-deletion-post-fence-load-local-dependencies"]
    require(deletion.get("requestsStartedBeforeFenceCovered") is False,
            "post-fence deletion checkpoint cannot claim pre-fence request coverage")

    if controlled_committed:
        controlled = external[CONTROLLED_SCENARIO_ID]
        require(controlled.get("classification") == "BOUNDED_LOCAL_CAPACITY_RAMP",
                "controlled saturation classification drift")
        for key in (
            "capacityBoundaryEstablished",
            "operationalThresholdApproved",
            "repeatabilityEstablished",
        ):
            require(controlled.get(key) is False,
                    f"one controlled local ramp cannot enable {key}")
    else:
        require(CONTROLLED_SCENARIO_ID not in external,
                "controlled saturation scenario cannot enter the load index before exact-source reconciliation")

    for scenario_id, item in deferred.items():
        reason = item.get("reason")
        mode = item.get("requiredDependencyMode")
        require(isinstance(reason, str) and reason.strip(),
                f"{scenario_id}: deferred reason is required")
        require(mode in mode_set, f"{scenario_id}: unknown requiredDependencyMode {mode!r}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    require(readiness.get("localLivePostgresCheckpointImplemented") is True,
            "localLivePostgresCheckpointImplemented must remain true")
    require(readiness.get("localLiveObjectStoreCheckpointImplemented") is True,
            "localLiveObjectStoreCheckpointImplemented must remain true")
    for local_only_false in (
        "productionShapedWorkload",
        "capacityBoundaryEstablished",
        "sustainedSoakEvidence",
        "operationalThresholds",
        "productionEquivalentDependencies",
    ):
        require(readiness.get(local_only_false) is False,
                f"local evidence cannot enable readiness.{local_only_false}")
    if controlled_committed:
        require(readiness.get("controlledLocalDependencySaturationRampExecuted") is True,
                "reconciled controlled saturation result must be reflected in load readiness")

    results_committed = readiness.get("exactHeadLiveResultsCommitted")
    require(isinstance(results_committed, bool),
            "readiness.exactHeadLiveResultsCommitted must be boolean")
    result_presence = {ref: (ROOT / ref).is_file() for ref in LIVE_RESULT_REFS}
    if results_committed:
        require(all(result_presence.values()),
                f"live results marked committed but files are missing: {result_presence}")
    elif any(result_presence.values()):
        require(all(result_presence.values()),
                f"partial live result pair exists: {result_presence}")

    evidence_refs = contract.get("evidenceRefs")
    require(isinstance(evidence_refs, list) and len(evidence_refs) == len(set(evidence_refs)),
            "evidenceRefs must be a unique list")
    for ref in evidence_refs:
        require(isinstance(ref, str) and (ROOT / ref).is_file(),
                f"contract evidence path missing: {ref}")

    print("Memory OS load evidence index PASS")
    print(f"mock executed: {len(executed)}")
    print(f"local/live external: {len(external)}")
    print(f"deferred: {len(deferred)}")
    print(f"live results committed flag: {results_committed}")
    print(f"controlled saturation committed flag: {controlled_committed}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"LOAD EVIDENCE INDEX FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
