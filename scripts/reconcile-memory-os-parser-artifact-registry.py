#!/usr/bin/env python3
"""Reconcile reviewed parser artifact authority without promoting production readiness."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/parser-artifact-registry-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/parser-artifact-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-parser-artifact.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-parser-artifact-registry.py")
VERSION_VALIDATOR_REL = Path("scripts/validate-memory-os-version-compatibility.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
WORKFLOW_REL = Path(".github/workflows/parser-artifact-registry.yml")
RUNBOOK_REL = Path("docs/runbooks/memory-os-parser-artifact-registry.md")
CONTRACT_PATH = ROOT / CONTRACT_REL
REGISTRY_PATH = ROOT / REGISTRY_REL
WRITER_PATH = ROOT / WRITER_REL
VALIDATOR_PATH = ROOT / VALIDATOR_REL
VERSION_VALIDATOR_PATH = ROOT / VERSION_VALIDATOR_REL
OPERABILITY_VALIDATOR_PATH = ROOT / OPERABILITY_VALIDATOR_REL
STATUS_PATH = ROOT / STATUS_REL
WORKFLOW_PATH = ROOT / WORKFLOW_REL
RUNBOOK_PATH = ROOT / RUNBOOK_REL

EXISTING = (
    "append-only reviewed parser artifact registry separating repository test harnesses, source, build outputs, digest strings and CI results from approved artifact bytes",
    "artifact writer recomputes exact SHA-256 and byte length, requires three distinct review roles, approved release bindings, replay evidence and independent retention evidence",
    "test harness worker and Go test binary are explicitly forbidden from being treated as approved production parser artifacts",
)
DYNAMIC_PREFIX = "reviewed parser artifact authority is append-only and fail-closed:"
OBSOLETE = (
    "reviewed parser artifact registry and old parser artifact replay tests",
)
REVIEWED_ARTIFACT_GAP = "reviewed production parser artifact record with exact bytes, build provenance, Security, Runtime and Release Owner approvals"
REPLAY_GAP = "exact registered old parser artifact replay test with deterministic accepted/rejected accounting and protocol binding"
RETENTION_GAP = "independent immutable retention evidence for every parser artifact required by a rollback-eligible approved release"
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


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, relative, field in (
        (CONTRACT_PATH, CONTRACT_REL, "parser artifact contract"),
        (REGISTRY_PATH, REGISTRY_REL, "parser artifact registry"),
        (WRITER_PATH, WRITER_REL, "parser artifact writer"),
        (VALIDATOR_PATH, VALIDATOR_REL, "parser artifact validator"),
        (VERSION_VALIDATOR_PATH, VERSION_VALIDATOR_REL, "version compatibility validator"),
        (OPERABILITY_VALIDATOR_PATH, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (STATUS_PATH, STATUS_REL, "production operability status"),
        (WORKFLOW_PATH, WORKFLOW_REL, "parser artifact workflow"),
        (RUNBOOK_PATH, RUNBOOK_REL, "parser artifact runbook"),
    ):
        require_exact_repo_file(path, relative, field)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> Any:
    require_exact_repo_file(WRITER_PATH, WRITER_REL, "parser artifact writer")
    spec = importlib.util.spec_from_file_location(
        "memory_os_parser_artifact_writer_for_reconcile", WRITER_PATH
    )
    require(spec is not None and spec.loader is not None,
            "cannot load canonical parser writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(Path(module.REGISTRY_PATH).resolve() == REGISTRY_PATH.resolve(),
            "canonical parser registry authority drift")
    require(Path(module.CONTRACT_PATH).resolve() == CONTRACT_PATH.resolve(),
            "canonical parser contract authority drift")
    return module


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def remove_value(items: list[Any], value: str) -> bool:
    before = len(items)
    items[:] = [item for item in items if item != value]
    return len(items) != before


def replace_prefixed(items: list[Any], prefix: str, value: str) -> bool:
    filtered = [item for item in items if not (isinstance(item, str) and item.startswith(prefix))]
    changed = filtered != items
    items[:] = filtered
    changed = append_once(items, value) or changed
    return changed


def _build_atomic_write_bytes(
    mkstemp_impl: Callable[..., tuple[int, str]],
    fdopen_impl: Callable[..., Any],
    fsync_impl: Callable[[int], None],
    chmod_impl: Callable[[Path, int], None],
    replace_impl: Callable[[Path, Path], None],
) -> Callable[[Path, bytes], None]:
    def atomic_write_bytes(path: Path, payload: bytes) -> None:
        mode = path.stat().st_mode & 0o7777
        fd, temp_name = mkstemp_impl(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temp_path = Path(temp_name)
        try:
            with fdopen_impl(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                fsync_impl(handle.fileno())
            chmod_impl(temp_path, mode)
            replace_impl(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    return atomic_write_bytes


atomic_write_bytes = _build_atomic_write_bytes(
    tempfile.mkstemp,
    os.fdopen,
    os.fsync,
    os.chmod,
    os.replace,
)
del _build_atomic_write_bytes


def _build_json_writer(
    atomic_writer: Callable[[Path, bytes], None],
) -> Callable[[Path, dict[str, Any]], None]:
    def write(path: Path, value: dict[str, Any]) -> None:
        payload = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        atomic_writer(path, payload)

    return write


write = _build_json_writer(atomic_write_bytes)
del _build_json_writer


def run_canonical_validators() -> None:
    enforce_runtime_authorities()
    for validator in (
        VALIDATOR_PATH,
        VERSION_VALIDATOR_PATH,
        OPERABILITY_VALIDATOR_PATH,
    ):
        subprocess.run([sys.executable, str(validator)], cwd=ROOT, check=True)


def _build_commit_authority_transaction(
    json_writer: Callable[[Path, dict[str, Any]], None],
    atomic_writer: Callable[[Path, bytes], None],
    default_validator_runner: Callable[[], None],
) -> Callable[..., None]:
    def commit_authority_transaction(
        contract: dict[str, Any],
        status: dict[str, Any],
        *,
        validator_runner: Callable[[], None] | None = None,
    ) -> None:
        originals = {
            CONTRACT_PATH: CONTRACT_PATH.read_bytes(),
            STATUS_PATH: STATUS_PATH.read_bytes(),
        }
        try:
            json_writer(CONTRACT_PATH, contract)
            json_writer(STATUS_PATH, status)
            if validator_runner is None:
                default_validator_runner()
            else:
                validator_runner()
        except BaseException:
            for path, payload in originals.items():
                atomic_writer(path, payload)
            raise

    return commit_authority_transaction


commit_authority_transaction = _build_commit_authority_transaction(
    write,
    atomic_write_bytes,
    run_canonical_validators,
)
del _build_commit_authority_transaction


def main() -> int:
    enforce_runtime_authorities()
    contract = load(CONTRACT_PATH)
    registry = load(REGISTRY_PATH)
    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise ReconcileFailure(f"parser artifact append-only authority invalid: {exc}") from exc

    artifacts = registry.get("artifacts")
    reviewed = registry.get("reviewedArtifactCount")
    retained = registry.get("retainedRollbackArtifactCount")
    replayed = registry.get("replayProvenArtifactCount")
    require(isinstance(artifacts, list), "parser artifact registry artifacts invalid")
    for field, value in (
        ("reviewedArtifactCount", reviewed),
        ("retainedRollbackArtifactCount", retained),
        ("replayProvenArtifactCount", replayed),
    ):
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0,
                f"{field} must be a non-negative integer")
    require(reviewed == len(artifacts), "reviewedArtifactCount drift")
    compatible_release_count = len({
        release_id
        for artifact in artifacts if isinstance(artifact, dict)
        for release_id in artifact.get("compatibleReleaseIds", [])
        if isinstance(release_id, str)
    })

    readiness = contract.get("readiness")
    state = contract.get("currentAuthorityState")
    boundary = contract.get("evidenceBoundary")
    require(isinstance(readiness, dict) and isinstance(state, dict) and isinstance(boundary, dict),
            "parser artifact contract authority missing")
    for field in (
        "contractDefined", "registryImplemented", "writerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
    ):
        require(readiness.get(field) is True, f"parser registry foundation missing: {field}")

    expected_decision = (
        "ARTIFACT_AUTHORITY_AVAILABLE" if reviewed > 0
        else "BLOCKED_NO_REVIEWED_PARSER_ARTIFACT"
    )
    state["reviewedArtifactCount"] = reviewed
    state["retainedRollbackArtifactCount"] = retained
    state["replayProvenArtifactCount"] = replayed
    state["compatibleApprovedReleaseCount"] = compatible_release_count
    state["decision"] = expected_decision

    readiness["reviewedArtifactAvailable"] = reviewed > 0
    readiness["oldArtifactReplayExecuted"] = replayed > 0
    readiness["rollbackArtifactAvailable"] = retained > 0
    readiness["independentRetentionVerified"] = retained > 0
    readiness["independentReviewCompleted"] = False
    readiness["productionReady"] = False

    boundary["testHarnessApproved"] = False
    boundary["productionArtifactApproved"] = reviewed > 0
    boundary["oldArtifactReplayProven"] = replayed > 0
    boundary["rollbackArtifactAvailable"] = retained > 0
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "parser registry cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL" and gate.get("blocking") is True,
            "OPS-P0-008 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-008 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-008 evidenceRefs must be a list")

    changed = False
    for item in EXISTING:
        changed = append_once(existing, item) or changed
    dynamic = (
        f"{DYNAMIC_PREFIX} reviewed artifacts={reviewed}, replay-proven artifacts={replayed}, "
        f"retained rollback artifacts={retained}, compatible approved releases={compatible_release_count}; "
        "source/test harness/CI evidence remains separate and productionEvidence/productionReady remain false"
    )
    changed = replace_prefixed(existing, DYNAMIC_PREFIX, dynamic) or changed
    for item in OBSOLETE:
        changed = remove_value(missing, item) or changed

    for gap, satisfied in (
        (REVIEWED_ARTIFACT_GAP, reviewed > 0),
        (REPLAY_GAP, replayed > 0),
        (RETENTION_GAP, retained > 0),
    ):
        if satisfied:
            changed = remove_value(missing, gap) or changed
        else:
            changed = append_once(missing, gap) or changed

    for ref in REFS:
        require((ROOT / ref).is_file(), f"parser artifact evidence missing: {ref}")
        changed = append_once(refs, ref) or changed

    if reviewed == 0:
        require(REVIEWED_ARTIFACT_GAP in missing, "reviewed parser artifact blocker disappeared")
    if replayed == 0:
        require(REPLAY_GAP in missing, "parser replay blocker disappeared")
    if retained == 0:
        require(RETENTION_GAP in missing, "parser retention blocker disappeared")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True and
            status.get("productionDecision") == "NO_GO",
            "parser artifact authority changed production readiness")

    contract_before = load(CONTRACT_PATH)
    status_before = load(STATUS_PATH)
    if contract == contract_before and status == status_before:
        run_canonical_validators()
        print("Parser artifact registry authority already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    commit_authority_transaction(contract, status)
    print("Reconciled parser artifact authority; OPS-P0-008 remains PARTIAL")
    print(f"reviewed artifacts: {reviewed}")
    print(f"replay-proven artifacts: {replayed}")
    print(f"retained rollback artifacts: {retained}")
    print(f"compatible approved releases: {compatible_release_count}")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ReconcileFailure, subprocess.CalledProcessError) as exc:
        print(f"PARSER ARTIFACT REGISTRY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
