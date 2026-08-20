#!/usr/bin/env python3
"""Register PostgreSQL 16 to 17 logical upgrade evidence conservatively."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/postgresql-major-upgrade-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
MAJOR_UPGRADE_VALIDATOR = ROOT / "scripts/validate-memory-os-postgresql-major-upgrade.py"
VERSION_VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
SHA_RE = __import__("re").compile(r"^[0-9a-f]{40}$")

EXISTING = (
    "exact-source isolated PostgreSQL 16 to PostgreSQL 17 logical forward-upgrade rehearsal using fresh expand-migrated target schema and PostgreSQL 17 dump tooling",
    "cross-major data-only restore preserves active account/session authority while deleted account and session authority remain absent and unresolvable",
    "bounded schema-authority fingerprints match across PostgreSQL 16 and 17, runtime roles remain NOBYPASSRLS, FORCE RLS remains enabled and the complete canonical SQL integration suite passes on PostgreSQL 17",
    "upgrade policy forbids automatic in-place upgrade, down migration, target-to-source downgrade, source deletion and traffic promotion",
)
OBSOLETE = (
    "PostgreSQL minor/major upgrade policy and rehearsal",
)
MISSING = (
    "reviewed PostgreSQL minor-version support window and patch-upgrade rehearsal",
    "production-shaped in-place pg_upgrade or approved blue-green database cutover rehearsal with connection-pool drain and rollback decision evidence",
    "physical replication, WAL continuity, replication-slot and failover verification across the approved PostgreSQL upgrade path",
    "approved rollback boundary for irreversible database-format changes and independent database recovery review",
)
REFS = (
    "contracts/operations/postgresql-major-upgrade-contract.v1.json",
    "scripts/run-memory-os-postgresql-major-upgrade.sh",
    "scripts/validate-memory-os-postgresql-major-upgrade.py",
    "scripts/reconcile-memory-os-postgresql-major-upgrade.py",
    "docs/fixtures/memory-os-operability/postgresql-major-upgrade-results.sample.v1.json",
    ".github/workflows/postgresql-major-upgrade.yml",
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


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_ancestor(base: str, head: str) -> bool:
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, head],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def run_validator(path: Path, *arguments: str) -> None:
    require(path.is_file(), f"canonical validator missing: {path.relative_to(ROOT)}")
    require(not path.is_symlink(), f"canonical validator cannot be a symlink: {path.relative_to(ROOT)}")
    completed = subprocess.run(
        [sys.executable, str(path), *arguments],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"canonical validator rejected authority: {path.relative_to(ROOT)}\n{completed.stdout[-4000:]}")


def validate_authority_chain(commit_sha: str, *, require_reconciled: bool) -> None:
    arguments = ["--expected-commit-sha", commit_sha]
    if require_reconciled:
        arguments.append("--require-reconciled")
    run_validator(MAJOR_UPGRADE_VALIDATOR, *arguments)
    run_validator(VERSION_VALIDATOR)
    run_validator(OPERABILITY_VALIDATOR)


def commit_candidate(contract: dict[str, Any], status: dict[str, Any], commit_sha: str) -> None:
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    try:
        write(CONTRACT_PATH, contract)
        write(STATUS_PATH, status)
        validate_authority_chain(commit_sha, require_reconciled=True)
    except Exception:
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)
        raise


def main() -> int:
    result = load(RESULT_PATH)
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None and
            is_ancestor(commit_sha, "HEAD"),
            "PostgreSQL upgrade result source lineage invalid")

    # The canonical validator owns the full contract/result semantics. Validate
    # the exact source and current aggregate authority before deriving updates.
    validate_authority_chain(commit_sha, require_reconciled=False)

    contract = load(CONTRACT_PATH)
    readiness = contract.get("readiness")
    refs = contract.get("evidenceRefs")
    require(isinstance(readiness, dict), "PostgreSQL upgrade readiness missing")
    require(isinstance(refs, list), "PostgreSQL upgrade evidenceRefs must be a list")
    for field in (
        "inPlaceUpgradeExecuted", "productionFailoverExecuted", "downgradeExecuted",
        "independentReviewCompleted", "productionReady",
    ):
        require(readiness.get(field) is False,
                f"logical upgrade evidence cannot promote {field}")

    contract_changed = False
    for field in ("exactSourcePassResultCommitted", "postgresql17LogicalForwardUpgradeExecuted"):
        if readiness.get(field) is not True:
            readiness[field] = True
            contract_changed = True
    for ref in REFS:
        require((ROOT / ref).is_file(), f"PostgreSQL upgrade evidence missing: {ref}")
        contract_changed = append_once(refs, ref) or contract_changed

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "PostgreSQL upgrade evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "OPS-P0-008 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    status_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-008 missingEvidence must be a list")
    require(isinstance(status_refs, list), "OPS-P0-008 evidenceRefs must be a list")

    status_changed = False
    for item in EXISTING:
        status_changed = append_once(existing, item) or status_changed
    for item in OBSOLETE:
        if item in missing:
            missing.remove(item)
            status_changed = True
    for item in MISSING:
        status_changed = append_once(missing, item) or status_changed
    for ref in REFS:
        status_changed = append_once(status_refs, ref) or status_changed

    lowered = [str(item).lower() for item in missing]
    for label, terms in {
        "minor upgrade": ("minor-version", "patch-upgrade"),
        "production cutover": ("blue-green", "connection-pool", "rollback"),
        "replication": ("physical replication", "wal", "failover"),
        "irreversible boundary": ("irreversible", "independent", "recovery"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered),
                f"required PostgreSQL upgrade gap disappeared: {label}")
    require(gate.get("status") == "PARTIAL" and
            status.get("productionDecision") == "NO_GO",
            "PostgreSQL logical upgrade evidence changed readiness")

    if not contract_changed and not status_changed:
        validate_authority_chain(commit_sha, require_reconciled=True)
        print("PostgreSQL major-upgrade authority already reconciled")
        return 0

    if status_changed:
        status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    commit_candidate(contract, status, commit_sha)
    print("Registered PostgreSQL 16 to 17 logical upgrade; OPS-P0-008 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"POSTGRESQL MAJOR UPGRADE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
