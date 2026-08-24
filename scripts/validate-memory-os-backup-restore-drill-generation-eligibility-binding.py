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
CONTRACT_REL = Path("contracts/operations/backup-restore-drill-generation-eligibility-binding-contract.v1.json")
DRILL_CONTRACT_REL = Path("contracts/operations/backup-restore-drill-request-contract.v1.json")
DRILL_REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
DRILL_WRITER_REL = Path("scripts/request-memory-os-backup-restore-drill.py")
DRILL_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-drill-request.py")
DRILL_NEGATIVE_REL = Path("scripts/validate-memory-os-backup-restore-drill-request-negative.py")
ELIGIBILITY_CONTRACT_REL = Path("contracts/operations/production-equivalent-environment-eligibility-contract.v1.json")
ELIGIBILITY_HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding.py")
WORKFLOW_REL = Path(".github/workflows/backup-restore-drill-generation-eligibility-binding.yml")
CONTRACT = ROOT / CONTRACT_REL
DRILL_CONTRACT = ROOT / DRILL_CONTRACT_REL
DRILL_REGISTRY = ROOT / DRILL_REGISTRY_REL
DRILL_WRITER = ROOT / DRILL_WRITER_REL
DRILL_VALIDATOR = ROOT / DRILL_VALIDATOR_REL
DRILL_NEGATIVE = ROOT / DRILL_NEGATIVE_REL
ELIGIBILITY_CONTRACT = ROOT / ELIGIBILITY_CONTRACT_REL
ELIGIBILITY_HELPER = ROOT / ELIGIBILITY_HELPER_REL
VALIDATOR = ROOT / VALIDATOR_REL
WORKFLOW = ROOT / WORKFLOW_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def exact_success(result: Any, label: str) -> None:
    require(
        isinstance(result, int) and not isinstance(result, bool) and result == 0,
        f"{label} returned nonzero/invalid result: {result}",
    )


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file() and not path.is_symlink(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "binding contract"),
        (DRILL_CONTRACT, DRILL_CONTRACT_REL, "drill request contract"),
        (DRILL_REGISTRY, DRILL_REGISTRY_REL, "drill request registry"),
        (DRILL_WRITER, DRILL_WRITER_REL, "drill request writer"),
        (DRILL_VALIDATOR, DRILL_VALIDATOR_REL, "drill request validator"),
        (DRILL_NEGATIVE, DRILL_NEGATIVE_REL, "drill request negative validator"),
        (ELIGIBILITY_CONTRACT, ELIGIBILITY_CONTRACT_REL, "generation eligibility contract"),
        (ELIGIBILITY_HELPER, ELIGIBILITY_HELPER_REL, "generation eligibility helper"),
        (VALIDATOR, VALIDATOR_REL, "generation binding validator"),
        (WORKFLOW, WORKFLOW_REL, "generation binding workflow"),
    ):
        require_exact_repo_file(path, expected, field)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        try:
            relative = path.relative_to(ROOT)
        except ValueError:
            relative = path
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, expected_relative: Path, name: str, field: str):
    require_exact_repo_file(path, expected_relative, field)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_negative_suite() -> None:
    require_exact_repo_file(DRILL_NEGATIVE, DRILL_NEGATIVE_REL, "drill request negative validator")
    completed = subprocess.run(
        [sys.executable, str(DRILL_NEGATIVE)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"drill request negative suite failed:\n{completed.stdout[-7000:]}{completed.stderr[-7000:]}",
    )


CANONICAL_REQUIRE = require
CANONICAL_SUBPROCESS_RUN = subprocess.run
CANONICAL_RUNTIME_ENFORCER = enforce_runtime_authorities
CANONICAL_EXECUTION_HELPERS = (
    exact_success,
    require_exact_repo_file,
    load,
    load_module,
    run_negative_suite,
)


def enforce_execution_identity(
    canonical_enforcer=CANONICAL_RUNTIME_ENFORCER,
    canonical_require=CANONICAL_REQUIRE,
    canonical_subprocess_run=CANONICAL_SUBPROCESS_RUN,
    canonical_helpers=CANONICAL_EXECUTION_HELPERS,
) -> None:
    if enforce_runtime_authorities is not canonical_enforcer:
        raise Fail("drill generation binding runtime authority enforcer drift")
    if require is not canonical_require:
        raise Fail("drill generation binding require helper drift")
    if subprocess.run is not canonical_subprocess_run:
        raise Fail("drill generation binding subprocess transport drift")
    current_helpers = (
        exact_success,
        require_exact_repo_file,
        load,
        load_module,
        run_negative_suite,
    )
    if current_helpers != canonical_helpers:
        raise Fail("drill generation binding execution helper drift")


def main(canonical_execution_guard=enforce_execution_identity) -> int:
    if enforce_execution_identity is not canonical_execution_guard:
        raise Fail("drill generation binding execution guard drift")
    enforce_execution_identity()
    enforce_runtime_authorities()
    contract = load(CONTRACT)
    drill_contract = load(DRILL_CONTRACT)
    drill_registry = load(DRILL_REGISTRY)
    eligibility_contract = load(ELIGIBILITY_CONTRACT)
    writer = load_module(
        DRILL_WRITER,
        DRILL_WRITER_REL,
        "memory_os_drill_request_writer_for_generation_binding",
        "drill request writer",
    )
    drill_validator = load_module(
        DRILL_VALIDATOR,
        DRILL_VALIDATOR_REL,
        "memory_os_drill_request_validator_for_generation_binding",
        "drill request validator",
    )
    helper = load_module(
        ELIGIBILITY_HELPER,
        ELIGIBILITY_HELPER_REL,
        "memory_os_generation_eligibility_for_drill_binding",
        "generation eligibility helper",
    )

    require(contract.get("schemaVersion") == "memory-os-backup-restore-drill-generation-eligibility-binding-contract.v1", "binding contract schema drift")
    refs = {
        "drillRequestContract": DRILL_CONTRACT_REL,
        "drillRequestRegistry": DRILL_REGISTRY_REL,
        "drillRequestWriter": DRILL_WRITER_REL,
        "drillRequestNegativeValidator": DRILL_NEGATIVE_REL,
        "generationEligibilityContract": ELIGIBILITY_CONTRACT_REL,
        "generationEligibilityHelper": ELIGIBILITY_HELPER_REL,
        "validator": VALIDATOR_REL,
        "workflow": WORKFLOW_REL,
    }
    for field, relative in refs.items():
        expected = str(relative)
        require(contract.get(field) == expected, f"binding ref drift: {field}")
        require_exact_repo_file(ROOT / relative, relative, f"binding artifact {field}")
    rules = contract.get("rules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "binding rules must remain fail-closed")

    try:
        drill_result = drill_validator.main()
    except drill_validator.Fail as exc:
        raise Fail(f"drill request full admission authority invalid: {exc}") from exc
    exact_success(drill_result, "drill request full admission authority")

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

    run_negative_suite()

    print("Memory OS drill request semantic generation binding PASS")
    print(f"eligible directed restore pairs: {pair_count}")
    print(f"reviewed/current drill requests: {request_count}/{current_count}")
    print(f"historical auditable requests: {historical_auditable}")
    print("canonical data/executable authorities enforced: true")
    print("drill request full admission validator delegated: true")
    print("delegated validator nonzero accepted: false")
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
