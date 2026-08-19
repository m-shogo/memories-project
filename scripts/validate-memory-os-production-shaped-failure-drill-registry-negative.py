#!/usr/bin/env python3
"""Fail-closed corruption suite for production-shaped failure-drill authority."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/production-shaped-failure-drill-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/production-shaped-failure-drill-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER_PATH = ROOT / "scripts/register-memory-os-production-shaped-failure-drill.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-production-shaped-failure-drills.py"
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-production-shaped-failure-drills.py"
ALTERNATE_LOCK = ROOT / "contracts/operations/.production-shaped-failure-drill-substitute.lock"
ALTERNATE_GENERATION_WRITER = ROOT / "scripts/register-memory-os-rate-limit-distributed-runtime.py"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expect_writer_rejected(writer: Any, name: str, mutate: Callable[[dict[str, Any]], None], original: bytes) -> None:
    registry = json.loads(original.decode("utf-8"))
    mutate(registry)
    write_json(REGISTRY, registry)
    corrupted = REGISTRY.read_bytes()
    try:
        try:
            writer.validate_registry_before_append(registry)
        except writer.Fail:
            pass
        else:
            raise RuntimeError(f"{name}: corrupt registry accepted before append")
        if REGISTRY.read_bytes() != corrupted:
            raise RuntimeError(f"{name}: rejected writer validation mutated registry")
    finally:
        REGISTRY.write_bytes(original)


def expect_reconciler_rejected(reconciler: Any, name: str, mutate: Callable[[dict[str, Any]], None], original: bytes) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    registry = json.loads(original.decode("utf-8"))
    mutate(registry)
    write_json(REGISTRY, registry)
    corrupted = REGISTRY.read_bytes()
    try:
        try:
            reconciler.main()
        except reconciler.Fail:
            pass
        else:
            raise RuntimeError(f"{name}: reconciler accepted corrupt registry")
        if REGISTRY.read_bytes() != corrupted:
            raise RuntimeError(f"{name}: reconciler mutated corrupt registry")
        if CONTRACT.read_bytes() != contract_before:
            raise RuntimeError(f"{name}: reconciler mutated contract before rejecting corrupt registry")
        if STATUS.read_bytes() != status_before:
            raise RuntimeError(f"{name}: reconciler mutated production status before rejecting corrupt registry")
    finally:
        REGISTRY.write_bytes(original)
        CONTRACT.write_bytes(contract_before)
        STATUS.write_bytes(status_before)


def expect_generation_authority_rejected(
    writer: Any,
    reconciler: Any,
    name: str,
    mutate: Callable[[dict[str, Any]], None],
    failure_registry_original: bytes,
    generation_registry_original: bytes,
) -> None:
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    generation_registry = json.loads(generation_registry_original.decode("utf-8"))
    mutate(generation_registry)
    write_json(GEN_REGISTRY, generation_registry)
    corrupted_generation = GEN_REGISTRY.read_bytes()
    failure_registry = json.loads(failure_registry_original.decode("utf-8"))
    try:
        try:
            writer.validated_generation_rows()
        except writer.Fail:
            pass
        else:
            raise RuntimeError(f"{name}: direct record generation helper accepted corrupt environment generation authority")
        try:
            writer.validate_registry_before_append(failure_registry)
        except writer.Fail:
            pass
        else:
            raise RuntimeError(f"{name}: writer accepted corrupt environment generation authority")
        try:
            reconciler.main()
        except reconciler.Fail:
            pass
        else:
            raise RuntimeError(f"{name}: reconciler accepted corrupt environment generation authority")
        if GEN_REGISTRY.read_bytes() != corrupted_generation:
            raise RuntimeError(f"{name}: corrupt environment generation authority was mutated")
        if REGISTRY.read_bytes() != failure_registry_original:
            raise RuntimeError(f"{name}: failure-drill registry mutated while rejecting upstream authority")
        if CONTRACT.read_bytes() != contract_before:
            raise RuntimeError(f"{name}: contract mutated while rejecting upstream authority")
        if STATUS.read_bytes() != status_before:
            raise RuntimeError(f"{name}: production status mutated while rejecting upstream authority")
    finally:
        GEN_REGISTRY.write_bytes(generation_registry_original)
        REGISTRY.write_bytes(failure_registry_original)
        CONTRACT.write_bytes(contract_before)
        STATUS.write_bytes(status_before)


def expect_contract_lock_rejected(validator: Any) -> None:
    original = CONTRACT.read_bytes()
    contract = json.loads(original.decode("utf-8"))
    contract["appendLockPath"] = str(ALTERNATE_LOCK.relative_to(ROOT))
    write_json(CONTRACT, contract)
    corrupted = CONTRACT.read_bytes()
    try:
        try:
            validator.main()
        except validator.Fail:
            pass
        else:
            raise RuntimeError("substituted failure-drill append lock accepted by contract validator")
        if CONTRACT.read_bytes() != corrupted:
            raise RuntimeError("rejected failure-drill lock validation mutated contract")
    finally:
        CONTRACT.write_bytes(original)


def expect_transactional_contract_rejected(validator: Any) -> None:
    original = CONTRACT.read_bytes()
    contract = json.loads(original.decode("utf-8"))
    contract["recordRequirements"]["appendMustRevalidateCanonicalRegistryAndRollbackOnFailure"] = False
    write_json(CONTRACT, contract)
    corrupted = CONTRACT.read_bytes()
    try:
        try:
            validator.main()
        except validator.Fail:
            pass
        else:
            raise RuntimeError("disabled failure-drill append rollback authority accepted")
        if CONTRACT.read_bytes() != corrupted:
            raise RuntimeError("rejected failure-drill append rollback validation mutated contract")
    finally:
        CONTRACT.write_bytes(original)


def expect_writer_lock_rejected(validator: Any, writer: Any) -> None:
    original = writer.LOCK
    try:
        writer.LOCK = ALTERNATE_LOCK
        try:
            validator.validate_writer_authority(writer)
        except validator.Fail:
            return
        raise RuntimeError("substituted failure-drill writer lock accepted")
    finally:
        writer.LOCK = original


def expect_writer_generation_writer_rejected(validator: Any, writer: Any) -> None:
    original = writer.GEN_WRITER
    try:
        writer.GEN_WRITER = ALTERNATE_GENERATION_WRITER
        try:
            validator.validate_writer_authority(writer)
        except validator.Fail:
            return
        raise RuntimeError("substituted failure-drill generation writer accepted")
    finally:
        writer.GEN_WRITER = original


def expect_writer_transactional_authority_rejected(validator: Any, writer: Any) -> None:
    original = writer.append_registry_transactionally
    try:
        writer.append_registry_transactionally = None
        try:
            validator.validate_writer_authority(writer)
        except validator.Fail:
            return
        raise RuntimeError("missing failure-drill transactional append helper accepted")
    finally:
        writer.append_registry_transactionally = original


def expect_append_rollback(writer: Any, original: bytes) -> None:
    candidate = json.loads(original.decode("utf-8"))
    candidate["productionReady"] = True
    original_validator = writer.validate_registry_before_append

    def fail_after_write(_: dict[str, Any]) -> list[dict[str, Any]]:
        raise writer.Fail("synthetic post-append validation failure")

    try:
        writer.validate_registry_before_append = fail_after_write
        try:
            writer.append_registry_transactionally(candidate, original)
        except writer.Fail:
            pass
        else:
            raise RuntimeError("synthetic post-append validation failure was accepted")
        if REGISTRY.read_bytes() != original:
            raise RuntimeError("failure-drill registry did not roll back after post-append validation failure")
    finally:
        writer.validate_registry_before_append = original_validator
        REGISTRY.write_bytes(original)


def expect_side_commit_rejected(writer: Any) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "memory-os-negative-fixture",
            "GIT_AUTHOR_EMAIL": "negative-fixture@example.invalid",
            "GIT_COMMITTER_NAME": "memory-os-negative-fixture",
            "GIT_COMMITTER_EMAIL": "negative-fixture@example.invalid",
        }
    )
    completed = subprocess.run(
        ["git", "commit-tree", "HEAD^{tree}", "-p", "HEAD^"],
        cwd=ROOT,
        input="failure-drill side commit fixture\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"cannot create side-commit fixture: {completed.stderr.strip()}")
    side_commit = completed.stdout.strip()
    try:
        writer.require_source_commit_ancestor(side_commit)
    except writer.Fail:
        return
    raise RuntimeError("detached side commit accepted as failure-drill source authority")


def expect_review_payload_rejected(writer: Any, name: str, payload: dict[str, Any], record: dict[str, Any], role: str) -> None:
    try:
        writer.validate_review_payload(payload, record, name, role)
    except writer.Fail:
        return
    raise RuntimeError(f"{name}: invalid independent review payload accepted")


def expect_review_namespace_rejected(writer: Any) -> None:
    record = {"securityReviewRef": "contracts/operations/production-shaped-failure-drill-contract.v1.json"}
    try:
        writer.validate_review(record, "securityReviewRef", "SECURITY")
    except writer.Fail:
        return
    raise RuntimeError("generic repository JSON accepted as failure-drill independent review authority")


def validate_review_payload_negatives(writer: Any) -> int:
    record = {
        "drillId": "fdr_negative01",
        "scenarioId": "FAIL-PROD-001",
        "environmentClass": "PRODUCTION_EQUIVALENT",
        "environmentIdentityDigest": "1" * 64,
        "environmentGenerationId": "pegen_negative01",
        "sourceCommitSha": "2" * 40,
    }
    base = {
        "schemaVersion": "memory-os-production-shaped-failure-drill-independent-review.v1",
        **record,
        "role": "SECURITY",
        "reviewerId": "security-reviewer",
        "decision": "APPROVED",
        "reviewedAt": "2026-08-16T09:00:00Z",
        "productionTrafficChanged": False,
        "credentialsIncluded": False,
        "automaticProductionPromotion": False,
    }
    writer.validate_review_payload(base, record, "securityReviewRef", "SECURITY")
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("generic review field set", lambda r: r.pop("drillId")),
        ("review role substitution", lambda r: r.__setitem__("role", "OPERABILITY")),
        ("reviewer pseudonym invalid", lambda r: r.__setitem__("reviewerId", "Reviewer Name")),
        ("review decision rejected", lambda r: r.__setitem__("decision", "REJECTED")),
        ("review drill binding drift", lambda r: r.__setitem__("drillId", "fdr_other001")),
        ("review generation binding drift", lambda r: r.__setitem__("environmentGenerationId", "pegen_other01")),
        ("review source binding drift", lambda r: r.__setitem__("sourceCommitSha", "3" * 40)),
        ("review timestamp invalid", lambda r: r.__setitem__("reviewedAt", "2026-99-99T99:99:99Z")),
        ("review production traffic mutation", lambda r: r.__setitem__("productionTrafficChanged", True)),
        ("review credential inclusion", lambda r: r.__setitem__("credentialsIncluded", True)),
        ("review automatic promotion", lambda r: r.__setitem__("automaticProductionPromotion", True)),
    ]
    for name, mutate in cases:
        payload = deepcopy(base)
        mutate(payload)
        expect_review_payload_rejected(writer, name, payload, record, "SECURITY")
    return len(cases)


def main() -> int:
    writer = load_module(WRITER_PATH, "failure_drill_writer_negative")
    validator = load_module(VALIDATOR_PATH, "failure_drill_validator_negative")
    reconciler = load_module(RECONCILER_PATH, "failure_drill_reconciler_negative")
    original = REGISTRY.read_bytes()
    generation_original = GEN_REGISTRY.read_bytes()
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda r: r.__setitem__("schemaVersion", "broken")),
        ("append-only disabled", lambda r: r.__setitem__("appendOnly", False)),
        ("unknown field", lambda r: r.__setitem__("unexpectedAuthority", True)),
        ("missing evidence digest authority", lambda r: r.pop("evidenceDigestsByDrillId")),
        ("unknown evidence digest drill", lambda r: r["evidenceDigestsByDrillId"].__setitem__("fdr_unknown01", {})),
        ("boolean registered count", lambda r: r.__setitem__("registeredDrillCount", False)),
        ("registered count drift", lambda r: r.__setitem__("registeredDrillCount", 1)),
        ("boolean production-equivalent count", lambda r: r.__setitem__("productionEquivalentDrillCount", False)),
        ("production-equivalent count drift", lambda r: r.__setitem__("productionEquivalentDrillCount", 1)),
        ("boolean production count", lambda r: r.__setitem__("productionDrillCount", False)),
        ("production count drift", lambda r: r.__setitem__("productionDrillCount", 1)),
        ("production readiness promotion", lambda r: r.__setitem__("productionReady", True)),
    ]
    generation_cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("generation registry class drift", lambda r: r.__setitem__("registryClass", "BROKEN")),
        ("generation append-only disabled", lambda r: r.__setitem__("appendOnly", False)),
        ("generation boolean count", lambda r: r.__setitem__("registeredGenerationCount", False)),
        ("generation production evidence promotion", lambda r: r.__setitem__("productionEvidence", True)),
    ]
    try:
        for name, mutate in cases:
            expect_writer_rejected(writer, name, mutate, original)
            expect_reconciler_rejected(reconciler, name, mutate, original)
        for name, mutate in generation_cases:
            expect_generation_authority_rejected(writer, reconciler, name, mutate, original, generation_original)
        expect_contract_lock_rejected(validator)
        expect_transactional_contract_rejected(validator)
        expect_writer_lock_rejected(validator, writer)
        expect_writer_generation_writer_rejected(validator, writer)
        expect_writer_transactional_authority_rejected(validator, writer)
        expect_append_rollback(writer, original)
        expect_side_commit_rejected(writer)
        expect_review_namespace_rejected(writer)
        review_case_count = validate_review_payload_negatives(writer)
    finally:
        REGISTRY.write_bytes(original)
        GEN_REGISTRY.write_bytes(generation_original)

    print("PASS: production-shaped failure-drill registry corruption is rejected before append/reconcile")
    print(f"failure-drill corruption cases: {len(cases)}")
    print(f"upstream generation corruption cases: {len(generation_cases)}")
    print(f"typed independent review negative cases: {review_case_count}")
    print("contract append lock substitution accepted: false")
    print("writer append lock substitution accepted: false")
    print("generation writer substitution accepted: false")
    print("transactional append authority disabled: false")
    print("post-append validation failure persisted registry mutation: false")
    print("generic repository review authority accepted: false")
    print("detached source commit accepted: false")
    print("reconciler auto-heal: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
