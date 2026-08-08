#!/usr/bin/env python3
"""Append one reviewed production-equivalent backup/restore drill planning request."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-request-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES_REGISTRY = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
LOCK = ROOT / "contracts/operations/.backup-restore-drill-request.lock"
REQUEST_ID = re.compile(r"^brrq_[a-z0-9][a-z0-9_-]{7,63}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def repo_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value and not Path(value).is_absolute(), f"{field} invalid")
    path = Path(value)
    require(".." not in path.parts and (ROOT / path).is_file(), f"{field} path missing")
    return value


def parse_timestamp(value: Any) -> None:
    require(isinstance(value, str) and value.endswith("Z"), "requestedAt must be UTC RFC3339 ending in Z")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise Fail("requestedAt invalid") from exc


def generations() -> list[dict[str, Any]]:
    registry = load(GEN_REGISTRY)
    require(registry.get("appendOnly") is True and registry.get("productionEvidence") is False, "environment generation registry boundary drift")
    rows = registry.get("generations")
    count = registry.get("registeredGenerationCount")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "environment generation registry invalid")
    require(isinstance(count, int) and count == len(rows), "environment generation registry count drift")
    return rows


def generation_by_id(rows: list[dict[str, Any]], generation_id: Any, field: str) -> dict[str, Any]:
    require(isinstance(generation_id, str) and generation_id, f"{field} required")
    matches = [row for row in rows if row.get("generationId") == generation_id]
    require(len(matches) == 1, f"{field} is not a unique registered generation")
    return matches[0]


def generation_is_unsuperseded(rows: list[dict[str, Any]], generation_id: str) -> bool:
    return not any(row.get("supersedesGenerationId") == generation_id for row in rows)


def objective_registry() -> tuple[list[dict[str, Any]], str | None]:
    registry = load(OBJECTIVES_REGISTRY)
    require(registry.get("appendOnly") is True and registry.get("productionEvidence") is False and registry.get("productionReady") is False, "recovery objective registry boundary drift")
    rows = registry.get("records")
    count = registry.get("approvedObjectiveCount")
    current = registry.get("currentObjectiveId")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "recovery objective registry invalid")
    require(isinstance(count, int) and count == len(rows), "recovery objective registry count drift")
    if count == 0:
        require(current is None, "empty recovery objective registry cannot have currentObjectiveId")
    else:
        require(isinstance(current, str) and sum(1 for row in rows if row.get("objectiveId") == current) == 1, "current recovery objective is not uniquely registered")
    return rows, current


def objective_by_id(rows: list[dict[str, Any]], objective_id: Any) -> dict[str, Any]:
    require(isinstance(objective_id, str) and objective_id, "recoveryObjectivesId required")
    matches = [row for row in rows if row.get("objectiveId") == objective_id]
    require(len(matches) == 1, "recoveryObjectivesId is not uniquely registered")
    return matches[0]


def validate_request(record: dict[str, Any], *, require_current: bool = True) -> None:
    """Validate an admitted request.

    `require_current=True` is the registration/execution-time gate. Historical
    append-only rows use `False`: immutable generation/objective references must
    still exist and match, but later supersession or objective replacement must
    not invalidate the historical admission record itself.
    """
    contract = load(CONTRACT)
    required = set(contract.get("requiredRequestFields", []))
    require(required and set(record) == required, f"request field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "request schemaVersion drift")
    request_id = record.get("requestId")
    require(isinstance(request_id, str) and REQUEST_ID.fullmatch(request_id), "requestId invalid")
    parse_timestamp(record.get("requestedAt"))

    rows = generations()
    source = generation_by_id(rows, record.get("sourceEnvironmentGenerationId"), "sourceEnvironmentGenerationId")
    target = generation_by_id(rows, record.get("restoreTargetEnvironmentGenerationId"), "restoreTargetEnvironmentGenerationId")
    require(source.get("generationId") != target.get("generationId"), "source and restore-target generation IDs must differ")
    require(source.get("environmentId") != target.get("environmentId"), "source and restore-target environment IDs must differ")
    if require_current:
        require(generation_is_unsuperseded(rows, source["generationId"]), "source generation has been superseded")
        require(generation_is_unsuperseded(rows, target["generationId"]), "restore-target generation has been superseded")
    for value, field in (
        (record.get("sourceEnvironmentManifestSha256"), "sourceEnvironmentManifestSha256"),
        (record.get("restoreTargetManifestSha256"), "restoreTargetManifestSha256"),
    ):
        require(isinstance(value, str) and DIGEST.fullmatch(value), f"{field} invalid")
    require(record["sourceEnvironmentManifestSha256"] == source.get("environmentManifestSha256"), "source environment manifest digest mismatch")
    require(record["restoreTargetManifestSha256"] == target.get("environmentManifestSha256"), "restore-target environment manifest digest mismatch")

    objective_rows, current_objective_id = objective_registry()
    objective_by_id(objective_rows, record.get("recoveryObjectivesId"))
    if require_current:
        require(record.get("recoveryObjectivesId") == current_objective_id, "request must bind current approved recovery objective")

    isolation = record.get("isolationPolicy")
    require(isinstance(isolation, dict) and set(isolation) == {"environmentClass", "networkIsolated", "productionRoutingForbidden", "syntheticOrApprovedSanitizedDataOnly"}, "isolationPolicy field drift")
    require(isolation.get("environmentClass") == "PRODUCTION_EQUIVALENT_ISOLATED_RESTORE_DRILL", "isolation environment class drift")
    require(isolation.get("networkIsolated") is True, "restore drill must be network isolated")
    require(isolation.get("productionRoutingForbidden") is True, "production routing must be forbidden")
    require(isolation.get("syntheticOrApprovedSanitizedDataOnly") is True, "restore drill data policy drift")

    database = record.get("databasePolicy")
    require(isinstance(database, dict) and set(database) == {"pitrRequired", "walContinuityRequired", "restoreIntoSeparateDatabaseRequired", "destructiveDownMigrationAllowed"}, "databasePolicy field drift")
    require(database.get("pitrRequired") is True and database.get("walContinuityRequired") is True, "PITR and WAL continuity are required")
    require(database.get("restoreIntoSeparateDatabaseRequired") is True, "isolated restore database required")
    require(database.get("destructiveDownMigrationAllowed") is False, "destructive down migration forbidden")

    object_policy = record.get("objectPolicy")
    require(isinstance(object_policy, dict) and set(object_policy) == {"independentRetentionRequired", "exactVersionRestoreRequired", "tlsRequired", "restoreOnlyCredentialsRequired", "deletionProtectionRequired", "immutabilityRequired"}, "objectPolicy field drift")
    for field in ("independentRetentionRequired", "exactVersionRestoreRequired", "tlsRequired", "restoreOnlyCredentialsRequired", "deletionProtectionRequired", "immutabilityRequired"):
        require(object_policy.get(field) is True, f"objectPolicy.{field} must be true")

    domains = record.get("requiredEvidenceDomains")
    required_domains = contract.get("requiredEvidenceDomains")
    require(isinstance(domains, list) and isinstance(required_domains, list), "requiredEvidenceDomains invalid")
    require(len(domains) == len(set(domains)) and set(domains) == set(required_domains), "requiredEvidenceDomains coverage drift")

    entry_refs = record.get("entryCriteriaRefs")
    require(isinstance(entry_refs, list) and len(entry_refs) >= 3 and len(entry_refs) == len(set(entry_refs)), "entryCriteriaRefs must contain at least three distinct refs")
    for index, ref in enumerate(entry_refs):
        repo_ref(ref, f"entryCriteriaRefs[{index}]")

    approvals = record.get("approvalRefs")
    require(isinstance(approvals, dict) and set(approvals) == {"recoveryOwner", "securityReview", "operabilityReview"}, "approvalRefs field drift")
    approval_values = [repo_ref(approvals[key], f"approvalRefs.{key}") for key in ("recoveryOwner", "securityReview", "operabilityReview")]
    require(len(set(approval_values)) == 3, "recovery owner, security and operability approvals must be distinct")

    stops = record.get("stopConditions")
    required_stops = contract.get("requiredStopConditions")
    require(isinstance(stops, list) and isinstance(required_stops, list), "stopConditions invalid")
    require(len(stops) == len(set(stops)) and set(required_stops).issubset(set(stops)), "required stop conditions missing")

    risks = record.get("openRisks")
    require(isinstance(risks, list), "openRisks must be list")
    risk_ids: set[str] = set()
    for index, risk in enumerate(risks):
        require(isinstance(risk, dict) and set(risk) == {"riskId", "severity", "status", "ownerRef"}, f"openRisks[{index}] field drift")
        risk_id = risk.get("riskId")
        require(isinstance(risk_id, str) and risk_id and risk_id not in risk_ids, f"openRisks[{index}].riskId invalid/duplicate")
        risk_ids.add(risk_id)
        require(risk.get("severity") in {"LOW", "MEDIUM"}, "HIGH/CRITICAL open risk blocks drill request admission")
        require(risk.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"openRisks[{index}].status invalid")
        repo_ref(risk.get("ownerRef"), f"openRisks[{index}].ownerRef")

    for field in ("productionTraffic", "productionCredentials", "automaticPromotion", "productionEvidence", "productionReady"):
        require(record.get(field) is False, f"{field} must remain false")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("http://", "https://", "postgres://", "postgresql://", "authorization: bearer", "password", "private_key", "access_key", "raw_ip", "account_id", "session_id", "@", "latest"):
        require(forbidden not in serialized, f"request contains forbidden material: {forbidden}")


def request_currently_executable(record: dict[str, Any]) -> bool:
    try:
        validate_request(record, require_current=True)
    except Fail:
        return False
    return True


def atomic_write(value: dict[str, Any]) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=".backup-restore-drill-request.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    args = parser.parse_args()
    input_path = Path(args.request).resolve()
    try:
        input_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("drill request input must be external to repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(input_path)
    validate_request(record, require_current=True)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("backup/restore drill request registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["requestId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        require(registry.get("appendOnly") is True, "request registry must remain append-only")
        requests = registry.get("requests")
        require(isinstance(requests, list) and all(isinstance(row, dict) for row in requests), "request registry records invalid")
        require(all(row.get("requestId") != record["requestId"] for row in requests), "requestId already registered")
        request_tuple = (
            record["sourceEnvironmentGenerationId"],
            record["restoreTargetEnvironmentGenerationId"],
            record["recoveryObjectivesId"],
        )
        for row in requests:
            existing_tuple = (
                row.get("sourceEnvironmentGenerationId"),
                row.get("restoreTargetEnvironmentGenerationId"),
                row.get("recoveryObjectivesId"),
            )
            require(existing_tuple != request_tuple, "source/target/objective tuple already has an admitted drill request")
        requests.append(record)
        registry["registeredRequestCount"] = len(requests)
        registry["currentExecutableRequestCount"] = sum(1 for row in requests if request_currently_executable(row))
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered production-equivalent backup/restore drill request: {record['requestId']}")
    print("planning authority only: true")
    print("execution-time revalidation required: true")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL REQUEST FAILED: {exc}")
        raise SystemExit(1)
