#!/usr/bin/env python3
"""Register empty parser artifact authority without approving an artifact."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/parser-artifact-registry-contract.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/parser-artifact-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"

EXISTING = (
    "append-only reviewed parser artifact registry separating repository test harnesses, source, build outputs, digest strings and CI results from approved artifact bytes",
    "artifact writer recomputes exact SHA-256 and byte length, requires three distinct review roles, approved release bindings, replay evidence and independent retention evidence",
    "test harness worker and Go test binary are explicitly forbidden from being treated as approved production parser artifacts",
    "empty registry records zero reviewed, replay-proven or rollback-retained parser artifacts and BLOCKED_NO_REVIEWED_PARSER_ARTIFACT",
)
OBSOLETE = (
    "reviewed parser artifact registry and old parser artifact replay tests",
)
MISSING = (
    "reviewed production parser artifact record with exact bytes, build provenance, Security, Runtime and Release Owner approvals",
    "exact registered old parser artifact replay test with deterministic accepted/rejected accounting and protocol binding",
    "independent immutable retention evidence for every parser artifact required by a rollback-eligible approved release",
    "approved release artifact-set digest binding and retirement proof that no rollback release depends on a deleted artifact",
)
REFS = (
    "contracts/operations/parser-artifact-registry-contract.v1.json",
    "contracts/operations/parser-artifact-registry.v1.json",
    "docs/runbooks/memory-os-parser-artifact-registry.md",
    "scripts/register-memory-os-parser-artifact.py",
    "scripts/validate-memory-os-parser-artifact-registry.py",
    "scripts/reconcile-memory-os-parser-artifact-registry.py",
    ".github/workflows/parser-artifact-registry.yml",
    "services/import-api/internal/parsersup/worker.go",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def main() -> int:
    contract = load(CONTRACT_PATH)
    registry = load(REGISTRY_PATH)
    readiness = contract.get("readiness")
    state = contract.get("currentAuthorityState")
    require(isinstance(readiness, dict) and isinstance(state, dict),
            "parser artifact contract readiness missing")
    for field in (
        "contractDefined", "registryImplemented", "writerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"parser registry foundation missing: {field}")
    require(registry.get("artifacts") == [] and
            registry.get("reviewedArtifactCount") == 0 and
            registry.get("retainedRollbackArtifactCount") == 0 and
            registry.get("replayProvenArtifactCount") == 0,
            "foundation reconcile cannot overwrite registered artifacts")
    require(state.get("reviewedArtifactCount") == 0 and
            state.get("retainedRollbackArtifactCount") == 0 and
            state.get("replayProvenArtifactCount") == 0 and
            state.get("compatibleApprovedReleaseCount") == 0 and
            state.get("decision") == "BLOCKED_NO_REVIEWED_PARSER_ARTIFACT",
            "empty parser artifact authority state drift")
    require(readiness.get("reviewedArtifactAvailable") is False and
            readiness.get("oldArtifactReplayExecuted") is False and
            readiness.get("rollbackArtifactAvailable") is False and
            readiness.get("independentRetentionVerified") is False and
            readiness.get("productionReady") is False,
            "empty parser registry cannot claim readiness")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "parser registry cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "OPS-P0-008 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-008 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-008 evidenceRefs must be a list")

    changed = False
    for item in EXISTING:
        changed = append_once(existing, item) or changed
    for item in OBSOLETE:
        if item in missing:
            missing.remove(item)
            changed = True
    for item in MISSING:
        changed = append_once(missing, item) or changed
    for ref in REFS:
        require((ROOT / ref).is_file(), f"parser artifact evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    lowered = [str(item).lower() for item in missing]
    for label, terms in {
        "reviewed artifact": ("reviewed", "exact bytes", "approvals"),
        "old artifact replay": ("old parser artifact", "replay", "protocol"),
        "retention": ("immutable retention", "rollback-eligible"),
        "release binding": ("artifact-set digest", "retirement"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered),
                f"required parser artifact gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL" and
            status.get("productionDecision") == "NO_GO",
            "parser registry foundation changed readiness")

    if not changed:
        print("Parser artifact registry authority already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print("Registered empty parser artifact authority; OPS-P0-008 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"PARSER ARTIFACT REGISTRY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
