#!/usr/bin/env python3
"""Validate backup/restore drill request binding to semantic generation eligibility."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-generation-eligibility-binding-contract.v1.json"
DRILL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
DRILL_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
DRILL_NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-drill-request-negative.py"
ELIGIBILITY_CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json"
ELIGIBILITY_HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"


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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract = load(CONTRACT)
    drill_contract = load(DRILL_CONTRACT)
    drill_registry = load(DRILL_REGISTRY)
    eligibility_contract = load(ELIGIBILITY_CONTRACT)
    writer = load_module(DRILL_WRITER, "memory_os_drill_request_writer_for_generation_binding")
    helper = load_module(ELIGIBILITY_HELPER, "memory_os_generation_eligibility_for_drill_binding")

    require(contract.get("schemaVersion") == "memory-os-backup-restore-drill-generation-eligibility-binding-contract.v1", "binding contract schema drift")
    refs = {
        "drillRequestContract": DRILL_CONTRACT,
        "drillRequestRegistry": DRILL_REGISTRY,
        "drillRequestWriter": DRILL_WRITER,
        "drillRequestNegativeValidator": DRILL_NEGATIVE,
        "generationEligibilityContract": ELIGIBILITY_CONTRACT,
        "generationEligibilityHelper": ELIGIBILITY_HELPER,
        "validator": Path("scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding.py"),
        "workflow": Path(".github/workflows/backup-restore-drill-generation-eligibility-binding.yml"),
    }
    for field, path in refs.items():
        expected = str(path.relative_to(ROOT)) if path.is_absolute() else str(path)
        require(contract.get(field) == expected, f"binding ref drift: {field}")
        require((ROOT / expected).is_file(), f"binding artifact missing: {expected}")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "binding rules must remain fail-closed")

    eligibility = helper.derive()
    eligibility_boundary = eligibility_contract.get("currentBoundary")
    require(isinstance(eligibility_boundary, dict), "generation eligibility boundary missing")
    pair_count = eligibility["eligibleDirectedPairCount"]
    require(eligibility_boundary.get("eligibleDirectedRestorePairCount") == pair_count, "generation eligibility pair count drift")
    require(eligibility_boundary.get("productionEvidence") is False and eligibility_boundary.get("productionReady") is False, "generation eligibility cannot promote production")

    try:
        requests = writer.validate_registry_for_append(drill_registry)
    except Exception as exc:
        raise Fail(f"drill request registry authority invalid: {exc}") from exc
    request_count = drill_registry.get("registeredRequestCount")
    current_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(request_count, int) and not isinstance(request_count, bool), "drill request count must be a non-boolean integer")
    require(isinstance(current_count, int) and not isinstance(current_count, bool), "current drill request count must be a non-boolean integer")

    derived_current = 0
    historical_auditable = 0
    for row in requests:
        try:
            writer.validate_request(row, require_current=False)
        except Exception as exc:
            raise Fail(f"historical drill request is no longer auditable: {row.get('requestId')}: {exc}") from exc
        historical_auditable += 1
        current = writer.request_currently_executable(row)
        if current:
            derived_current += 1
            source = row.get("sourceEnvironmentGenerationId")
            target = row.get("restoreTargetEnvironmentGenerationId")
            try:
                helper.eligible_generation_by_id(source)
                helper.eligible_generation_by_id(target)
            except Exception as exc:
                raise Fail(f"current drill request uses noneligible generation: {row.get('requestId')}: {exc}") from exc
            require(source != target, "current drill request source/target generation must differ")
            eligible_rows = eligibility["unsupersededPreflightEligibleRows"]
            source_rows = [item for item in eligible_rows if item.get("generationId") == source]
            target_rows = [item for item in eligible_rows if item.get("generationId") == target]
            require(len(source_rows) == 1 and len(target_rows) == 1, "current drill request eligible generation lookup drift")
            require(source_rows[0].get("environmentId") != target_rows[0].get("environmentId"), "current drill request source/target environment must differ")
    require(derived_current == current_count, "current executable drill request count derivation drift")
    if current_count > 0:
        require(pair_count > 0, "current executable drill request requires eligible directed restore pair")

    state = drill_contract.get("currentAdmissionState")
    execution = drill_contract.get("executionBoundary")
    require(isinstance(state, dict) and isinstance(execution, dict), "drill request contract state missing")
    require(state.get("registeredRequestCount") == request_count, "drill request contract history count drift")
    require(state.get("currentExecutableRequestCount") == current_count, "drill request contract current count drift")
    require(execution.get("planningAuthorityOnly") is True and execution.get("requestAloneMayExecuteDrill") is False, "drill request may not become execution authority")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "binding currentBoundary missing")
    expected = {
        "eligibleDirectedRestorePairCount": pair_count,
        "reviewedDrillRequestCount": request_count,
        "currentExecutableDrillRequestCount": current_count,
        "historicalAuditableRequestCount": historical_auditable,
    }
    for field, value in expected.items():
        require(boundary.get(field) == value, f"binding boundary drift: {field}")
    require(boundary.get("productionEvidence") is False and boundary.get("productionReady") is False and boundary.get("productionDecision") == "NO_GO", "binding cannot promote production")

    completed = subprocess.run([sys.executable, str(DRILL_NEGATIVE)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"drill request negative suite failed:\n{completed.stdout[-7000:]}{completed.stderr[-7000:]}")

    print("Memory OS drill request semantic generation binding PASS")
    print(f"eligible directed restore pairs: {pair_count}")
    print(f"reviewed/current drill requests: {request_count}/{current_count}")
    print(f"historical auditable requests: {historical_auditable}")
    print("generation registration alone is sufficient: false")
    print("noneligible generation can create current request: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL REQUEST GENERATION ELIGIBILITY BINDING FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
