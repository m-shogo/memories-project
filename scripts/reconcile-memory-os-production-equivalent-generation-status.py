#!/usr/bin/env python3
"""Reconcile immutable environment-generation registry into bounded operability authority."""

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
CONTRACT_REL = Path("contracts/operations/production-equivalent-environment-generation-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
GEN_SCHEMA_REL = Path("contracts/operations/production-equivalent-environment-generation-record.v1.schema.json")
ENV_VALIDATOR_REL = Path("scripts/validate-memory-os-production-equivalent-environment-record.py")
WRITER_REL = Path("scripts/register-memory-os-production-equivalent-environment-generation.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-production-equivalent-environment-generation.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
NEGATIVE_REL = Path("scripts/validate-memory-os-production-equivalent-environment-generation-negative.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
GEN_SCHEMA = ROOT / GEN_SCHEMA_REL
ENV_VALIDATOR = ROOT / ENV_VALIDATOR_REL
WRITER = ROOT / WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
NEGATIVE = ROOT / NEGATIVE_REL
STATUS = ROOT / STATUS_REL
EVIDENCE_PREFIX = "production-equivalent environment generation admission is machine-readable and append-only:"
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


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"authority path escapes repository: {path}") from exc


def require_repo_file(path: Path, message: str) -> Path:
    relative = repo_relative(path)
    require((ROOT / relative).is_file(), message)
    return relative


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
        (CONTRACT, CONTRACT_REL, "environment generation contract"),
        (REGISTRY, REGISTRY_REL, "environment generation registry"),
        (GEN_SCHEMA, GEN_SCHEMA_REL, "environment generation record schema"),
        (ENV_VALIDATOR, ENV_VALIDATOR_REL, "environment semantic validator"),
        (WRITER, WRITER_REL, "environment generation writer"),
        (VALIDATOR, VALIDATOR_REL, "environment generation validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (NEGATIVE, NEGATIVE_REL, "environment generation negative suite"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, expected, field)


def canonical_repo_ref(ref: object, message: str) -> Path:
    require(isinstance(ref, str) and bool(ref), message)
    raw = Path(ref)
    require(not raw.is_absolute() and ".." not in raw.parts, message)
    relative = require_repo_file(ROOT / raw, message)
    require(relative.as_posix() == ref, message)
    return ROOT / relative


def read_text(path: Path) -> str:
    relative = repo_relative(path)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {relative}: {exc}") from exc


def write_text(path: Path, text: str) -> None:
    relative = repo_relative(path)
    require(path.parent.is_dir(), f"authority parent missing: {relative.parent}")
    mode = path.stat().st_mode & 0o7777 if path.exists() else None
    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        if mode is not None:
            os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except OSError as exc:
        raise Fail(f"cannot atomically write {relative}: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                pass


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_writer():
    require_exact_repo_file(WRITER, WRITER_REL, "environment generation writer")
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_writer_for_reconcile", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation writer")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"cannot load environment generation writer: {exc}") from exc
    return module


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def replace_single_prefixed(values: list[Any], prefix: str, value: str) -> None:
    matches = [index for index, item in enumerate(values) if isinstance(item, str) and item.startswith(prefix)]
    require(len(matches) <= 1, f"duplicate authority evidence prefix: {prefix}")
    if matches:
        values[matches[0]] = value
    else:
        values.append(value)


def run_validator(path: Path, expected_relative: Path, label: str) -> None:
    require_exact_repo_file(path, expected_relative, label)
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0, f"{label} failed:\n{completed.stdout[-9000:]}{completed.stderr[-9000:]}")


def main() -> int:
    enforce_runtime_authorities()
    original_contract_text = read_text(CONTRACT)
    original_status_text = read_text(STATUS)
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    status = load(STATUS)
    writer = load_writer()
    try:
        rows = writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"generation registry append-only authority invalid: {exc}") from exc
    count = registry["registeredGenerationCount"]
    current_id = registry.get("currentGenerationId")
    current_env: dict[str, Any] | None = None
    eligibility_by_id: dict[str, bool] = {}
    for row in rows:
        generation_id = row.get("generationId")
        require(isinstance(generation_id, str), "generationId invalid")
        try:
            eligibility_by_id[generation_id] = writer.validate_record(row)
        except Exception as exc:
            raise Fail(f"generation record validation failed for {generation_id}: {exc}") from exc
    if count:
        env_path = canonical_repo_ref(rows[-1].get("environmentRecordRef"), "current environment record ref must be canonical repository file")
        current_env = load(env_path)

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
    readiness["registryRecordSchemaDefined"] = True
    readiness["environmentRecordSemanticValidatorImplemented"] = True
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["negativeAdmissionSuiteImplemented"] = True
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
            "production traffic and production credentials remain outside automatic evidence generation",
        ]
    else:
        contract["limitations"] = [
            "registered environment generations remain non-production evidence and may include planned/provisioned/rejected historical states",
            "generation registration does not by itself approve load, restore, failure-drill or production promotion",
            "restore-drill preflight may use only semantically validated generations whose environment records prove production-equivalent dependencies and independent review with repository-resolvable evidence",
            "production traffic and production credentials remain outside automatic evidence generation",
        ]

    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-006"), None)
    require(isinstance(gate, dict), "OPS-P0-006 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-006 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-006 authority arrays missing")
    evidence = (
        f"{EVIDENCE_PREFIX} load, restore, failure-drill and review evidence must bind immutable generation, environment/dependency/evidence/material-delta hashes and source commit; "
        f"registered generations={count}, preflight-eligible generations={preflight_eligible_count}, current generation={current_id or 'none'}, and current production-equivalent dependencies={str(equivalent).lower()}; registration alone never creates preflight eligibility"
    )
    replace_single_prefixed(existing, EVIDENCE_PREFIX, evidence)
    for ref in REFS:
        require_repo_file(ROOT / ref, f"generation evidence ref missing: {ref}")
        append_once(refs, ref)

    joined = "\n".join(str(item).lower() for item in missing)
    require("production topology" in joined, "production topology blocker must remain")
    if preflight_eligible_count == 0:
        require("production-equivalent dependency behavior" in joined, "production-equivalent dependency blocker must remain")

    contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    status_text = json.dumps(status, indent=2, ensure_ascii=False) + "\n"
    try:
        write_text(CONTRACT, contract_text)
        write_text(STATUS, status_text)
        run_validator(VALIDATOR, VALIDATOR_REL, "generation validator")
        run_validator(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    except Exception:
        write_text(CONTRACT, original_contract_text)
        write_text(STATUS, original_status_text)
        raise

    print("Memory OS production-equivalent generation status reconciliation PASS")
    print(f"generation registry entries: {count}")
    print(f"preflight-eligible generations: {preflight_eligible_count}")
    print(f"current generation: {current_id or 'none'}")
    print(f"current production-equivalent dependencies: {str(equivalent).lower()}")
    print("canonical environment generation data/executable authorities enforced: true")
    print("registration implies preflight eligibility: false")
    print("cross-generation evidence reuse: forbidden")
    print("generation contract/status writes use atomic same-directory replace with mode preservation: true")
    print("failed aggregate validation leaves generation/status mutation behind: false")
    print("aggregate operability validation is inside reconciliation transaction: true")
    print("OPS-P0-006: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION STATUS FAILED: {exc}")
        raise SystemExit(1)
