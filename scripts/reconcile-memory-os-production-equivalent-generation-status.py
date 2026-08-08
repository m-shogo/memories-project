#!/usr/bin/env python3
"""Reconcile immutable environment-generation registry into bounded operability authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json"
ENV_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-record.py"
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py"
NEGATIVE = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation-negative.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
REFS = (
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "contracts/operations/production-equivalent-environment-record.v1.schema.json",
    "contracts/operations/production-equivalent-environment-generation-record.v1.schema.json",
    "scripts/validate-memory-os-production-equivalent-environment-record.py",
    "scripts/register-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation.py",
    "scripts/validate-memory-os-production-equivalent-environment-generation-negative.py",
    "scripts/reconcile-memory-os-production-equivalent-generation-status.py",
    ".github/workflows/production-equivalent-environment-generation.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_writer_for_reconcile", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    writer = load_writer()
    rows = registry.get("generations")
    count = registry.get("registeredGenerationCount")
    require(isinstance(rows, list) and isinstance(count, int) and len(rows) == count, "generation registry count drift")
    current_id = registry.get("currentGenerationId")
    current_env: dict[str, Any] | None = None
    eligibility_by_id: dict[str, bool] = {}
    for row in rows:
        require(isinstance(row, dict), "generation registry row invalid")
        generation_id = row.get("generationId")
        require(isinstance(generation_id, str), "generationId invalid")
        try:
            eligibility_by_id[generation_id] = writer.validate_record(row)
        except Exception as exc:
            raise Fail(f"generation record validation failed for {generation_id}: {exc}") from exc
    if count:
        require(isinstance(rows[-1], dict) and rows[-1].get("generationId") == current_id, "current generation must equal latest append-only record")
        env_ref = rows[-1].get("environmentRecordRef")
        require(isinstance(env_ref, str) and (ROOT / env_ref).is_file(), "current environment record missing")
        current_env = load(ROOT / env_ref)
    else:
        require(current_id is None, "empty generation registry requires null currentGenerationId")

    preflight_eligible_count = sum(1 for value in eligibility_by_id.values() if value)
    current_eligible = bool(current_id and eligibility_by_id.get(current_id) is True)
    status_value = current_env.get("status") if current_env else None
    boundary_value = current_env.get("evidenceBoundary", {}) if current_env else {}
    provisioned = status_value in {"PROVISIONED_UNVALIDATED", "VALIDATION_IN_PROGRESS", "VALIDATED_LOCAL_NONPRODUCTION"}
    validated = status_value == "VALIDATED_LOCAL_NONPRODUCTION"
    reviewed = bool(current_eligible and boundary_value.get("independentReviewCompleted") is True)
    equivalent = current_eligible

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "generation authority state missing")
    boundary["registeredGenerationCount"] = count
    boundary["preflightEligibleGenerationCount"] = preflight_eligible_count
    boundary["currentGenerationId"] = current_id
    boundary["environmentProvisioned"] = provisioned
    boundary["environmentValidated"] = validated
    boundary["productionEquivalentDependencies"] = equivalent
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    readiness["contractDefined"] = True
    readiness["registryDefined"] = True
    readiness["registryRecordSchemaDefined"] = GEN_SCHEMA.is_file()
    readiness["environmentRecordSemanticValidatorImplemented"] = ENV_VALIDATOR.is_file()
    readiness["writerImplemented"] = WRITER.is_file()
    readiness["validatorImplemented"] = VALIDATOR.is_file()
    readiness["negativeAdmissionSuiteImplemented"] = NEGATIVE.is_file()
    readiness["automaticWorkflowImplemented"] = True
    readiness["generationRegistered"] = count > 0
    readiness["preflightEligibleGenerationAvailable"] = preflight_eligible_count > 0
    readiness["generationEvidenceBound"] = count > 0
    readiness["independentReviewCompleted"] = reviewed
    readiness["productionEquivalentDependencies"] = equivalent
    readiness["productionReady"] = False
    if count == 0:
        contract["limitations"] = [
            "no production-equivalent environment generation is registered",
            "this contract prevents cross-generation evidence reuse but does not provision infrastructure",
            "a registered generation and hash match do not by themselves prove environment equivalence or restore-drill preflight eligibility",
            "preflight eligibility additionally requires a fully validated environment record, production-equivalent dependency controls, repository-resolvable evidence references and independent review evidence",
            "production traffic and production credentials remain outside automatic evidence generation"
        ]
    else:
        contract["limitations"] = [
            "registered environment generations remain non-production evidence and may include planned/provisioned/rejected historical states",
            "generation registration does not by itself approve load, restore, failure-drill or production promotion",
            "restore-drill preflight may use only semantically validated generations whose environment records prove production-equivalent dependencies and independent review with repository-resolvable evidence",
            "production traffic and production credentials remain outside automatic evidence generation"
        ]
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"generation validator failed:\n{completed.stdout[-9000:]}{completed.stderr[-9000:]}")

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-006"), None)
    require(isinstance(gate, dict), "OPS-P0-006 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-006 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-006 authority arrays missing")
    evidence = (
        "production-equivalent environment generation admission is machine-readable and append-only: load, restore, failure-drill and review evidence must bind immutable generation, environment/dependency/evidence/material-delta hashes and source commit; "
        f"registered generations={count}, preflight-eligible generations={preflight_eligible_count}, current generation={current_id or 'none'}, and current production-equivalent dependencies={str(equivalent).lower()}; registration alone never creates preflight eligibility"
    )
    stale_prefix = "production-equivalent environment generation admission is machine-readable and append-only:"
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(stale_prefix))]
    append_once(existing, evidence)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"generation evidence ref missing: {ref}")
        append_once(refs, ref)

    joined = "\n".join(str(item).lower() for item in missing)
    require("production topology" in joined, "production topology blocker must remain")
    if preflight_eligible_count == 0:
        require("production-equivalent dependency behavior" in joined, "production-equivalent dependency blocker must remain")

    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Memory OS production-equivalent generation status reconciliation PASS")
    print(f"generation registry entries: {count}")
    print(f"preflight-eligible generations: {preflight_eligible_count}")
    print(f"current generation: {current_id or 'none'}")
    print(f"current production-equivalent dependencies: {str(equivalent).lower()}")
    print("registration implies preflight eligibility: false")
    print("cross-generation evidence reuse: forbidden")
    print("OPS-P0-006: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION STATUS FAILED: {exc}")
        raise SystemExit(1)
