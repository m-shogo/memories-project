#!/usr/bin/env python3
"""Register bounded compatibility foundations without promoting release readiness."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION_PATH = ROOT / "contracts/operations/version-compatibility-foundations.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RELEASE_CONTRACT_PATH = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
RELEASE_WRITER_PATH = ROOT / "scripts/register-memory-os-release-baseline.py"
ROLLBACK_CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
ROLLBACK_REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
ROLLBACK_WRITER_PATH = ROOT / "scripts/request-memory-os-rollback-rehearsal.py"
PARSER_REGISTRY_PATH = ROOT / "contracts/operations/parser-artifact-registry.v1.json"
PARSER_WRITER_PATH = ROOT / "scripts/register-memory-os-parser-artifact.py"
PAIR_REGISTRY_PATH = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
PAIR_WRITER_PATH = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
FOUNDATION_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-version-compatibility-foundations.py"
OPERABILITY_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-operability.py"

EXISTING = (
    "supplemental compatibility foundation authority records candidate-only, local-CI-only and empty-registry evidence without changing the canonical approved-release matrix",
    "historical candidate and current processes share session authority and persisted Apply idempotency, including simultaneous claim convergence and SIGKILL rollback/retry with zero durable residue",
    "isolated PostgreSQL 16 to 17 logical forward restore preserves schema authority, RLS, active session resolution, deletion non-resurrection and the complete canonical SQL integration suite",
    "release, rollback-admission, release-pair and parser-artifact authorities are independently append-only and cannot be replaced by candidate, CI, tag, digest or test-harness evidence",
)
PAIR_MISSING = "approved predecessor and successor release pair despite candidate-only mixed-version evidence"
PARSER_MISSING = "reviewed production parser artifact with exact-byte replay and immutable rollback retention evidence"
MISSING_ALWAYS = (
    "production rolling traffic, connection drain and application rollback rehearsal using rollback-eligible approved releases",
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


def load_module(path: Path, name: str) -> Any:
    require(path.is_file(), f"missing authority module: {path.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load authority module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def remove_value(items: list[Any], value: str) -> bool:
    original_len = len(items)
    items[:] = [item for item in items if item != value]
    return len(items) != original_len


def require_zero_count(boundaries: dict[str, Any], field: str) -> None:
    value = boundaries.get(field)
    require(isinstance(value, int) and not isinstance(value, bool) and value == 0,
            f"compatibility foundation {field} must be integer zero")


def run_validator(path: Path, label: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"{label} failed:\n{completed.stdout[-4000:]}{completed.stderr[-4000:]}",
    )


def run_canonical_validators() -> None:
    run_validator(FOUNDATION_VALIDATOR_PATH, "post-write compatibility foundation validator")
    run_validator(OPERABILITY_VALIDATOR_PATH, "post-write operability validator")


def commit_status_transaction(
    status: dict[str, Any],
    *,
    validator_runner: Callable[[], None] = run_canonical_validators,
) -> None:
    original = STATUS_PATH.read_bytes()
    try:
        STATUS_PATH.write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        validator_runner()
    except Exception:
        STATUS_PATH.write_bytes(original)
        raise


def validate_source_registries() -> dict[str, int]:
    releases = load(RELEASE_REGISTRY_PATH)
    rollback = load(ROLLBACK_REGISTRY_PATH)
    parsers = load(PARSER_REGISTRY_PATH)
    pairs = load(PAIR_REGISTRY_PATH)
    release_contract = load(RELEASE_CONTRACT_PATH)
    rollback_contract = load(ROLLBACK_CONTRACT_PATH)
    release_writer = load_module(RELEASE_WRITER_PATH, "memory_os_release_baseline_writer_for_foundation")
    rollback_writer = load_module(ROLLBACK_WRITER_PATH, "memory_os_rollback_rehearsal_writer_for_foundation")
    parser_writer = load_module(PARSER_WRITER_PATH, "memory_os_parser_artifact_writer_for_foundation")
    pair_writer = load_module(PAIR_WRITER_PATH, "memory_os_release_pair_writer_for_foundation")
    try:
        release_writer.validate_registry_for_append(releases, release_contract)
        rollback_writer.validate_registry_for_append(rollback, rollback_contract, releases)
        parser_writer.validate_registry_for_append(parsers)
        # The pair writer's shared registry guard revalidates every historical row,
        # including typed Security/Operability independent-review semantics.
        pair_writer.validate_registry_for_append(pairs)
    except Exception as exc:
        raise ReconcileFailure(f"compatibility source authority invalid: {exc}") from exc
    counts = {
        "approvedReleases": releases.get("approvedReleaseCount"),
        "rollbackRequests": rollback.get("rehearsalRequestCount"),
        "reviewedParserArtifacts": parsers.get("reviewedArtifactCount"),
        "approvedReleasePairs": pairs.get("approvedPairCount"),
    }
    for field, value in counts.items():
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0,
                f"compatibility source {field} must be a non-negative integer")
    return counts


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

    source_counts = validate_source_registries()

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
    for item in MISSING_ALWAYS:
        changed = append_once(missing, item) or changed
    if source_counts["approvedReleasePairs"] == 0:
        changed = append_once(missing, PAIR_MISSING) or changed
    else:
        changed = remove_value(missing, PAIR_MISSING) or changed
    if source_counts["reviewedParserArtifacts"] == 0:
        changed = append_once(missing, PARSER_MISSING) or changed
    else:
        changed = remove_value(missing, PARSER_MISSING) or changed
    for ref in REFS:
        require((ROOT / ref).is_file(), f"compatibility foundation evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    lowered = [str(item).lower() for item in missing]
    required_terms = [
        ("rolling rollback", ("rolling", "rollback", "rollback-eligible")),
        ("client skew", ("client/server", "skew")),
        ("database cutover", ("blue-green", "connection-pool", "failover")),
        ("independent review", ("independent review", "critical", "high")),
    ]
    if source_counts["approvedReleasePairs"] == 0:
        required_terms.append(("approved release pair", ("approved", "predecessor", "successor")))
    if source_counts["reviewedParserArtifacts"] == 0:
        required_terms.append(("parser artifact", ("reviewed", "parser artifact", "retention")))
    for label, terms in required_terms:
        require(any(all(term in item for term in terms) for item in lowered),
                f"required compatibility gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL" and
            status.get("productionDecision") == "NO_GO",
            "compatibility foundations changed readiness")

    if not changed:
        print("Compatibility foundation status already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    commit_status_transaction(status)
    print("Registered bounded compatibility foundations; OPS-P0-008 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"COMPATIBILITY FOUNDATION STATUS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
