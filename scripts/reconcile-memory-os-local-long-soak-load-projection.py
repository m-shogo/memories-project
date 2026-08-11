#!/usr/bin/env python3
"""Derive the LOCAL_LONG_SOAK load projection from canonical local-only soak authority."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOAK_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
LOAD_PATH = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"

SCENARIO_ID = "LOCAL_LONG_SOAK"
EVIDENCE_REFS = [
    "docs/fixtures/memory-os-operability/memory-os-rehearsal-sustained-soak-60s.attempts.json",
    "docs/fixtures/memory-os-operability/memory-os-rehearsal-sustained-soak-3600s.attempts.json",
]
REPORT_OUTPUT = "docs/fixtures/memory-os-operability/memory-os-rehearsal-sustained-soak-3600s.attempts.json"
RUNNER = "scripts/run-memory-os-sustained-local-soak.py"
SEMANTIC_SUMMARY = "contracts/operations/load-test-semantic-summary.v1.json"
PARAMETER_PROVENANCE = "contracts/operations/load-test-result-contract.v1.json"
DESCRIPTIVE_STATUS = "DESCRIPTIVE_LOCAL_SOAK_COMPLETE"
REMAINING_SCOPE = (
    "Local 60-second and 3600-second bounded runs are registered as descriptive non-production evidence only; "
    "production-equivalent sustained soak, leak proof, capacity approval and threshold approval remain absent."
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def assert_local_only_boundary(row: dict[str, Any]) -> None:
    for key in (
        "productionEvidence",
        "productionSustainedSoakEvidence",
        "leakProof",
        "capacityApproved",
        "thresholdsApproved",
    ):
        require(row.get(key) is False, f"{SCENARIO_ID} existing row must keep {key}=false")
    metadata = row.get("runMetadata")
    require(isinstance(metadata, dict), f"{SCENARIO_ID} existing row runMetadata missing")
    for key in ("productionEquivalent", "productionTraffic", "productionCredentials", "productionEvidence"):
        require(metadata.get(key) is False, f"{SCENARIO_ID} existing row must keep runMetadata.{key}=false")
    require(metadata.get("approvalAuthority") == "NONE", f"{SCENARIO_ID} existing row must not claim approval authority")


def derived_row() -> dict[str, Any]:
    return {
        "scenarioId": SCENARIO_ID,
        "environment": "local-sustained-soak",
        "attemptLayout": "30s, 60s and 3600s bounded local long-soak receipts",
        "evidenceRefs": EVIDENCE_REFS,
        "reportOutput": REPORT_OUTPUT,
        "executedRunner": RUNNER,
        "semanticSummaryRef": SEMANTIC_SUMMARY,
        "semanticStatus": DESCRIPTIVE_STATUS,
        "parameterProvenanceRef": PARAMETER_PROVENANCE,
        "parameterProvenanceStatus": DESCRIPTIVE_STATUS,
        "outcome": DESCRIPTIVE_STATUS,
        "productionEvidence": False,
        "productionSustainedSoakEvidence": False,
        "leakProof": False,
        "capacityApproved": False,
        "thresholdsApproved": False,
        "remainingScope": REMAINING_SCOPE,
        "runMetadata": {
            "executionClass": SCENARIO_ID,
            "environmentClass": "local",
            "productionEquivalent": False,
            "productionTraffic": False,
            "productionCredentials": False,
            "productionEvidence": False,
            "approvalAuthority": "NONE",
        },
    }


def main() -> int:
    soak = load(SOAK_PATH)
    load_contract = load(LOAD_PATH)

    load_readiness = load_contract.get("readiness")
    require(isinstance(load_readiness, dict), "load contract readiness missing")
    require(load_readiness.get("sustainedSoakEvidence") is False, "load contract sustainedSoakEvidence must remain false")
    require(load_readiness.get("productionEquivalentDependencies") is False, "load contract productionEquivalentDependencies must remain false")

    readiness = soak.get("readiness")
    require(isinstance(readiness, dict), "sustained local soak readiness missing")
    eligible = all(
        readiness.get(key) is True
        for key in (
            "firstLongRunCommitted",
            "secondIndependentLongRunCommitted",
            "trendReviewCompleted",
            "localSustainedSoakEvidence",
        )
    )
    for key in (
        "productionSustainedSoakEvidence",
        "leakProofAvailable",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"sustained local soak authority must keep readiness.{key}=false")

    rows = load_contract.get("externalExecutedScenarios")
    require(isinstance(rows, list), "externalExecutedScenarios must be a list")
    matches = [row for row in rows if isinstance(row, dict) and row.get("scenarioId") == SCENARIO_ID]
    require(len(matches) <= 1, f"duplicate {SCENARIO_ID} projection rows are forbidden")
    if matches:
        assert_local_only_boundary(matches[0])

    rebuilt: list[Any] = []
    replaced = False
    for row in rows:
        if isinstance(row, dict) and row.get("scenarioId") == SCENARIO_ID:
            if eligible:
                rebuilt.append(derived_row())
                replaced = True
            continue
        rebuilt.append(row)
    if eligible and not replaced:
        rebuilt.append(derived_row())

    load_contract["externalExecutedScenarios"] = rebuilt
    LOAD_PATH.write_text(json.dumps(load_contract, indent=2) + "\n", encoding="utf-8")
    print(f"{SCENARIO_ID} load projection reconciled: {'registered' if eligible else 'withheld'}")
    print("production evidence: false")
    print("production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL LONG SOAK LOAD PROJECTION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
