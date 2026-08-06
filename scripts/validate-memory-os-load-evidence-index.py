#!/usr/bin/env python3
"""Validate the partition between mock, live and deferred load scenarios."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
EXPECTED_EXTERNAL = {
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
}
EXPECTED_DEFERRED = {
    "capacity-ramp-local-postgres-minio",
    "deletion-worker-under-api-load",
    "soak-memory-leak",
    "production-equivalent",
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

    require(external_ids == set(EXPECTED_EXTERNAL),
            f"external live scenario set drift: {sorted(external_ids)}")
    require(deferred_ids == EXPECTED_DEFERRED,
            f"deferred scenario set drift: {sorted(deferred_ids)}")

    for scenario_id, (mode, contract_ref, validator_ref) in EXPECTED_EXTERNAL.items():
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

    results_committed = readiness.get("exactHeadLiveResultsCommitted")
    require(isinstance(results_committed, bool),
            "readiness.exactHeadLiveResultsCommitted must be boolean")
    result_presence = {ref: (ROOT / ref).is_file() for ref in LIVE_RESULT_REFS}
    if results_committed:
        require(all(result_presence.values()),
                f"live results marked committed but files are missing: {result_presence}")
    elif any(result_presence.values()):
        # Both files are generated atomically by one workflow. A partial pair is
        # always invalid. A complete pair with the flag still false is allowed
        # only transiently inside the workflow before reconciliation.
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
    print(f"live external: {len(external)}")
    print(f"deferred: {len(deferred)}")
    print(f"live results committed flag: {results_committed}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"LOAD EVIDENCE INDEX FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
