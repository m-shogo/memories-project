#!/usr/bin/env python3
"""Append one approved rollback rehearsal request under an exclusive lock.

This tool records admission to an isolated rehearsal only. It never executes a
rollback, changes traffic, edits a release record or creates production proof.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_CONTRACT_PATH = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
RELEASE_WRITER_PATH = ROOT / "scripts/register-memory-os-release-baseline.py"
REHEARSAL_REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
LOCK_PATH = ROOT / "contracts/operations/.rollback-rehearsal-registry.lock"
CONFIRMATION = "REQUEST ISOLATED ROLLBACK REHEARSAL"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REHEARSAL_ID_RE = re.compile(r"^rrh_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")
APPROVER_RE = re.compile(r"^apr_[a-z0-9][a-z0-9_-]{7,63}$")
REQUIRED_ROLES = {"RELEASE_OWNER", "DATABASE_RECOVERY_OWNER"}
REGISTRY_FIELDS = {
    "schemaVersion",
    "registryClass",
    "appendOnly",
    "planningAuthorityOnly",
    "productionEvidence",
    "rehearsalRequestCount",
    "latestRehearsalId",
    "requests",
    "limitations",
}


class RequestFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RequestFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RequestFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RequestFailure(f"invalid JSON: {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load authority module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0,
            f"git {' '.join(arguments)} failed without admission")
    return completed.stdout.strip()


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def parse_utc(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"),
            f"{field} must be RFC3339 UTC ending in Z")
    try:
        parsed = dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RequestFailure(f"{field} must be valid RFC3339 UTC") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0),
            f"{field} must be UTC")
    return parsed


def safe_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value.strip(), f"{field} is required")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts,
            f"{field} contains an unsafe path")
    candidate = ROOT / path
    current = ROOT
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), f"{field} contains a symlink path")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(ROOT.resolve())
    except (FileNotFoundError, ValueError) as exc:
        raise RequestFailure(f"{field} escapes or is missing from the repository: {value}") from exc
    require(resolved.is_file(), f"{field} does not reference a regular file: {value}")
    require(bool(git("ls-files", "--error-unmatch", "--", value)),
            f"{field} is not tracked by the repository: {value}")
    return value


def validate_release_registry_for_append(release_registry: dict[str, Any]) -> None:
    release_contract = load(RELEASE_CONTRACT_PATH)
    try:
        release_writer = load_module(RELEASE_WRITER_PATH, "memory_os_release_baseline_writer")
        release_writer.validate_registry_for_append(release_registry, release_contract)
    except Exception as exc:
        raise RequestFailure(f"approved release registry authority invalid: {exc}") from exc


def validate_request(request: dict[str, Any], required_fields: set[str],
                     release_registry: dict[str, Any]) -> None:
    require(set(request) >= required_fields,
            f"request missing fields: {sorted(required_fields - set(request))}")
    require(request.get("schemaVersion") == "memory-os-rollback-rehearsal-request.v1",
            "request schemaVersion drift")
    rehearsal_id = request.get("rehearsalId")
    require(isinstance(rehearsal_id, str) and
            REHEARSAL_ID_RE.fullmatch(rehearsal_id) is not None,
            "rehearsalId format invalid")
    parse_utc(request.get("requestedAt"), "requestedAt")

    releases = release_registry.get("releases")
    require(isinstance(releases, list), "approved release registry is invalid")
    by_id = {
        item.get("releaseId"): item
        for item in releases
        if isinstance(item, dict) and isinstance(item.get("releaseId"), str)
    }
    source_id = request.get("sourceReleaseId")
    target_id = request.get("rollbackTargetReleaseId")
    require(isinstance(source_id, str) and isinstance(target_id, str) and
            source_id != target_id,
            "source and rollback target release IDs must be distinct")
    require(source_id in by_id, "source release is not approved")
    require(target_id in by_id, "rollback target release is not approved")
    source = by_id[source_id]
    target = by_id[target_id]

    for request_field, release_field, release in (
        ("sourceCommitSha", "commitSha", source),
        ("sourceReleaseTag", "releaseTag", source),
        ("rollbackTargetCommitSha", "commitSha", target),
        ("rollbackTargetReleaseTag", "releaseTag", target),
    ):
        require(request.get(request_field) == release.get(release_field),
                f"{request_field} differs from approved release authority")
    require(SHA_RE.fullmatch(str(request.get("sourceCommitSha", ""))) is not None and
            SHA_RE.fullmatch(str(request.get("rollbackTargetCommitSha", ""))) is not None,
            "release SHA binding invalid")

    rollback = target.get("rollbackEligibility")
    require(isinstance(rollback, dict), "rollback target eligibility missing")
    require(rollback.get("status") in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"} and
            rollback.get("verified") is True,
            "rollback target is not verified rollback eligible")
    target_conditions = rollback.get("conditions")
    require(isinstance(target_conditions, list) and
            all(isinstance(item, str) and item for item in target_conditions),
            "rollback target conditions are invalid")

    require(request.get("environmentClass") == "ISOLATED_NON_PRODUCTION_REHEARSAL",
            "environmentClass must be isolated non-production rehearsal")
    traffic = request.get("trafficPolicy")
    require(isinstance(traffic, dict) and
            traffic.get("productionTrafficAllowed") is False and
            traffic.get("productionCredentialsAllowed") is False and
            traffic.get("automaticPromotionAllowed") is False and
            traffic.get("syntheticOrApprovedSanitizedDataOnly") is True,
            "traffic policy violates rehearsal boundary")
    database = request.get("databasePolicy")
    require(isinstance(database, dict) and
            database.get("destructiveDownMigrationAllowed") is False and
            database.get("automaticRecoveryDecisionAllowed") is False,
            "database policy violates rehearsal boundary")
    safe_ref(database.get("recoveryPointEvidenceRef"),
             "databasePolicy.recoveryPointEvidenceRef")
    safe_ref(database.get("forwardFixDecisionRef"),
             "databasePolicy.forwardFixDecisionRef")

    artifacts = request.get("artifactPolicy")
    require(isinstance(artifacts, dict), "artifactPolicy missing")
    for field in ("parserArtifactEvidenceRef", "objectVersionEvidenceRef"):
        safe_ref(artifacts.get(field), f"artifactPolicy.{field}")
    require(artifacts.get("exactRetainedArtifactsRequired") is True,
            "exact retained artifacts must be required")

    for ref in strings(request.get("entryCriteriaRefs"), "entryCriteriaRefs", 5):
        safe_ref(ref, "entryCriteriaRefs")
    stop_conditions = strings(request.get("stopConditions"), "stopConditions", 6)
    for condition in target_conditions:
        require(condition in stop_conditions,
                "rollback target condition is missing from stopConditions")

    approvers = request.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 2,
            "exactly two rehearsal approvers are required")
    roles: set[str] = set()
    identities: set[str] = set()
    for approver in approvers:
        require(isinstance(approver, dict), "approver entry must be an object")
        role = approver.get("role")
        identity = approver.get("approverRef")
        require(role in REQUIRED_ROLES and role not in roles,
                f"approval role invalid or duplicated: {role}")
        require(isinstance(identity, str) and APPROVER_RE.fullmatch(identity) is not None,
                "approverRef must be an operational pseudonym")
        require(identity not in identities, "duplicate rehearsal approver detected")
        roles.add(role)
        identities.add(identity)
    require(roles == REQUIRED_ROLES, "required rehearsal approval roles incomplete")

    risks = request.get("openRisks")
    require(isinstance(risks, list), "openRisks must be a list")
    for risk in risks:
        require(isinstance(risk, dict) and risk.get("riskId") and
                risk.get("ownerRef") and risk.get("deadline") and risk.get("status"),
                "open risk entry is incomplete")

    serialized = json.dumps(request, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "authorization: bearer",
        "minioadmin", "secretaccesskey", "account_id", "session_id", "job_id",
        "preview_id", "object_key", "apple_subject", "@",
    ):
        require(forbidden not in serialized,
                f"request contains forbidden content: {forbidden}")


def validate_registry_for_append(
    registry: dict[str, Any], contract: dict[str, Any], release_registry: dict[str, Any]
) -> None:
    validate_release_registry_for_append(release_registry)
    require(set(registry) == REGISTRY_FIELDS,
            "rollback rehearsal registry field set drift")
    require(registry.get("schemaVersion") == "memory-os-rollback-rehearsal-registry.v1",
            "rollback rehearsal registry schemaVersion drift")
    require(registry.get("registryClass") == "APPROVED_ROLLBACK_REHEARSAL_REQUESTS",
            "rollback rehearsal registry class drift")
    require(registry.get("appendOnly") is True,
            "rollback rehearsal registry must remain append-only")
    require(registry.get("planningAuthorityOnly") is True,
            "rollback rehearsal registry must remain planning authority only")
    require(registry.get("productionEvidence") is False,
            "rollback rehearsal registry cannot claim production evidence")
    limitations = registry.get("limitations")
    require(isinstance(limitations, list) and
            all(isinstance(item, str) and item for item in limitations),
            "rollback rehearsal registry limitations invalid")
    requests = registry.get("requests")
    require(isinstance(requests, list) and all(isinstance(item, dict) for item in requests),
            "rollback rehearsal registry contains invalid requests")
    count = registry.get("rehearsalRequestCount")
    require(isinstance(count, int) and not isinstance(count, bool),
            "rehearsalRequestCount must be an integer")
    require(count == len(requests), "rehearsalRequestCount drift")
    required_fields = set(strings(contract.get("requiredRequestFields"),
                                  "requiredRequestFields", 17))
    ids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for record in requests:
        validate_request(record, required_fields, release_registry)
        rehearsal_id = record["rehearsalId"]
        pair = (record["sourceReleaseId"], record["rollbackTargetReleaseId"])
        require(rehearsal_id not in ids, "duplicate rehearsalId")
        require(pair not in pairs, "duplicate admitted release pair")
        ids.add(rehearsal_id)
        pairs.add(pair)
    expected_latest = requests[-1]["rehearsalId"] if requests else None
    require(registry.get("latestRehearsalId") == expected_latest,
            "latestRehearsalId drift")


def acquire_lock() -> int:
    try:
        return os.open(LOCK_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RequestFailure("rollback rehearsal registry lock already exists") from exc


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=".rollback-rehearsal-registry.", suffix=".tmp",
        dir=REHEARSAL_REGISTRY_PATH.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REHEARSAL_REGISTRY_PATH)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True,
                        help="JSON request outside the repository working tree")
    parser.add_argument("--confirm", required=True)
    arguments = parser.parse_args()

    require(arguments.confirm == CONFIRMATION,
            f"confirmation must equal: {CONFIRMATION}")
    request_path = Path(arguments.request).resolve()
    try:
        request_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise RequestFailure("input request must be outside the repository")
    require(git("status", "--porcelain") == "",
            "working tree must be clean before rehearsal admission")

    contract = load(CONTRACT_PATH)
    required_fields = set(strings(contract.get("requiredRequestFields"),
                                  "requiredRequestFields", 17))
    release_registry = load(RELEASE_REGISTRY_PATH)
    validate_release_registry_for_append(release_registry)
    request = load(request_path)
    validate_request(request, required_fields, release_registry)

    lock_fd = acquire_lock()
    try:
        os.write(lock_fd, f"{request['rehearsalId']}\n".encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REHEARSAL_REGISTRY_PATH)
        validate_registry_for_append(registry, contract, release_registry)
        requests = registry["requests"]
        require(all(item.get("rehearsalId") != request["rehearsalId"]
                    for item in requests),
                "rehearsalId is already registered")
        require(all(not (
            item.get("sourceReleaseId") == request["sourceReleaseId"] and
            item.get("rollbackTargetReleaseId") == request["rollbackTargetReleaseId"]
        ) for item in requests),
                "release pair already has an admitted rehearsal request")

        requests.append(request)
        registry["rehearsalRequestCount"] = len(requests)
        registry["latestRehearsalId"] = request["rehearsalId"]
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass

    print(f"Admitted isolated rollback rehearsal request: {request['rehearsalId']}")
    print("No rollback or traffic action was executed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RequestFailure as exc:
        print(f"ROLLBACK REHEARSAL REQUEST FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)