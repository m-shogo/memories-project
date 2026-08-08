#!/usr/bin/env python3
"""Reconcile the read-only restore-preflight environment-generation eligibility authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-eligibility.py"


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


def load_helper():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_eligibility_reconcile", HELPER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract = load(CONTRACT)
    generation_contract = load(GEN_CONTRACT)
    helper = load_helper()
    state = helper.derive(GEN_REGISTRY)

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "eligibility authority state missing")
    mapping = {
        "registeredGenerationCount": state["registeredGenerationCount"],
        "unsupersededGenerationCount": state["unsupersededGenerationCount"],
        "preflightEligibleGenerationCount": state["preflightEligibleGenerationCount"],
        "unsupersededPreflightEligibleGenerationCount": state["unsupersededPreflightEligibleGenerationCount"],
        "distinctPreflightEligibleEnvironmentCount": state["distinctPreflightEligibleEnvironmentCount"],
        "eligibleDirectedRestorePairCount": state["eligibleDirectedPairCount"],
    }
    for field, value in mapping.items():
        boundary[field] = value
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    readiness["contractDefined"] = True
    readiness["helperImplemented"] = HELPER.is_file()
    readiness["validatorImplemented"] = VALIDATOR.is_file()
    readiness["reconcileImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["eligibleGenerationAvailable"] = mapping["preflightEligibleGenerationCount"] > 0
    readiness["twoDistinctEligibleEnvironmentsAvailable"] = mapping["distinctPreflightEligibleEnvironmentCount"] >= 2
    readiness["eligibleDirectedRestorePairAvailable"] = mapping["eligibleDirectedRestorePairCount"] > 0
    readiness["productionReady"] = False
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    gen_boundary = generation_contract.get("currentBoundary")
    require(isinstance(gen_boundary, dict), "generation boundary missing")
    require(gen_boundary.get("registeredGenerationCount") == mapping["registeredGenerationCount"], "generation registered count drift")
    require(gen_boundary.get("preflightEligibleGenerationCount") == mapping["preflightEligibleGenerationCount"], "generation eligible count drift")

    completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"post-reconcile eligibility validator failed:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}")

    print("Memory OS production-equivalent environment eligibility reconciliation PASS")
    print(f"registered generations: {mapping['registeredGenerationCount']}")
    print(f"preflight-eligible generations: {mapping['preflightEligibleGenerationCount']}")
    print(f"distinct eligible environments: {mapping['distinctPreflightEligibleEnvironmentCount']}")
    print(f"eligible directed restore pairs: {mapping['eligibleDirectedRestorePairCount']}")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT ENVIRONMENT ELIGIBILITY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
