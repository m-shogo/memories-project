#!/usr/bin/env python3
"""Register bounded compatibility foundations without promoting release readiness."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_PATH = ROOT / "contracts/operations/version-compatibility-foundations.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
ROLLBACK_REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
PARSER_REGISTRY_PATH = ROOT / "contracts/operations/parser-artifact-registry.v1.json"

EXISTING = (
    "supplemental compatibility foundation authority records candidate-only, local-CI-only and empty-registry evidence without changing the canonical approved-release matrix",
    "historical candidate and current processes share session authority and persisted Apply idempotency, including simultaneous claim convergence and SIGKILL rollback/retry with zero durable residue",
    "isolated PostgreSQL 16 to 17 logical forward restore preserves schema authority, RLS, active session resolution, deletion non-resurrection and the complete canonical SQL integration suite",
    "release, rollback-admission and parser-artifact authorities remain deliberately empty so candidate, CI, tag, digest and test-harness evidence cannot manufacture approval",
)
MISSING = (
    "approved predecessor and successor release pair despite candidate-only mixed-version evidence",
    "production rolling traffic, connection drain and application rollback rehearsal using rollback-eligible approved releases",
    "reviewed production parser artifact with exact-byte replay and immutable rollback retention evidence",
    "implemented client/server support windows and client/server skew tests",
    "production-shaped PostgreSQL blue-green cutover with connection-pool drain, replication, failover and irreversible rollback-boundary review",
    "independent review of integrated compatibility controls with zero unresolved Critical or High findings",
)
REFS = (
    "contracts/operations/version-compatibility-foundations.v1.json",
    "docs/runbooks/memory-os-version-compatibility-foundations.md",
    "scripts/validate-memory-os-version-compatibility-foundations.py",
    "scripts/reconcile-memory-os-version-compatibility-foundation-status.py",
    ".github/workflows/version-compatibility-foundations.yml",
)
ZERO_COUNT_FIELDS = (
    "approvedReleaseCount",
    "approvedRollbackPairCount",
    "reviewedParserArtifactCount",
)
EMPTY_AUTHORITIES = (
    (RELEASE_REGISTRY_PATH, "approvedReleaseCount", "releases", "approved release authority"),
    (ROLLBACK_REGISTRY_PATH, "rehearsalRequestCount", "requests", "rollback rehearsal authority"),
    (PARSER_REGISTRY_PATH, "reviewedArtifactCount", "artifacts", "parser artifact authority"),
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


def require_zero_count(boundaries: dict[str, Any], field: str) -> None:
    value = boundaries.get(field)
    require(isinstance(value, int) and not isinstance(value, bool) and value == 0,
            f"compatibility foundation {field} must be integer zero")


def require_empty_registry(registry: dict[str, Any], count_field: str,
                           items_field: str, label: str) -> None:
    count = registry.get(count_field)
    require(isinstance(count, int) and not isinstance(count, bool) and count == 0,
            f"{label} {count_field} must be integer zero")
    require(registry.get(items_field) == [], f"{label} must remain empty")


def main() -> int:
    foundation = load(FOUNDATION_PATH)
    boundaries = foundation.get("aggregateBoundaries")
    require(isinstance(boundaries, dict), "compatibility foundation boundary missing")
    for field in ZERO_COUNT_FIELDS:
        require_zero_count(boundaries, field)
    require(boundaries.get("canonicalReleaseMatrixChanged") is False and
            boundaries.get("productionEvidence") is False and
            boundaries.get("releaseCompatibilityEvidence") is False and
            boundaries.get("productionReady") is False and
            boundaries.get("productionDecision") == "NO_GO",
            "compatibility foundation boundary drift")

    for path, count_field, items_field, label in EMPTY_AUTHORITIES:
        require_empty_registry(load(path), count_field, items_field, label)

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "compatibility foundations cannot change production decision")
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
    for item in MISSING:
        changed = append_once(missing, item) or changed
    for ref in REFS:
        require((ROOT / ref).is_file(), f"compatibility foundation evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    lowered = [str(item).lower() for item in missing]
    for label, terms in {
        "approved release pair": ("approved", "predecessor", "successor"),
        "rolling rollback": ("rolling", "rollback", "rollback-eligible"),
        "parser artifact": ("reviewed", "parser artifact", "retention"),
        "client skew": ("client/server", "skew"),
        "database cutover": ("blue-green", "connection-pool", "failover"),
        "independent review": ("independent review", "critical", "high"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered),
                f"required compatibility gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL" and
            status.get("productionDecision") == "NO_GO",
            "compatibility foundations changed readiness")

    if not changed:
        print("Compatibility foundation status already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print("Registered bounded compatibility foundations; OPS-P0-008 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"COMPATIBILITY FOUNDATION STATUS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
