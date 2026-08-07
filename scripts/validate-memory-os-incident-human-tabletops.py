#!/usr/bin/env python3
"""Validate the append-only human incident-tabletop evidence ledger."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/incident-human-tabletop-evidence-contract.v1.json"
LEDGER = ROOT / "docs/evidence/incident-tabletops"
WRITER = ROOT / "scripts/register-memory-os-incident-human-tabletop.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    contract = load(CONTRACT)
    require(contract.get("schemaVersion") == "memory-os-incident-human-tabletop-evidence.v1", "contract schema drift")
    require(contract.get("ledgerDirectory") == str(LEDGER.relative_to(ROOT)), "ledger directory drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer binding drift")
    required = set(contract.get("requiredScenarioIds", []))
    require(len(required) == 6, "required scenario count drift")
    LEDGER.mkdir(parents=True, exist_ok=True)
    scenarios: set[str] = set()
    for path in sorted(LEDGER.glob("IR-DRILL-*.json")):
        completed = subprocess.run(
            ["python", str(WRITER), "--record", str(path), "--validate-only"],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        require(completed.returncode == 0, f"invalid human tabletop record {path.name}: {completed.stdout[-2000:]}")
        record = load(path)
        scenario = record.get("scenarioId")
        require(isinstance(scenario, str) and scenario in required, f"unknown scenario in ledger: {scenario}")
        require(path.name == scenario + ".json", f"ledger filename must equal scenario id: {path.name}")
        require(scenario not in scenarios, f"duplicate completed scenario: {scenario}")
        scenarios.add(scenario)
    current = contract.get("currentAuthority")
    readiness = contract.get("readiness")
    require(isinstance(current, dict) and isinstance(readiness, dict), "contract authority missing")
    require(current.get("acceptedCompletedScenarioCount") in {0, len(scenarios)}, "accepted count drift before reconcile")
    require(current.get("requiredScenarioCount") == len(required), "requiredScenarioCount drift")
    for key in ("productionRecoveryDrillCompleted", "pagingConfigured", "externalContactTreeOwned", "independentIncidentControlReviewCompleted", "productionEvidence", "productionReady"):
        require(current.get(key) is False, f"human tabletop authority cannot enable {key}")
    require(current.get("productionDecision") == "NO_GO", "production decision drift")
    require(readiness.get("productionRecoveryDrillCompleted") is False and readiness.get("productionReady") is False, "readiness production boundary drift")
    print("Memory OS human incident tabletop ledger validation PASS")
    print(f"accepted scenarios: {len(scenarios)}/{len(required)}")
    print(f"all required scenarios completed: {scenarios == required}")
    print("production recovery drill: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"HUMAN TABLETOP LEDGER VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
