#!/usr/bin/env python3
"""Prove parser artifact append and reconcile reject corrupt registry authority."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/register-memory-os-parser-artifact.py"
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-parser-artifact-registry.py"
REGISTRY_PATH = ROOT / "contracts/operations/parser-artifact-registry.v1.json"
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
    return load_module(WRITER_PATH, "parser_artifact_writer_registry_negative")


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
        "artifactId": artifact_id,
        "artifactSha256": "0" * 64,
        "adapterId": "generic-csv",
        "adapterVersion": "1.0.0",
        "buildProvenanceRef": refs[0],
        "securityReviewRef": refs[1],
        "retentionEvidenceRef": refs[2],
        "replayEvidenceRefs": [refs[3]],
        "rollbackRetentionState": {
            "state": "RETENTION_PENDING",
            "immutableLocationVerified": False,
            "verificationEvidenceRef": None,
        },
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

    for label, mutate in (
        ("missing evidence digest authority", lambda value: value.pop("evidenceDigestsByArtifactId")),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
    ):
        expect_reconcile_rejection(reconciler, base, label, mutate)

    bound = synthetic_bound_registry(base)
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

    require(REGISTRY_PATH.read_bytes() == json.dumps(base, indent=2, ensure_ascii=False).encode("utf-8") + b"\n" or
            json.loads(REGISTRY_PATH.read_text(encoding="utf-8")) == base,
            "parser registry was not restored after reconcile negatives")
    print("Parser artifact registry authority negative PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"PARSER ARTIFACT REGISTRY AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
