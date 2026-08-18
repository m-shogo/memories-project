#!/usr/bin/env python3
"""Prove parser artifact append and reconcile reject corrupt registry authority."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/register-memory-os-parser-artifact.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-parser-artifact-registry.py"
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-parser-artifact-registry.py"
CONTRACT_PATH = ROOT / "contracts/operations/parser-artifact-registry-contract.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/parser-artifact-registry.v1.json"
LOCK_PATH = ROOT / "contracts/operations/.parser-artifact-registry.lock"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer() -> Any:
    module = load_module(WRITER_PATH, "parser_artifact_writer_registry_negative")
    require(Path(module.CONTRACT_PATH).resolve() == CONTRACT_PATH.resolve(),
            "parser writer contract authority drift")
    require(Path(module.REGISTRY_PATH).resolve() == REGISTRY_PATH.resolve(),
            "parser writer registry authority drift")
    require(Path(module.LOCK_PATH).resolve() == LOCK_PATH.resolve(),
            "parser writer append lock authority drift")
    return module


def load_reconciler() -> Any:
    return load_module(RECONCILER_PATH, "parser_artifact_reconciler_registry_negative")


def expect_rejection(writer: Any, base: dict[str, Any], label: str,
                     mutate: Callable[[dict[str, Any]], None]) -> None:
    candidate = copy.deepcopy(base)
    mutate(candidate)
    try:
        writer.validate_registry_for_append(candidate)
    except writer.RegistrationFailure:
        return
    raise NegativeFailure(f"writer accepted corrupt parser registry: {label}")


def expect_validator_rejection(label: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(completed.returncode != 0,
            f"standalone validator accepted corrupt parser authority: {label}")


def expect_reconcile_rejection(reconciler: Any, base: dict[str, Any], label: str,
                               mutate: Callable[[dict[str, Any]], None]) -> None:
    original_registry = REGISTRY_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    candidate = copy.deepcopy(base)
    mutate(candidate)
    try:
        REGISTRY_PATH.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
        try:
            reconciler.main()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise NegativeFailure(f"reconciler accepted corrupt parser registry: {label}")
        require(STATUS_PATH.read_bytes() == original_status,
                f"reconciler mutated status after corrupt parser registry: {label}")
    finally:
        REGISTRY_PATH.write_bytes(original_registry)
        if STATUS_PATH.read_bytes() != original_status:
            STATUS_PATH.write_bytes(original_status)


def synthetic_bound_registry(base: dict[str, Any]) -> dict[str, Any]:
    candidate = copy.deepcopy(base)
    artifact_id = "par_fake0000"
    refs = [
        "contracts/operations/parser-artifact-registry-contract.v1.json",
        "contracts/operations/production-operability-status.json",
        "contracts/operations/backup-restore-contract.v1.json",
        "docs/fixtures/memory-os-operability/parser-restart-matrix-results.sample.v1.json",
    ]
    record = {
        "schemaVersion": "memory-os-parser-artifact-record.v1",
        "artifactId": artifact_id,
        "adapterId": "generic-csv",
        "adapterVersion": "1.0.0",
        "artifactSha256": "0" * 64,
        "artifactSizeBytes": 1,
        "artifactFormat": "ELF_EXECUTABLE",
        "targetOs": "linux",
        "targetArch": "amd64",
        "protocolVersion": "memory-os-parser-frame-v1",
        "registeredAt": "2026-08-17T00:00:00Z",
        "reviewClass": "REVIEWED_PARSER_ARTIFACT",
        "approvers": [
            {"role": "SECURITY_REVIEWER", "approverRef": "apr_security01"},
            {"role": "RUNTIME_REVIEWER", "approverRef": "apr_runtime002"},
            {"role": "RELEASE_OWNER", "approverRef": "apr_release003"},
        ],
        "buildProvenanceRef": refs[0],
        "securityReviewRef": refs[1],
        "retentionEvidenceRef": refs[2],
        "replayEvidenceRefs": [refs[3]],
        "compatibleReleaseIds": ["rel_fake0000"],
        "rollbackRetentionState": {
            "state": "RETENTION_PENDING",
            "immutableLocationVerified": False,
            "verificationEvidenceRef": None,
        },
        "openRisks": [],
    }
    candidate["artifacts"] = [record]
    candidate["reviewedArtifactCount"] = 1
    candidate["retainedRollbackArtifactCount"] = 0
    candidate["replayProvenArtifactCount"] = 1
    candidate["latestReviewedArtifactId"] = artifact_id
    candidate["evidenceDigestsByArtifactId"] = {
        artifact_id: {
            ref: hashlib.sha256((ROOT / ref).read_bytes()).hexdigest()
            for ref in refs
        }
    }
    return candidate


def main() -> int:
    writer = load_writer()
    reconciler = load_reconciler()
    contract_bytes = CONTRACT_PATH.read_bytes()
    contract = json.loads(contract_bytes.decode("utf-8"))
    require(contract.get("appendLockPath") == str(LOCK_PATH.relative_to(ROOT)),
            "parser contract append lock authority drift")
    base = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    require(isinstance(base, dict), "parser registry must be object")
    writer.validate_registry_for_append(copy.deepcopy(base))

    cases: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
        ("boolean reviewed count", lambda value: value.__setitem__("reviewedArtifactCount", True)),
        ("reviewed count drift", lambda value: value.__setitem__("reviewedArtifactCount", 1)),
        ("retained count drift", lambda value: value.__setitem__("retainedRollbackArtifactCount", 1)),
        ("replay count drift", lambda value: value.__setitem__("replayProvenArtifactCount", 1)),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("latest pointer drift", lambda value: value.__setitem__("latestReviewedArtifactId", "par_fake0000")),
        ("missing evidence digest authority", lambda value: value.pop("evidenceDigestsByArtifactId")),
        ("unknown evidence digest artifact", lambda value: value["evidenceDigestsByArtifactId"].__setitem__("par_fake0000", {})),
        ("unknown registry field", lambda value: value.__setitem__("unexpectedAuthority", True)),
    )
    for label, mutate in cases:
        expect_rejection(writer, base, label, mutate)

    try:
        corrupt_contract = copy.deepcopy(contract)
        corrupt_contract["appendLockPath"] = "contracts/operations/.parser-artifact-registry-alternate.lock"
        CONTRACT_PATH.write_text(json.dumps(corrupt_contract, indent=2) + "\n", encoding="utf-8")
        expect_validator_rejection("append lock binding drift")
    finally:
        CONTRACT_PATH.write_bytes(contract_bytes)

    for label, mutate in (
        ("missing evidence digest authority", lambda value: value.pop("evidenceDigestsByArtifactId")),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
    ):
        expect_reconcile_rejection(reconciler, base, label, mutate)

    bound = synthetic_bound_registry(base)
    original_release_ids = writer.approved_release_ids
    try:
        writer.approved_release_ids = lambda: {"rel_fake0000"}
        writer.validate_registry_for_append(copy.deepcopy(bound))
        artifact_id = bound["latestReviewedArtifactId"]
        first_ref = next(iter(bound["evidenceDigestsByArtifactId"][artifact_id]))
        expect_rejection(
            writer,
            bound,
            "stale evidence digest",
            lambda value: value["evidenceDigestsByArtifactId"][artifact_id].__setitem__(first_ref, "f" * 64),
        )
        expect_rejection(
            writer,
            bound,
            "missing evidence ref digest",
            lambda value: value["evidenceDigestsByArtifactId"][artifact_id].pop(first_ref),
        )
        expect_rejection(
            writer,
            bound,
            "historical duplicate approver",
            lambda value: value["artifacts"][0]["approvers"].__setitem__(1, copy.deepcopy(value["artifacts"][0]["approvers"][0])),
        )
        expect_rejection(
            writer,
            bound,
            "historical unapproved release",
            lambda value: value["artifacts"][0].__setitem__("compatibleReleaseIds", ["rel_not_approved"]),
        )
        expect_rejection(
            writer,
            bound,
            "historical retention state drift",
            lambda value: value["artifacts"][0]["rollbackRetentionState"].__setitem__("state", "INVALID"),
        )
        expect_rejection(
            writer,
            bound,
            "historical test-harness source marker",
            lambda value: value["artifacts"][0].__setitem__("artifactFormat", "go test harness"),
        )
    finally:
        writer.approved_release_ids = original_release_ids

    require(REGISTRY_PATH.read_bytes() == json.dumps(base, indent=2, ensure_ascii=False).encode("utf-8") + b"\n" or
            json.loads(REGISTRY_PATH.read_text(encoding="utf-8")) == base,
            "parser registry was not restored after reconcile negatives")
    print("Parser artifact registry rejects aggregate corruption, evidence digest drift, and historical artifact semantic drift")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"PARSER ARTIFACT REGISTRY AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
