#!/usr/bin/env python3
"""Register one approved release baseline under an exclusive repository lock.

The input record must live outside the repository so the working tree can be
proven clean. This tool does not create approvals, tags, evidence or digests; it
only verifies them and performs one bounded atomic registry update. Git review
and the registry validator remain mandatory after execution.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
CANONICAL_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
CANONICAL_LOCK_PATH = ROOT / "contracts/operations/.release-baseline-registry.lock"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
REGISTRY_PATH = CANONICAL_REGISTRY_PATH
LOCK_PATH = CANONICAL_LOCK_PATH
CONFIRMATION = "REGISTER APPROVED RELEASE BASELINE"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
RELEASE_ID_RE = re.compile(r"^rel_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")
TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
APPROVER_RE = re.compile(r"^apr_[a-z0-9][a-z0-9_-]{7,63}$")
REQUIRED_ROLES = {"SECURITY_REVIEWER", "OPERABILITY_REVIEWER", "RELEASE_OWNER"}
ROLLBACK_VALUES = {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE", "NOT_ELIGIBLE"}
RECORD_FIELDS = {
    "schemaVersion", "releaseId", "releaseTag", "commitSha", "approvedAt",
    "approvalClass", "approvers", "apiContractSha256", "migrationSequenceSha256",
    "parserArtifactSetSha256", "runtimeConfigurationSchemaSha256",
    "compatibilityEvidenceRefs", "restoreEvidenceRefs", "securityEvidenceRefs",
    "rollbackEligibility", "openRisks", "evidenceComplete", "productionReady",
}
APPROVER_FIELDS = {"role", "approverRef"}
ROLLBACK_FIELDS = {"status", "verified", "conditions"}
RISK_FIELDS = {"riskId", "ownerRef", "deadline", "status"}
REGISTRY_FIELDS = {
    "schemaVersion",
    "registryClass",
    "appendOnly",
    "productionEvidence",
    "approvedReleaseCount",
    "latestApprovedReleaseId",
    "latestRollbackEligibleReleaseId",
    "releases",
    "limitations",
}


class RegistrationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistrationFailure(message)


def require_actual_cli_authorities() -> None:
    for label, actual, canonical in (
        ("contract", CONTRACT_PATH, CANONICAL_CONTRACT_PATH),
        ("registry", REGISTRY_PATH, CANONICAL_REGISTRY_PATH),
    ):
        require(actual == canonical, f"release baseline CLI {label} authority substitution rejected")
        require(not actual.is_symlink(), f"release baseline CLI {label} authority must be symlink-free")
        require(actual.resolve(strict=True) == canonical.resolve(strict=True), f"release baseline CLI {label} authority drift")
    require(LOCK_PATH == CANONICAL_LOCK_PATH, "release baseline CLI lock authority substitution rejected")
    require(not LOCK_PATH.is_symlink(), "release baseline CLI lock authority must be symlink-free")
    require(
        LOCK_PATH.parent.resolve(strict=True) == CANONICAL_LOCK_PATH.parent.resolve(strict=True),
        "release baseline CLI lock parent authority drift",
    )


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RegistrationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RegistrationFailure(f"invalid JSON: {path}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path}")
    return value


def git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    require(completed.returncode == 0,
            f"git {' '.join(arguments)} failed without registration")
    return completed.stdout.strip()


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def exact_object(value: Any, fields: set[str], field: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{field} must be an object")
    require(set(value) == fields, f"{field} field set drift")
    return value


def require_utc_timestamp(value: Any, field: str) -> None:
    require(isinstance(value, str) and value.endswith("Z"),
            f"{field} must be an RFC3339 UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise RegistrationFailure(f"{field} is not a valid timestamp") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0),
            f"{field} must be UTC")


def validate_release_commit_lineage(commit_sha: str) -> None:
    head = git("rev-parse", "HEAD")
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit_sha, head],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0,
            f"release commit is not an ancestor of current HEAD: {commit_sha}")


def validate_evidence_ref_binding(commit_sha: str, ref: str) -> None:
    relative = Path(ref)
    require(not relative.is_absolute() and ".." not in relative.parts,
            f"unsafe evidence path: {ref}")
    path = ROOT / relative
    try:
        resolved = path.resolve(strict=True)
        resolved.relative_to(ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise RegistrationFailure(f"evidence path escapes repository or is unreadable: {ref}") from exc
    cursor = path
    while cursor != ROOT:
        require(not cursor.is_symlink(), f"evidence path contains symlink: {ref}")
        cursor = cursor.parent
    require(path.is_file(), f"evidence path missing: {ref}")
    git("ls-files", "--error-unmatch", "--", ref)
    source_blob = git("rev-parse", f"{commit_sha}:{ref}")
    current_blob = git("hash-object", "--", ref)
    require(source_blob == current_blob,
            f"release evidence changed after source commit: {ref}")


def validate_contract_for_append(contract: dict[str, Any]) -> set[str]:
    require(contract.get("schemaVersion") == "memory-os-release-baseline-registry-contract.v1",
            "release contract schemaVersion drift")
    expected_paths = {
        "registryPath": str(REGISTRY_PATH.relative_to(ROOT)),
        "appendLockPath": str(LOCK_PATH.relative_to(ROOT)),
        "validator": "scripts/validate-memory-os-release-baseline-registry.py",
        "writer": str(Path(__file__).resolve().relative_to(ROOT)),
    }
    for field, expected in expected_paths.items():
        require(contract.get(field) == expected, f"release contract path drift: {field}")
    require(contract.get("appendOnly") is True,
            "release contract must remain append-only")
    require(contract.get("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure") is True,
            "release contract must require post-append revalidation and rollback")
    require(contract.get("productionDecision") == "NO_GO",
            "release contract cannot authorize production")
    required_fields = set(strings(contract.get("requiredFields"), "requiredFields", len(RECORD_FIELDS)))
    require(required_fields == RECORD_FIELDS,
            "release contract requiredFields drift")

    approval = contract.get("approvalPolicy")
    require(isinstance(approval, dict), "release approvalPolicy missing")
    require(approval.get("approvalClass") == "PRODUCTION_RELEASE_BASELINE",
            "release approval class drift")
    minimum = approval.get("minimumDistinctApprovers")
    require(isinstance(minimum, int) and not isinstance(minimum, bool) and minimum == 3,
            "release minimum distinct approvers drift")
    require(set(strings(approval.get("requiredRoles"), "approvalPolicy.requiredRoles", 3)) == REQUIRED_ROLES,
            "release required approval roles drift")
    for field in (
        "selfApprovalForbidden", "candidateCommitIsInsufficient", "ciPassIsInsufficient",
        "tagAloneIsInsufficient", "branchHeadIsInsufficient",
        "productionTrafficIsForbiddenBeforeRegistration",
    ):
        require(approval.get(field) is True, f"release approval policy drift: {field}")

    binding = contract.get("evidenceBinding")
    require(isinstance(binding, dict) and binding.get("sourceCommitField") == "commitSha",
            "release evidence binding source field drift")
    for field in (
        "sourceCommitMustBeAncestorOfCurrentHead", "repositoryTrackedRequired",
        "repositoryContainmentRequired", "symlinkForbidden", "parentDirectorySymlinkForbidden",
        "sourceCommitBlobRequired", "currentBytesMustMatchSourceCommit",
    ):
        require(binding.get(field) is True, f"release evidence binding drift: {field}")
    return required_fields


def validate_record(record: dict[str, Any], required_fields: set[str]) -> None:
    require(set(record) == required_fields,
            f"record field set drift: {sorted(set(record) ^ required_fields)}")
    require(record.get("schemaVersion") == "memory-os-release-baseline-record.v1",
            "record schemaVersion drift")
    require(isinstance(record.get("releaseId"), str) and
            RELEASE_ID_RE.fullmatch(record["releaseId"]) is not None,
            "releaseId format invalid")
    require(isinstance(record.get("releaseTag"), str) and
            TAG_RE.fullmatch(record["releaseTag"]) is not None,
            "releaseTag format invalid")
    require(isinstance(record.get("commitSha"), str) and
            SHA_RE.fullmatch(record["commitSha"]) is not None,
            "commitSha format invalid")
    validate_release_commit_lineage(record["commitSha"])
    require_utc_timestamp(record.get("approvedAt"), "approvedAt")
    require(record.get("approvalClass") == "PRODUCTION_RELEASE_BASELINE",
            "approvalClass must be PRODUCTION_RELEASE_BASELINE")
    require(record.get("evidenceComplete") is True,
            "release baseline requires evidenceComplete=true")
    require(record.get("productionReady") is True,
            "release baseline requires productionReady=true")

    approvers = record.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 3,
            "exactly three required approvers are required")
    roles: set[str] = set()
    identities: set[str] = set()
    for approver in approvers:
        approver = exact_object(approver, APPROVER_FIELDS, "approver entry")
        role = approver.get("role")
        identity = approver.get("approverRef")
        require(role in REQUIRED_ROLES and role not in roles,
                f"approval role invalid or duplicated: {role}")
        require(isinstance(identity, str) and APPROVER_RE.fullmatch(identity) is not None,
                "approverRef must be an operational pseudonym")
        require(identity not in identities, "self-approval or duplicate approver detected")
        roles.add(role)
        identities.add(identity)
    require(roles == REQUIRED_ROLES, "required approval roles are incomplete")

    for field in (
        "apiContractSha256", "migrationSequenceSha256",
        "parserArtifactSetSha256", "runtimeConfigurationSchemaSha256",
    ):
        require(isinstance(record.get(field), str) and
                DIGEST_RE.fullmatch(record[field]) is not None,
                f"{field} must be a SHA-256 digest")

    for field in (
        "compatibilityEvidenceRefs", "restoreEvidenceRefs", "securityEvidenceRefs",
    ):
        for ref in strings(record.get(field), field, 1):
            validate_evidence_ref_binding(record["commitSha"], ref)

    rollback = exact_object(record.get("rollbackEligibility"), ROLLBACK_FIELDS, "rollbackEligibility")
    require(rollback.get("status") in ROLLBACK_VALUES,
            "rollbackEligibility invalid")
    conditions = rollback.get("conditions")
    require(isinstance(conditions, list), "rollback conditions must be a list")
    if rollback["status"] == "ELIGIBLE":
        require(rollback.get("verified") is True and not conditions,
                "ELIGIBLE rollback requires verified=true and no conditions")
    elif rollback["status"] == "CONDITIONALLY_ELIGIBLE":
        require(rollback.get("verified") is True,
                "conditional rollback requires verified=true")
        strings(conditions, "rollbackEligibility.conditions", 1)
    else:
        require(rollback.get("verified") is False,
                "NOT_ELIGIBLE rollback must remain unverified")

    risks = record.get("openRisks")
    require(isinstance(risks, list), "openRisks must be a list")
    for risk in risks:
        risk = exact_object(risk, RISK_FIELDS, "open risk entry")
        require(risk.get("riskId") and risk.get("ownerRef") and
                risk.get("deadline") and risk.get("status"),
                "open risk entry is incomplete")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "authorization: bearer",
        "minioadmin", "secretaccesskey", "account_id", "session_id",
        "job_id", "preview_id", "object_key", "apple_subject", "@",
    ):
        require(forbidden not in serialized,
                f"record contains forbidden content: {forbidden}")


def validate_registry_for_append(
    registry: dict[str, Any], contract: dict[str, Any] | None = None
) -> None:
    if contract is None:
        contract = load(CONTRACT_PATH)
    required_fields = validate_contract_for_append(contract)
    require(set(registry) == REGISTRY_FIELDS, "release registry field set drift")
    require(registry.get("schemaVersion") == "memory-os-release-baseline-registry.v1",
            "release registry schemaVersion drift")
    require(registry.get("registryClass") == "APPROVED_PRODUCTION_RELEASE_BASELINES",
            "release registry class drift")
    require(registry.get("appendOnly") is True, "release registry must remain append-only")
    require(registry.get("productionEvidence") is False,
            "release registry cannot claim production evidence")
    releases = registry.get("releases")
    require(isinstance(releases, list) and all(isinstance(item, dict) for item in releases),
            "release registry contains invalid releases")
    count = registry.get("approvedReleaseCount")
    require(isinstance(count, int) and not isinstance(count, bool),
            "approvedReleaseCount must be an integer")
    require(count == len(releases), "approvedReleaseCount drift")
    release_ids: set[str] = set()
    tags: set[str] = set()
    commits: set[str] = set()
    for record in releases:
        validate_record(record, required_fields)
        release_id = record["releaseId"]
        release_tag = record["releaseTag"]
        commit_sha = record["commitSha"]
        require(release_id not in release_ids, f"duplicate registered releaseId: {release_id}")
        require(release_tag not in tags, f"duplicate registered releaseTag: {release_tag}")
        require(commit_sha not in commits, f"duplicate registered commitSha: {commit_sha}")
        release_ids.add(release_id)
        tags.add(release_tag)
        commits.add(commit_sha)
    expected_latest = releases[-1]["releaseId"] if releases else None
    require(registry.get("latestApprovedReleaseId") == expected_latest,
            "latestApprovedReleaseId drift")
    eligible = [
        record["releaseId"] for record in releases
        if record.get("rollbackEligibility", {}).get("status") in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"}
    ]
    require(registry.get("latestRollbackEligibleReleaseId") == (eligible[-1] if eligible else None),
            "latestRollbackEligibleReleaseId drift")
    limitations = registry.get("limitations")
    require(isinstance(limitations, list) and limitations and
            all(isinstance(item, str) and item.strip() for item in limitations),
            "release registry limitations invalid")


def acquire_lock() -> int:
    try:
        return os.open(LOCK_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise RegistrationFailure("release registry lock already exists") from exc


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=".release-baseline-registry.", suffix=".tmp",
        dir=REGISTRY_PATH.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY_PATH)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def atomic_write_bytes(value: bytes) -> None:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=".release-baseline-registry.", suffix=".tmp",
        dir=REGISTRY_PATH.parent,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY_PATH)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def append_registry_transactionally(
    registry: dict[str, Any], contract: dict[str, Any], original_bytes: bytes
) -> None:
    atomic_write(registry)
    try:
        validate_registry_for_append(load(REGISTRY_PATH), contract)
    except Exception:
        atomic_write_bytes(original_bytes)
        raise


def main() -> int:
    require_actual_cli_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True,
                        help="JSON record outside the repository working tree")
    parser.add_argument("--confirm", required=True)
    arguments = parser.parse_args()

    require(arguments.confirm == CONFIRMATION,
            f"confirmation must equal: {CONFIRMATION}")
    record_path = Path(arguments.record).resolve()
    try:
        record_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise RegistrationFailure("input record must be outside the repository")

    require(git("status", "--porcelain") == "",
            "working tree must be clean before release registration")
    head = git("rev-parse", "HEAD")
    contract = load(CONTRACT_PATH)
    required_fields = validate_contract_for_append(contract)
    record = load(record_path)
    validate_record(record, required_fields)
    require(record["commitSha"] == head,
            "release commitSha must equal exact repository HEAD")
    tag_commit = git("rev-list", "-n", "1", f"refs/tags/{record['releaseTag']}")
    require(tag_commit == head, "release tag must resolve to exact repository HEAD")

    lock_fd = acquire_lock()
    try:
        os.write(lock_fd, f"{record['releaseId']}\n".encode("ascii"))
        os.fsync(lock_fd)
        original_registry_bytes = REGISTRY_PATH.read_bytes()
        registry = load(REGISTRY_PATH)
        validate_registry_for_append(registry, contract)
        releases = registry["releases"]
        require(all(item.get("releaseId") != record["releaseId"] for item in releases),
                "releaseId is already registered")
        require(all(item.get("releaseTag") != record["releaseTag"] for item in releases),
                "releaseTag is already registered")
        require(all(item.get("commitSha") != record["commitSha"] for item in releases),
                "commitSha is already registered")

        releases.append(record)
        registry["approvedReleaseCount"] = len(releases)
        registry["latestApprovedReleaseId"] = record["releaseId"]
        eligible = [item["releaseId"] for item in releases
                    if item.get("rollbackEligibility", {}).get("status") in
                    {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"}]
        registry["latestRollbackEligibleReleaseId"] = eligible[-1] if eligible else None
        append_registry_transactionally(registry, contract, original_registry_bytes)
    finally:
        os.close(lock_fd)
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass

    print(f"Registered release baseline: {record['releaseId']}")
    print("Run scripts/validate-memory-os-release-baseline-registry.py and obtain review before any production action.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegistrationFailure as exc:
        print(f"RELEASE BASELINE REGISTRATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
