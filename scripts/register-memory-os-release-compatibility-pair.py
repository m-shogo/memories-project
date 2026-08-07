#!/usr/bin/env python3
"""Append one reviewed approved-release compatibility pair."""

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
CONTRACT = ROOT / "contracts/operations/release-compatibility-pair-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REGISTRY = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
LOCK = ROOT / "contracts/operations/.release-compatibility-pair.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
PAIR_ID = re.compile(r"^rcp_[a-z0-9][a-z0-9_-]{7,63}$")


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


def evidence_refs(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum, f"{field} requires at least {minimum} reference(s)")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for ref in value:
        require(isinstance(ref, str) and ref and not Path(ref).is_absolute() and ".." not in Path(ref).parts, f"{field} invalid reference")
        require((ROOT / ref).is_file(), f"{field} evidence missing: {ref}")
    return value


def approved_release(releases: list[Any], release_id: Any, field: str) -> dict[str, Any]:
    require(isinstance(release_id, str) and release_id, f"{field} required")
    matches = [row for row in releases if isinstance(row, dict) and row.get("releaseId") == release_id]
    require(len(matches) == 1, f"{field} is not uniquely approved")
    record = matches[0]
    require(record.get("approvalClass") == "PRODUCTION_RELEASE_BASELINE", f"{field} approval class drift")
    require(record.get("evidenceComplete") is True and record.get("productionReady") is True, f"{field} is not a complete approved release baseline")
    return record


def validate_record(record: dict[str, Any]) -> None:
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"pair record field drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "pair schemaVersion drift")
    pair_id = record.get("pairId")
    require(isinstance(pair_id, str) and PAIR_ID.fullmatch(pair_id), "pairId invalid")

    release_registry = load(RELEASES)
    releases = release_registry.get("releases")
    require(isinstance(releases, list), "approved release registry invalid")
    predecessor = approved_release(releases, record.get("predecessorReleaseId"), "predecessorReleaseId")
    successor = approved_release(releases, record.get("successorReleaseId"), "successorReleaseId")
    require(predecessor.get("releaseId") != successor.get("releaseId"), "predecessor and successor must be distinct releases")
    for field, release in (("predecessorCommitSha", predecessor), ("successorCommitSha", successor)):
        sha = record.get(field)
        require(isinstance(sha, str) and SHA40.fullmatch(sha), f"{field} invalid")
        require(sha == release.get("commitSha"), f"{field} does not match approved release registry")
        require(git("cat-file", "-e", sha + "^{commit}") == "", f"{field} commit absent from repository history")
    require(predecessor.get("rollbackEligibility") == "ELIGIBLE", "predecessor must be rollback ELIGIBLE")

    evidence_refs(record.get("rollingDeploymentEvidenceRefs"), "rollingDeploymentEvidenceRefs")
    evidence_refs(record.get("applicationRollbackEvidenceRefs"), "applicationRollbackEvidenceRefs")
    evidence_refs(record.get("persistedRouteEvidenceRefs"), "persistedRouteEvidenceRefs")
    evidence_refs(record.get("databaseUpgradeEvidenceRefs"), "databaseUpgradeEvidenceRefs")
    evidence_refs(record.get("artifactRetentionEvidenceRefs"), "artifactRetentionEvidenceRefs")
    reviews = evidence_refs(record.get("independentReviewRefs"), "independentReviewRefs", minimum=2)
    require(len(set(reviews)) >= 2, "independentReviewRefs must contain at least two distinct references")

    approved_at = record.get("approvedAt")
    require(isinstance(approved_at, str), "approvedAt required")
    try:
        datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Fail("approvedAt must be ISO-8601 date-time") from exc

    findings = record.get("openFindings")
    require(isinstance(findings, list), "openFindings must be list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"openFindings[{index}] field drift")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "CRITICAL/HIGH findings forbid pair admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"openFindings[{index}] status invalid")
    require(record.get("pairEvidenceComplete") is True, "pairEvidenceComplete must be true for admission")
    require(record.get("productionEvidence") is False and record.get("productionReady") is False, "pair admission cannot promote production")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "http://", "https://", "postgres://", "postgresql://", "authorization: bearer", "password",
        "private_key", "access_key", "secret", "raw_ip", "account_id", "session_id", "@", "latest", "candidate_only_local_ci",
    ):
        require(forbidden not in serialized, f"pair record contains forbidden material: {forbidden}")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".release-pair.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
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
    parser.add_argument("--record", required=True)
    args = parser.parse_args()
    input_path = Path(args.record).resolve()
    try:
        input_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input pair record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(input_path)
    validate_record(record)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("release compatibility pair registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["pairId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        require(registry.get("appendOnly") is True, "pair registry must remain append-only")
        pairs = registry.get("pairs")
        require(isinstance(pairs, list) and all(isinstance(row, dict) for row in pairs), "pair registry invalid")
        require(all(row.get("pairId") != record["pairId"] for row in pairs), "pairId already registered")
        require(all(not (row.get("predecessorReleaseId") == record["predecessorReleaseId"] and row.get("successorReleaseId") == record["successorReleaseId"]) for row in pairs), "release pair already registered")
        pairs.append(record)
        registry["approvedPairCount"] = len(pairs)
        registry["rollbackEligiblePairCount"] = len(pairs)
        registry["latestPairId"] = record["pairId"]
        registry["productionEvidence"] = False
        registry["productionReady"] = False
        registry["limitations"] = [
            "approved release pairs are compatibility admission evidence, not application production readiness",
            "pair-specific rolling/rollback/persisted-route/database/artifact evidence must remain available",
            "candidate/local mixed-version evidence cannot substitute approved release baselines"
        ]
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered approved release compatibility pair: {record['pairId']}")
    print("Production evidence: false")
    print("Production readiness: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
