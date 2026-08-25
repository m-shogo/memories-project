#!/usr/bin/env python3
"""Normalize OPS-P0-007 from committed policy and local restore evidence.

The PostgreSQL and object restore workflows can complete in either order. This
is the local-foundation convergence point: it validates both exact-source PASS
results and registers only local CI foundations. The canonical production
blockers are immutable input authority here: drift must fail closed rather than
being silently repaired by reconciliation.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
INDEX_PATH = ROOT / "contracts/operations/backup-local-foundation-evidence.v1.json"
LOGICAL_RESULT = ROOT / "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json"
OBJECT_RESULT = ROOT / "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json"
BACKUP_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

POLICY_EVIDENCE = (
    "binding backup, PITR, object-version retention and isolated-restore policy with object versioning explicitly separated from backup completion",
    "four protected recovery domains covering canonical PostgreSQL state, exact object versions, release metadata and incident/deletion evidence",
    "nine-phase isolated restore lifecycle with mandatory authority, integrity, idempotency and non-resurrection verification",
    "promotion guards that block routing on cross-tenant visibility, resurrection, recovery-point incoherence, missing artifacts, unmeasured objectives or incomplete checks",
    "canonical backup/restore runbook and fail-closed policy validator",
)
LOGICAL_EVIDENCE = (
    "executable local PostgreSQL logical dump and isolated-restore drill over the complete canonical migration sequence",
    "restored database verification covering all canonical SQL integration suites, four NOBYPASSRLS runtime roles and FORCE RLS tenant tables",
    "synthetic deleted account and account-session digest remain absent after restore and cannot resolve through memory_auth_runtime",
    "synthetic expired-active and revoked-unexpired session rows preserve their terminal authorization semantics after restore and both remain non-resolvable through memory_auth_runtime",
    "privacy-safe exact-source restore result with database identity stored only as a SHA-256 digest",
)
OBJECT_EVIDENCE = (
    "executable local three-bucket MinIO exact-version recovery drill using explicit source and backup VersionIds",
    "complete simulated source-version loss before restore with backup checksum and source-version metadata binding preserved",
    "privacy-safe exact-source object recovery result storing only SHA-256 digests of bucket, key and provider version identifiers",
)
EVIDENCE_REFS = (
    "contracts/operations/backup-restore-contract.v1.json",
    "contracts/operations/backup-local-foundation-evidence.v1.json",
    "contracts/operations/local-logical-restore-contract.v1.json",
    "contracts/operations/local-object-version-restore-contract.v1.json",
    "docs/runbooks/memory-os-backup-restore.md",
    "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json",
    "scripts/memory_os_backup_restore_blockers.py",
    "scripts/validate-memory-os-backup-restore.py",
    "scripts/validate-memory-os-backup-local-foundations.py",
    "scripts/validate-memory-os-local-logical-restore.py",
    "scripts/validate-memory-os-local-object-version-restore.py",
    "scripts/reconcile-memory-os-backup-authority.py",
    ".github/workflows/local-logical-restore.yml",
    ".github/workflows/local-object-version-restore.yml",
    ".github/workflows/reconcile-backup-authority.yml",
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
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def source_is_ancestor(value: Any) -> bool:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        return False
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", value, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def append_all(items: list[str], values: tuple[str, ...]) -> None:
    for value in values:
        if value not in items:
            items.append(value)


def validate_runtime_authority(
    canonical_root=ROOT,
    canonical_status=STATUS_PATH,
    canonical_index=INDEX_PATH,
    canonical_logical_result=LOGICAL_RESULT,
    canonical_object_result=OBJECT_RESULT,
    canonical_backup_validator=BACKUP_VALIDATOR,
    canonical_operability_validator=OPERABILITY_VALIDATOR,
    canonical_blocker_validator=require_canonical_gaps,
    canonical_subprocess_run=subprocess.run,
) -> None:
    require(ROOT == canonical_root, "canonical backup repository root authority drift")
    require(STATUS_PATH == canonical_status, "canonical production status authority drift")
    require(INDEX_PATH == canonical_index, "canonical backup local foundation index authority drift")
    require(LOGICAL_RESULT == canonical_logical_result, "canonical local logical result authority drift")
    require(OBJECT_RESULT == canonical_object_result, "canonical local object result authority drift")
    require(BACKUP_VALIDATOR == canonical_backup_validator, "canonical backup validator authority drift")
    require(OPERABILITY_VALIDATOR == canonical_operability_validator, "canonical operability validator authority drift")
    require(require_canonical_gaps is canonical_blocker_validator, "canonical blocker validator execution authority drift")
    require(subprocess.run is canonical_subprocess_run, "backup authority subprocess execution transport drift")

    for path, expected, label in (
        (canonical_status, canonical_root / "contracts/operations/production-operability-status.json", "production status"),
        (canonical_index, canonical_root / "contracts/operations/backup-local-foundation-evidence.v1.json", "backup local foundation index"),
        (canonical_logical_result, canonical_root / "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json", "local logical restore result"),
        (canonical_object_result, canonical_root / "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json", "local object restore result"),
        (canonical_backup_validator, canonical_root / "scripts/validate-memory-os-backup-restore.py", "backup restore validator"),
        (canonical_operability_validator, canonical_root / "scripts/validate-memory-os-operability.py", "operability validator"),
    ):
        require(path == expected, f"canonical {label} identity drift")
        require(path.is_file(), f"canonical {label} missing")
        require(not path.is_symlink(), f"canonical {label} must not be a symlink")
        try:
            require(path.resolve(strict=True) == expected, f"canonical {label} path drift")
        except OSError as exc:
            raise ReconcileFailure(f"cannot resolve canonical {label}") from exc


def run_validator(path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        check=False,
    )
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"canonical validator rejected reconciled backup authority: {path.name}")


def validate_projected_authority() -> None:
    run_validator(BACKUP_VALIDATOR)
    run_validator(OPERABILITY_VALIDATOR)


def validate_logical(result: dict[str, Any]) -> None:
    require(result.get("schemaVersion") == "memory-os-local-logical-restore-results.v1",
            "logical result schema drift")
    require(source_is_ancestor(result.get("commitSha")),
            "logical result SHA is not an ancestor")
    environment = result.get("environment")
    scenario = result.get("scenario")
    require(isinstance(environment, dict) and
            environment.get("productionEvidence") is False and
            environment.get("containsSecrets") is False,
            "logical result evidence boundary drift")
    require(isinstance(scenario, dict) and scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "logical result is not PASS")
    require(scenario.get("migrationFilesApplied") == 11 and
            scenario.get("sqlIntegrationTestsExecuted") == 11,
            "logical result does not cover the canonical sequence")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "logical assertions missing")
    require(assertions.get("runtimeRolesWithoutBypassRls") == 4,
            "logical runtime role assertion failed")
    require(isinstance(assertions.get("forceRlsTables"), int) and
            assertions["forceRlsTables"] > 0,
            "logical FORCE RLS assertion failed")
    for field in (
        "deletedSyntheticAccountsAfterRestore",
        "deletedSyntheticSessionDigestsAfterRestore",
        "deletedSyntheticSessionsResolvedAfterRestore",
        "expiredSyntheticSessionsResolvedAfterRestore",
        "revokedSyntheticSessionsResolvedAfterRestore",
    ):
        require(assertions.get(field) == 0,
                f"logical non-resurrection assertion failed: {field}")
    require(assertions.get("expiredSyntheticSessionRowsAfterRestore") == 1,
            "expired synthetic session state did not survive restore safely")
    require(assertions.get("revokedSyntheticSessionRowsAfterRestore") == 1,
            "revoked synthetic session state did not survive restore safely")


def validate_object(result: dict[str, Any]) -> None:
    require(result.get("schemaVersion") ==
            "memory-os-local-object-version-restore-results.v1",
            "object result schema drift")
    require(source_is_ancestor(result.get("commitSha")),
            "object result SHA is not an ancestor")
    environment = result.get("environment")
    scenario = result.get("scenario")
    require(isinstance(environment, dict) and
            environment.get("productionEvidence") is False and
            environment.get("containsSecrets") is False,
            "object result evidence boundary drift")
    require(isinstance(scenario, dict) and scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "object result is not PASS")
    require(scenario.get("sourceVersionsCreated") >= 3 and
            scenario.get("sourceVersionsRemainingAfterLoss") == 0,
            "object source-loss simulation failed")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and assertions and
            all(value is True for value in assertions.values()),
            "object result contains a failed assertion")


def normalize(status: dict[str, Any]) -> dict[str, Any]:
    index = load(INDEX_PATH)
    require(index.get("schemaVersion") ==
            "memory-os-backup-local-foundation-evidence.v1",
            "local backup evidence index drift")
    require(index.get("productionEvidence") is False and
            index.get("productionDecision") == "NO_GO",
            "local backup index evidence boundary drift")
    validate_logical(load(LOGICAL_RESULT))
    validate_object(load(OBJECT_RESULT))

    require(status.get("productionDecision") == "NO_GO",
            "backup authority requires productionDecision NO_GO")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") in {
        "NOT_IMPLEMENTED_OR_PROVEN", "PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"
    }, "unexpected OPS-P0-007 status")

    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-007 existingEvidence must be a list")
    require_canonical_gaps(missing, ReconcileFailure)
    if refs is None:
        refs = []
        gate["evidenceRefs"] = refs
    require(isinstance(refs, list), "OPS-P0-007 evidenceRefs must be a list")

    gate["status"] = "PARTIAL_FOUNDATIONS_ONLY"
    append_all(existing, POLICY_EVIDENCE + LOGICAL_EVIDENCE + OBJECT_EVIDENCE)
    for ref in EVIDENCE_REFS:
        require((ROOT / ref).is_file(), f"backup authority evidence path missing: {ref}")
    append_all(refs, EVIDENCE_REFS)

    gate["existingEvidence"] = unique(existing)
    gate["evidenceRefs"] = unique(refs)
    require_canonical_gaps(gate.get("missingEvidence"), ReconcileFailure)
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY",
            "local foundations cannot advance backup readiness beyond partial")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")
    return status


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        temp_path = None
    except OSError as exc:
        raise ReconcileFailure(f"atomic authority write failed: {path.name}") from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


CANONICAL_RUNTIME_AUTHORITY_GUARD = validate_runtime_authority


def main(canonical_runtime_authority_guard=CANONICAL_RUNTIME_AUTHORITY_GUARD) -> int:
    if validate_runtime_authority is not canonical_runtime_authority_guard:
        raise ReconcileFailure("backup authority runtime guard drift")

    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    validate_runtime_authority()
    current = load(STATUS_PATH)
    candidate = normalize(copy.deepcopy(current))
    candidate["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    left = copy.deepcopy(current)
    right = copy.deepcopy(candidate)
    left.pop("asOf", None)
    right.pop("asOf", None)
    changed = left != right

    if args.check:
        require(not changed, "OPS-P0-007 backup authority is not normalized")
        validate_projected_authority()
        print("Memory OS backup authority normalization check PASS")
        return 0
    if not changed:
        validate_projected_authority()
        print("Memory OS backup authority already normalized")
        return 0

    original_bytes = STATUS_PATH.read_bytes()
    payload = (json.dumps(candidate, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    atomic_write_bytes(STATUS_PATH, payload)
    try:
        validate_projected_authority()
    except Exception:
        atomic_write_bytes(STATUS_PATH, original_bytes)
        raise

    print("Normalized OPS-P0-007 local foundations; canonical production blockers unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"BACKUP AUTHORITY NORMALIZATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
