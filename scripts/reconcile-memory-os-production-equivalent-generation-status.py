#!/usr/bin/env python3
"""Reconcile immutable environment-generation registry into bounded operability authority."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import stat
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
    """Read a bounded canonical authority from one regular inode."""
    repo_relative(path)
    require(hasattr(os, "O_NOFOLLOW") and hasattr(os, "O_NONBLOCK"),
            "environment generation authority safe read unavailable")
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        require(stat.S_ISREG(os.fstat(descriptor).st_mode),
                "environment generation authority source is not a regular file")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = -1
            raw = source.read(MAX_AUTHORITY_BYTES + 1)
    except OSError:
        raise Fail("cannot read environment generation authority") from None
    finally:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                raise Fail("environment generation authority read descriptor cleanup failed") from None
    require(len(raw) <= MAX_AUTHORITY_BYTES,
            "environment generation authority source size limit exceeded")
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        raise Fail("environment generation authority source UTF-8 invalid") from None


MAX_AUTHORITY_BYTES = 1024 * 1024


def write_text(path: Path, text: str) -> None:
    """Publish one bounded authority with owned descriptors and private failures."""
    relative = repo_relative(path)
    require(path.parent.is_dir(), f"authority parent missing: {relative.parent}")
    require(not path.is_symlink(), "environment generation authority target symlink refused")
    require(isinstance(text, str), "environment generation authority payload must be text")
    try:
        require(len(text.encode("utf-8")) <= MAX_AUTHORITY_BYTES,
                "environment generation authority payload size limit exceeded")
    except UnicodeError:
        raise Fail("environment generation authority payload encoding invalid") from None

    descriptor: int | None = None
    temp_name: str | None = None
    try:
        mode = path.stat().st_mode & 0o7777 if path.exists() else None
        descriptor, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True)
        if mode is not None:
            os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            descriptor = None
            written = handle.write(text)
            require(type(written) is int and written == len(text),
                    "cannot atomically write environment generation authority")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except Exception:
        raise Fail("cannot atomically write environment generation authority") from None
    finally:
        cleanup_failed = False
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                cleanup_failed = True
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise Fail("environment generation authority temporary cleanup failed") from None


def restore_authorities(authorities: tuple[tuple[Path, str], ...]) -> None:
    """Attempt every restore and report only a fixed incomplete class."""
    failed = False
    for path, text in authorities:
        try:
            write_text(path, text)
        except Exception:
            failed = True
    if failed:
        raise Fail("environment generation authority rollback incomplete") from None


def load(path: Path) -> dict[str, Any]:
    """Reject ambiguous JSON authority before any derived status publication."""
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result,
                    "environment generation authority JSON duplicate key refused")
            result[key] = value
        return result

    def reject_nonfinite(_value: str) -> None:
        raise Fail("environment generation authority JSON nonfinite number refused")

    def finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number),
                "environment generation authority JSON nonfinite number refused")
        return number

    def bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128,
                "environment generation authority JSON integer too large")
        return int(value)

    try:
        value = json.loads(
            read_text(path), object_pairs_hook=reject_duplicates,
            parse_constant=reject_nonfinite, parse_float=finite_float,
            parse_int=bounded_int,
        )
    except Fail:
        raise
    except (json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("environment generation authority JSON invalid") from None
    require(isinstance(value, dict),
            "environment generation authority JSON root must be object")
    return value


def load_writer():
    require_exact_repo_file(WRITER, WRITER_REL, "environment generation writer")
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_writer_for_reconcile", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation writer")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError):
        raise Fail("cannot load environment generation writer") from None
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


VALIDATOR_TIMEOUT_SECONDS = 90


def run_validator(path: Path, expected_relative: Path, label: str) -> None:
    """Execute a canonical child with bounded time and no captured private output."""
    require_exact_repo_file(path, expected_relative, label)
    try:
        completed = subprocess.run(
            [sys.executable, str(path)], cwd=ROOT,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=VALIDATOR_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail("environment generation child validator failed") from None
    require(type(completed.returncode) is int and completed.returncode == 0,
            "environment generation child validator failed")


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
        try:
            restore_authorities(
                (
                    (CONTRACT, original_contract_text),
                    (STATUS, original_status_text),
                )
            )
        except Exception:
            raise Fail("environment generation status reconcile failed; rollback incomplete") from None
        raise Fail("environment generation status reconcile failed; rollback completed") from None

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
