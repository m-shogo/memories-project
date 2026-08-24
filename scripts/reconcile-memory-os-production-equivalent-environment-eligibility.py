#!/usr/bin/env python3
"""Reconcile the read-only restore-preflight environment-generation eligibility authority."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/production-equivalent-environment-eligibility-contract.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
GEN_CONTRACT_REL = Path("contracts/operations/production-equivalent-environment-generation-contract.v1.json")
HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-production-equivalent-environment-eligibility.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
CONTRACT = ROOT / CONTRACT_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
GEN_CONTRACT = ROOT / GEN_CONTRACT_REL
HELPER = ROOT / HELPER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "environment eligibility contract"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "environment generation registry"),
        (GEN_CONTRACT, GEN_CONTRACT_REL, "environment generation contract"),
        (HELPER, HELPER_REL, "environment generation eligibility helper"),
        (VALIDATOR, VALIDATOR_REL, "environment eligibility validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
    ):
        require_exact_repo_file(path, expected, field)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_helper():
    require_exact_repo_file(HELPER, HELPER_REL, "environment generation eligibility helper")
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_eligibility_reconcile", HELPER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_post_validator(path: Path, expected_relative: Path, field: str) -> None:
    require_exact_repo_file(path, expected_relative, field)
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"post-reconcile {field} failed:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}",
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    enforce_runtime_authorities()
    try:
        original_contract_text = CONTRACT.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {CONTRACT.relative_to(ROOT)}: {exc}") from exc
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

    gen_boundary = generation_contract.get("currentBoundary")
    require(isinstance(gen_boundary, dict), "generation boundary missing")
    require(gen_boundary.get("registeredGenerationCount") == mapping["registeredGenerationCount"], "generation registered count drift")
    require(gen_boundary.get("preflightEligibleGenerationCount") == mapping["preflightEligibleGenerationCount"], "generation eligible count drift")

    updated_contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    try:
        atomic_write_text(CONTRACT, updated_contract_text)
        run_post_validator(VALIDATOR, VALIDATOR_REL, "environment eligibility validator")
        run_post_validator(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    except Exception:
        try:
            atomic_write_text(CONTRACT, original_contract_text)
        except OSError as restore_exc:
            raise Fail(f"eligibility contract rollback failed: {restore_exc}") from restore_exc
        raise

    print("Memory OS production-equivalent environment eligibility reconciliation PASS")
    print(f"registered generations: {mapping['registeredGenerationCount']}")
    print(f"preflight-eligible generations: {mapping['preflightEligibleGenerationCount']}")
    print(f"distinct eligible environments: {mapping['distinctPreflightEligibleEnvironmentCount']}")
    print(f"eligible directed restore pairs: {mapping['eligibleDirectedRestorePairCount']}")
    print("canonical data/executable authorities enforced: true")
    print("atomic eligibility contract replacement: true")
    print("aggregate operability validation inside transaction: true")
    print("failed post-validation leaves eligibility authority mutation behind: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT ENVIRONMENT ELIGIBILITY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
