#!/usr/bin/env python3
"""Reconcile committed local migration recovery results missing from the append-only ledger.

This rescue path never executes a migration and never creates production evidence.
It accepts only immutable, already-committed LOCAL_POSTGRES_REHEARSAL result files
created by the canonical local recovery workflow, reconstructs the same non-production
ledger record deterministically, validates it with the canonical writer, and appends it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULT_ROOT = ROOT / "docs/evidence/migrations/recovery"
REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
REGISTRY_CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
LOCAL_CONTRACT = ROOT / "contracts/operations/local-migration-recovery-artifact-contract.v1.json"
WRITER = ROOT / "scripts/register-memory-os-migration-rehearsal-evidence.py"
RESULT_VALIDATOR = ROOT / "scripts/validate-memory-os-local-migration-recovery-artifact.py"
LOCAL_RECONCILER = ROOT / "scripts/reconcile-memory-os-local-migration-recovery-artifact.py"
GLOBAL_RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-evidence-registry.py"
CREATION_SUBJECT = "test(migration): record local recovery artifact rehearsal"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def git_bytes(*args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0, f"git {' '.join(args)} failed: {completed.stderr.decode('utf-8', errors='replace').strip()}")
    return completed.stdout


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_migration_writer_for_orphan_reconcile", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load canonical migration rehearsal writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(Path(module.REGISTRY).resolve() == REGISTRY.resolve(), "migration writer registry authority drift")
    require(Path(module.CONTRACT).resolve() == REGISTRY_CONTRACT.resolve(), "migration writer contract authority drift")
    return module


def parse_utc(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be RFC3339 UTC")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} invalid") from exc
    require(parsed.utcoffset() == dt.timedelta(0), f"{field} must be UTC")
    return parsed


def committed_creation(path: Path) -> tuple[int, str]:
    relative = str(path.relative_to(ROOT))
    require(not path.is_symlink(), f"recovery result cannot be symlink: {relative}")
    require(path.resolve().is_relative_to(RESULT_ROOT.resolve()), f"recovery result escaped evidence root: {relative}")
    git("ls-files", "--error-unmatch", "--", relative)
    current_blob = git_bytes("show", f"HEAD:{relative}")
    require(current_blob == path.read_bytes(), f"recovery result working bytes differ from HEAD: {relative}")
    creations = [line for line in git("log", "--diff-filter=A", "--format=%H", "--", relative).splitlines() if line]
    require(len(creations) == 1, f"recovery result must have exactly one creation commit: {relative}")
    creation = creations[0]
    require(git("show", "-s", "--format=%s", creation) == CREATION_SUBJECT,
            f"recovery result was not created by canonical workflow: {relative}")
    created_at = int(git("show", "-s", "--format=%ct", creation))
    return created_at, creation


def validate_result(path: Path, value: dict[str, Any]) -> tuple[int, str]:
    run_id = value.get("migrationRunId")
    require(isinstance(run_id, str) and path.name == f"{run_id}.json", "recovery result run ID/path mismatch")
    require(value.get("schemaVersion") == "memory-os-local-migration-recovery-artifact.v1", "recovery result schema drift")
    require(value.get("environmentClass") == "LOCAL_POSTGRES_REHEARSAL", "orphan rescue accepts local rehearsal results only")
    require(value.get("result") == "PASS" and value.get("integrityResult") == "PASS", "orphan rescue accepts passing results only")
    assertions = value.get("assertions")
    require(isinstance(assertions, dict), "recovery result assertions missing")
    for field in ("containsSecrets", "productionTraffic", "productionCredentials", "productionEvidence"):
        require(assertions.get(field) is False, f"orphan rescue forbids {field}")
    source = value.get("commitSha")
    require(isinstance(source, str) and len(source) == 40, "recovery result commitSha invalid")
    completed = subprocess.run(
        [
            "python", str(RESULT_VALIDATOR), "--path", str(path),
            "--expected-commit-sha", source, "--require-result",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(completed.returncode == 0, f"canonical local result validation failed for {run_id}: {completed.stdout.strip()}")
    return committed_creation(path)


def build_record(result_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    lifecycle = load(LIFECYCLE)
    local_contract = load(LOCAL_CONTRACT)
    canonical = lifecycle.get("migrationSequence")
    budgets = local_contract.get("operatorBudgets")
    require(isinstance(canonical, list) and canonical and all(isinstance(item, str) for item in canonical), "canonical migration sequence missing")
    require(isinstance(budgets, dict), "local migration operator budgets missing")
    completed = parse_utc(result.get("completedAt"), "completedAt")
    deadline = completed.date() + dt.timedelta(days=30)
    artifact = result.get("recoveryArtifact")
    require(isinstance(artifact, dict), "recovery result artifact missing")
    return {
        "schemaVersion": "memory-os-migration-rehearsal-evidence.v1",
        "migrationRunId": result["migrationRunId"],
        "environmentClass": "LOCAL_POSTGRES_REHEARSAL",
        "environmentGenerationId": None,
        "databaseIdentityDigest": result["databaseIdentityDigest"],
        "sourceCommitSha": result["commitSha"],
        "migrationSequenceBefore": canonical[:-1],
        "migrationSequenceAfter": canonical,
        "startedAt": result["startedAt"],
        "completedAt": result["completedAt"],
        "operatorRef": "opr_ci_recovery_operator",
        "reviewerRef": "rev_ci_recovery_reviewer",
        "recoveryPointReference": artifact["reference"],
        "recoveryPointArtifactDigest": artifact["sha256"],
        "recoveryPointVerified": True,
        "restoreCapabilityEvidenceRef": "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
        "restoreCapabilityVerified": True,
        "recoveryPointRestoreEvidenceRef": str(result_path.relative_to(ROOT)),
        "lockBudgetMs": int(budgets["lockBudgetMs"]),
        "statementBudgetMs": int(budgets["statementBudgetMs"]),
        "observedLockWaitMs": int(budgets["isolatedCleanDatabaseExpectedLockWaitMs"]),
        "observedRuntimeMs": int(result["migrationApplyDurationMs"]),
        "preflightResult": "PASS",
        "applyResult": "PASS",
        "verificationResult": "PASS",
        "recoveryDecision": "NO_RECOVERY_REQUIRED",
        "openRisks": [{
            "riskId": "risk_local_same_cluster_only",
            "ownerRef": "opr_ci_recovery_owner",
            "deadline": deadline.isoformat(),
            "status": "OPEN",
        }],
        "containsSecrets": False,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
    }


def find_orphans(registry: dict[str, Any]) -> list[tuple[int, Path, dict[str, Any]]]:
    records = registry.get("records")
    require(isinstance(records, list), "migration evidence registry records missing")
    registered = {
        row.get("migrationRunId") for row in records
        if isinstance(row, dict) and isinstance(row.get("migrationRunId"), str)
    }
    orphans: list[tuple[int, Path, dict[str, Any]]] = []
    for path in sorted(RESULT_ROOT.glob("mig_*.json")):
        value = load(path)
        run_id = value.get("migrationRunId")
        if run_id in registered:
            continue
        created_at, _ = validate_result(path, value)
        orphans.append((created_at, path, value))
    orphans.sort(key=lambda item: (item[0], item[1].name))
    return orphans


def reconcile(orphans: list[tuple[int, Path, dict[str, Any]]], writer: ModuleType) -> None:
    require(git("status", "--porcelain") == "", "working tree must be clean before orphan reconciliation")
    registry = load(REGISTRY)
    contract = load(REGISTRY_CONTRACT)
    writer.validate_registry_for_append(registry, contract)
    required = contract.get("requiredRecordFields")
    require(isinstance(required, list) and all(isinstance(item, str) for item in required), "requiredRecordFields invalid")
    records = registry["records"]
    existing_ids = {row.get("migrationRunId") for row in records if isinstance(row, dict)}
    new_run_ids: list[str] = []
    for _, path, result in orphans:
        run_id = result["migrationRunId"]
        if run_id in existing_ids:
            continue
        record = build_record(path, result)
        writer.validate_record(record, set(required), contract)
        records.append(record)
        existing_ids.add(run_id)
        new_run_ids.append(run_id)
    require(new_run_ids, "no migration recovery result orphans require reconciliation")
    registry["rehearsalEvidenceCount"] = len(records)
    registry["passingRehearsalCount"] = sum(
        1 for item in records
        if item.get("preflightResult") == "PASS" and item.get("applyResult") == "PASS" and item.get("verificationResult") == "PASS"
    )
    registry["productionEquivalentRehearsalCount"] = sum(
        1 for item in records if item.get("environmentClass") == "PRODUCTION_EQUIVALENT_REHEARSAL"
    )
    registry["latestRehearsalRunId"] = records[-1].get("migrationRunId") if records else None
    writer.validate_registry_for_append(registry, contract)

    originals = {
        REGISTRY: REGISTRY.read_bytes(),
        REGISTRY_CONTRACT: REGISTRY_CONTRACT.read_bytes(),
        LIFECYCLE: LIFECYCLE.read_bytes(),
        LOCAL_CONTRACT: LOCAL_CONTRACT.read_bytes(),
        STATUS: STATUS.read_bytes(),
    }
    previous_registry = json.loads(originals[REGISTRY].decode("utf-8"))
    lock_fd = writer.acquire_lock()
    try:
        writer.write_registry_transactionally(registry, previous_registry, contract)
        completed = subprocess.run(
            ["python", str(GLOBAL_RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode == 0, f"migration ledger authority reconcile failed: {completed.stdout.strip()}")
        for run_id in new_run_ids:
            completed = subprocess.run(
                ["python", str(LOCAL_RECONCILER), "--run-id", run_id],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            require(completed.returncode == 0, f"local recovery authority reconcile failed for {run_id}: {completed.stdout.strip()}")
    except BaseException:
        for path, payload in originals.items():
            path.write_bytes(payload)
        raise
    finally:
        os.close(lock_fd)
        try:
            writer.LOCK.unlink()
        except FileNotFoundError:
            pass

    print("Reconciled committed local migration recovery result orphans:")
    for run_id in new_run_ids:
        print(f"- {run_id}")
    print("productionEvidence: false")
    print("productionReady: false")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    writer = load_writer()
    registry = load(REGISTRY)
    contract = load(REGISTRY_CONTRACT)
    writer.validate_registry_for_append(registry, contract)
    orphans = find_orphans(registry)
    if not orphans:
        print("Migration recovery result/registry consistency PASS: no committed local result orphans")
        return 0
    ids = [value["migrationRunId"] for _, _, value in orphans]
    if args.check_only:
        raise Fail(f"committed local recovery results missing from append-only registry: {ids}")
    reconcile(orphans, writer)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"MIGRATION RECOVERY RESULT ORPHAN RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
