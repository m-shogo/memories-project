#!/usr/bin/env python3
"""Reconcile local long-soak load authority without inventing a duplicate scenario ID."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SOAK_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
CANONICAL_LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
CANONICAL_SOAK_VALIDATOR = ROOT / "scripts/validate-memory-os-sustained-local-soak.py"
CANONICAL_LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
SOAK_PATH = CANONICAL_SOAK_PATH
LOAD_PATH = CANONICAL_LOAD_PATH
SOAK_VALIDATOR = CANONICAL_SOAK_VALIDATOR
LOAD_VALIDATOR = CANONICAL_LOAD_VALIDATOR

SCENARIO_ID = "mixed-import-lifecycle-local-long-soak"
LEGACY_ALIAS_ID = "LOCAL_LONG_SOAK"
CONTRACT_REF = "contracts/operations/sustained-local-soak-contract.v1.json"
VALIDATOR_REF = "scripts/validate-memory-os-sustained-local-soak-aggregate.py"
DEPENDENCY_MODE = "LOCAL_POSTGRES_MINIO"
CLASSIFICATION = "LOCAL_LONG_SOAK"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")


def validate_authorities() -> None:
    require_exact_authority(SOAK_PATH, CANONICAL_SOAK_PATH, "sustained-soak contract")
    require_exact_authority(LOAD_PATH, CANONICAL_LOAD_PATH, "load contract")
    require_exact_authority(SOAK_VALIDATOR, CANONICAL_SOAK_VALIDATOR, "sustained-soak validator")
    require_exact_authority(LOAD_VALIDATOR, CANONICAL_LOAD_VALIDATOR, "load validator")


def run_validator(path: Path, label: str) -> None:
    validate_authorities()
    try:
        subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)
    except subprocess.CalledProcessError as exc:
        raise Fail(f"canonical {label} rejected authority: {exc}") from exc


def validate_source_authority() -> None:
    run_validator(SOAK_VALIDATOR, "sustained-soak validator")


def validate_projected_load_authority() -> None:
    run_validator(LOAD_VALIDATOR, "load validator")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def assert_local_only_boundary(row: dict[str, Any]) -> None:
    require(row.get("scenarioId") == SCENARIO_ID, "local long-soak projection must use the canonical scenarioId")
    require(row.get("contractRef") == CONTRACT_REF, f"{SCENARIO_ID} contractRef drift")
    require(row.get("validatorRef") == VALIDATOR_REF, f"{SCENARIO_ID} validatorRef drift")
    require(row.get("dependencyMode") == DEPENDENCY_MODE, f"{SCENARIO_ID} dependencyMode drift")
    require(row.get("classification") == CLASSIFICATION, f"{SCENARIO_ID} classification drift")
    require(row.get("productionEvidence") is False, f"{SCENARIO_ID} productionEvidence must remain false")
    for key in (
        "productionSustainedSoakEvidence",
        "leakProof",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
    ):
        require(row.get(key) is False, f"{SCENARIO_ID} must keep {key}=false")
    require(isinstance(row.get("localSustainedSoakEvidence"), bool), f"{SCENARIO_ID} local evidence flag must be boolean")


def derived_row(*, local_evidence: bool) -> dict[str, Any]:
    return {
        "scenarioId": SCENARIO_ID,
        "contractRef": CONTRACT_REF,
        "validatorRef": VALIDATOR_REF,
        "dependencyMode": DEPENDENCY_MODE,
        "classification": CLASSIFICATION,
        "productionEvidence": False,
        "localSustainedSoakEvidence": local_evidence,
        "productionSustainedSoakEvidence": False,
        "leakProof": False,
        "capacityBoundaryEstablished": False,
        "operationalThresholdApproved": False,
    }


def assert_legacy_alias_safe_to_remove(row: dict[str, Any]) -> None:
    require(row.get("scenarioId") == LEGACY_ALIAS_ID, "legacy alias identity drift")
    for key in (
        "productionEvidence",
        "productionSustainedSoakEvidence",
        "leakProof",
        "capacityApproved",
        "thresholdsApproved",
    ):
        require(row.get(key) is False, f"legacy {LEGACY_ALIAS_ID} row must keep {key}=false before removal")
    metadata = row.get("runMetadata")
    require(isinstance(metadata, dict), f"legacy {LEGACY_ALIAS_ID} row runMetadata missing")
    for key in ("productionEquivalent", "productionTraffic", "productionCredentials", "productionEvidence"):
        require(metadata.get(key) is False, f"legacy {LEGACY_ALIAS_ID} row must keep runMetadata.{key}=false before removal")
    require(metadata.get("approvalAuthority") == "NONE", f"legacy {LEGACY_ALIAS_ID} row must not claim approval authority")


def assert_projection_input_safe(rows: Any) -> list[dict[str, Any]]:
    require(isinstance(rows, list), "externalExecutedScenarios must be a list")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        require(isinstance(row, dict), f"externalExecutedScenarios[{index}] must be an object")
        scenario_id = row.get("scenarioId")
        require(isinstance(scenario_id, str) and scenario_id,
                f"externalExecutedScenarios[{index}].scenarioId is required")
        require(scenario_id not in seen, f"duplicate external scenarioId before projection: {scenario_id}")
        seen.add(scenario_id)
        require(row.get("productionEvidence") is False,
                f"external scenario cannot claim production evidence before local soak projection: {scenario_id}")
        if "productionEquivalentDependencies" in row:
            require(row.get("productionEquivalentDependencies") is False,
                    f"external scenario cannot claim production-equivalent dependencies: {scenario_id}")
        normalized.append(row)
    return normalized


def main() -> int:
    validate_authorities()
    validate_source_authority()
    soak = load(SOAK_PATH)
    load_contract = load(LOAD_PATH)

    load_readiness = load_contract.get("readiness")
    require(isinstance(load_readiness, dict), "load contract readiness missing")
    require(load_readiness.get("sustainedSoakEvidence") is False, "load contract sustainedSoakEvidence must remain false")
    require(load_readiness.get("productionEquivalentDependencies") is False, "load contract productionEquivalentDependencies must remain false")

    readiness = soak.get("readiness")
    require(isinstance(readiness, dict), "sustained local soak readiness missing")
    first_run = readiness.get("firstLongRunCommitted")
    second_run = readiness.get("secondIndependentLongRunCommitted")
    trend_review = readiness.get("trendReviewCompleted")
    local_evidence = readiness.get("localSustainedSoakEvidence")
    for key, value in (
        ("firstLongRunCommitted", first_run),
        ("secondIndependentLongRunCommitted", second_run),
        ("trendReviewCompleted", trend_review),
        ("localSustainedSoakEvidence", local_evidence),
    ):
        require(isinstance(value, bool), f"sustained local soak readiness.{key} must be boolean")
    if local_evidence:
        require(first_run and second_run and trend_review, "local sustained-soak evidence requires two long runs and trend review")
    for key in (
        "productionSustainedSoakEvidence",
        "leakProofAvailable",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"sustained local soak authority must keep readiness.{key}=false")

    rows = assert_projection_input_safe(load_contract.get("externalExecutedScenarios"))
    canonical = [row for row in rows if row.get("scenarioId") == SCENARIO_ID]
    legacy = [row for row in rows if row.get("scenarioId") == LEGACY_ALIAS_ID]
    require(len(canonical) <= 1, f"duplicate {SCENARIO_ID} rows are forbidden")
    require(len(legacy) <= 1, f"duplicate legacy {LEGACY_ALIAS_ID} rows are forbidden")
    if canonical:
        assert_local_only_boundary(canonical[0])
    if legacy:
        assert_legacy_alias_safe_to_remove(legacy[0])

    rebuilt = [
        row
        for row in rows
        if row.get("scenarioId") not in {SCENARIO_ID, LEGACY_ALIAS_ID}
    ]
    if first_run:
        rebuilt.append(derived_row(local_evidence=local_evidence))

    load_contract["externalExecutedScenarios"] = rebuilt
    original_load_bytes = LOAD_PATH.read_bytes()
    try:
        LOAD_PATH.write_text(json.dumps(load_contract, indent=2) + "\n", encoding="utf-8")
        validate_projected_load_authority()
    except BaseException:
        LOAD_PATH.write_bytes(original_load_bytes)
        raise
    print(f"{SCENARIO_ID} load projection reconciled: {'registered' if first_run else 'withheld'}")
    print(f"legacy {LEGACY_ALIAS_ID} alias present after reconcile: false")
    print(f"local sustained-soak evidence: {str(local_evidence).lower()}")
    print("production evidence: false")
    print("production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL LONG SOAK LOAD PROJECTION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
