#!/usr/bin/env python3
"""Fail-closed validation for the approved release baseline registry."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
WRITER_PATH = ROOT / "scripts/register-memory-os-release-baseline.py"
CANDIDATE_CONTRACT_PATH = ROOT / "contracts/operations/mixed-version-candidate-contract.v1.json"
REJECTION_PATH = ROOT / "docs/fixtures/memory-os-operability/mixed-version-candidate-rejections.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
RELEASE_ID_RE = re.compile(r"^rel_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")
TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")
APPROVER_RE = re.compile(r"^apr_[a-z0-9][a-z0-9_-]{7,63}$")
REQUIRED_ROLES = {"SECURITY_REVIEWER", "OPERABILITY_REVIEWER", "RELEASE_OWNER"}
ROLLBACK_VALUES = {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE", "NOT_ELIGIBLE"}


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_release_baseline_writer_validator", WRITER_PATH)
    require(spec is not None and spec.loader is not None,
            "cannot load canonical release baseline writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT_PATH", None) == CONTRACT_PATH,
            "release writer contract authority drift")
    require(getattr(module, "REGISTRY_PATH", None) == REGISTRY_PATH,
            "release writer registry authority drift")
    return module


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum,
            f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def parse_utc(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"),
            f"{field} must be an RFC3339 UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise ValidationFailure(f"{field} is not a valid timestamp") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0),
            f"{field} must be UTC")
    return parsed


def validate_record(record: dict[str, Any], required_fields: set[str]) -> None:
    require(set(record) >= required_fields,
            f"release record missing fields: {sorted(required_fields - set(record))}")
    require(record.get("schemaVersion") == "memory-os-release-baseline-record.v1",
            "release record schemaVersion drift")
    release_id = record.get("releaseId")
    tag = record.get("releaseTag")
    commit_sha = record.get("commitSha")
    require(isinstance(release_id, str) and RELEASE_ID_RE.fullmatch(release_id) is not None,
            "releaseId format invalid")
    require(isinstance(tag, str) and TAG_RE.fullmatch(tag) is not None,
            f"release tag invalid: {tag}")
    require(isinstance(commit_sha, str) and SHA_RE.fullmatch(commit_sha) is not None,
            "release commitSha invalid")
    parse_utc(record.get("approvedAt"), "approvedAt")
    require(record.get("approvalClass") == "PRODUCTION_RELEASE_BASELINE",
            "release approvalClass drift")
    require(record.get("evidenceComplete") is True,
            "approved release record requires evidenceComplete=true")
    require(record.get("productionReady") is True,
            "approved release record requires productionReady=true")

    approvers = record.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 3,
            "release requires exactly three approvers")
    roles: set[str] = set()
    identities: set[str] = set()
    for approver in approvers:
        require(isinstance(approver, dict), "approver entry must be an object")
        role = approver.get("role")
        identity = approver.get("approverRef")
        require(role in REQUIRED_ROLES, f"unknown approval role: {role}")
        require(isinstance(identity, str) and APPROVER_RE.fullmatch(identity) is not None,
                "approverRef must be an operational pseudonym")
        require(role not in roles, f"duplicate approval role: {role}")
        require(identity not in identities, "self-approval or duplicate approver detected")
        roles.add(role)
        identities.add(identity)
    require(roles == REQUIRED_ROLES,
            f"approval roles incomplete: {sorted(REQUIRED_ROLES - roles)}")

    for field in (
        "apiContractSha256", "migrationSequenceSha256",
        "parserArtifactSetSha256", "runtimeConfigurationSchemaSha256",
    ):
        value = record.get(field)
        require(isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None,
                f"{field} must be a SHA-256 digest")

    for field in (
        "compatibilityEvidenceRefs", "restoreEvidenceRefs", "securityEvidenceRefs",
    ):
        refs = strings(record.get(field), field, 1)
        for ref in refs:
            relative = Path(ref)
            require(not relative.is_absolute() and ".." not in relative.parts,
                    f"{field} contains an unsafe path: {ref}")
            require((ROOT / relative).is_file(), f"{field} evidence missing: {ref}")

    rollback = record.get("rollbackEligibility")
    require(isinstance(rollback, dict), "rollbackEligibility must be an object")
    require(rollback.get("status") in ROLLBACK_VALUES,
            "rollback eligibility status invalid")
    conditions = rollback.get("conditions")
    require(isinstance(conditions, list), "rollback conditions must be a list")
    if rollback.get("status") == "ELIGIBLE":
        require(not conditions and rollback.get("verified") is True,
                "ELIGIBLE rollback requires verified=true and no conditions")
    elif rollback.get("status") == "CONDITIONALLY_ELIGIBLE":
        strings(conditions, "rollbackEligibility.conditions", 1)
        require(rollback.get("verified") is True,
                "conditional rollback requires verified=true")
    else:
        require(rollback.get("verified") is False,
                "NOT_ELIGIBLE rollback must remain unverified")

    open_risks = record.get("openRisks")
    require(isinstance(open_risks, list), "openRisks must be a list")
    for risk in open_risks:
        require(isinstance(risk, dict) and risk.get("riskId") and
                risk.get("ownerRef") and risk.get("deadline") and risk.get("status"),
                "open risk entry is incomplete")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "password=", "authorization: bearer",
        "minioadmin", "secretaccesskey", "account_id", "session_id",
        "job_id", "preview_id", "object_key", "apple_subject", "@",
    ):
        require(forbidden not in serialized,
                f"release record contains forbidden content: {forbidden}")


def validate_writer(path: Path) -> None:
    require(path.is_file(), "release registry writer is missing")
    source = path.read_text(encoding="utf-8")
    for required in (
        "REGISTER APPROVED RELEASE BASELINE",
        "os.O_EXCL",
        "os.replace",
        "working tree must be clean",
        "release tag must resolve to exact repository HEAD",
        "releaseId is already registered",
        "releaseTag is already registered",
        "commitSha is already registered",
        "evidenceComplete=true",
        "productionReady=true",
        "input record must be outside the repository",
    ):
        require(required in source, f"release writer missing guard: {required}")
    for forbidden in (
        "git tag ", "git push", "approvalClass =", "productionReady = True",
        "evidenceComplete = True",
    ):
        require(forbidden not in source,
                f"release writer must not manufacture authority: {forbidden}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    registry = load(REGISTRY_PATH)
    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry, contract)
    except Exception as exc:
        raise ValidationFailure(f"canonical release writer authority rejected registry: {exc}") from exc

    require(contract.get("schemaVersion") ==
            "memory-os-release-baseline-registry-contract.v1",
            "release registry contract schemaVersion drift")
    require(contract.get("registryPath") == str(REGISTRY_PATH.relative_to(ROOT)),
            "release registry path drift")
    require(contract.get("canonicalRunbook") == "docs/evidence/releases/README.md",
            "release registry runbook path drift")
    require(contract.get("validator") ==
            "scripts/validate-memory-os-release-baseline-registry.py",
            "release registry validator path drift")
    require(contract.get("writer") == "scripts/register-memory-os-release-baseline.py",
            "release registry writer path drift")
    require(contract.get("appendOnly") is True and
            contract.get("productionDecision") == "NO_GO",
            "release registry foundation cannot change production decision")
    required_fields = set(strings(contract.get("requiredFields"), "requiredFields", 18))
    require({"evidenceComplete", "productionReady"} <= required_fields,
            "release record completion fields are not binding")

    approval = contract.get("approvalPolicy")
    require(isinstance(approval, dict), "approvalPolicy missing")
    require(approval.get("minimumDistinctApprovers") == 3 and
            set(approval.get("requiredRoles", [])) == REQUIRED_ROLES,
            "release approval policy drift")
    for field in (
        "selfApprovalForbidden", "candidateCommitIsInsufficient",
        "ciPassIsInsufficient", "tagAloneIsInsufficient",
        "branchHeadIsInsufficient", "productionTrafficIsForbiddenBeforeRegistration",
    ):
        require(approval.get(field) is True, f"approval guard missing: {field}")
    strings(contract.get("requiredEvidenceClasses"), "requiredEvidenceClasses", 7)
    strings(contract.get("forbiddenRecordContent"), "forbiddenRecordContent", 6)
    strings(contract.get("registrationGuards"), "registrationGuards", 10)

    writer_path = ROOT / contract["writer"]
    validate_writer(writer_path)

    require(registry.get("schemaVersion") == "memory-os-release-baseline-registry.v1",
            "release registry schemaVersion drift")
    require(registry.get("registryClass") == "APPROVED_PRODUCTION_RELEASE_BASELINES" and
            registry.get("appendOnly") is True and
            registry.get("productionEvidence") is False,
            "release registry authority drift")
    releases = registry.get("releases")
    require(isinstance(releases, list), "release registry releases must be a list")
    release_ids: set[str] = set()
    tags: set[str] = set()
    commits: set[str] = set()
    for record in releases:
        require(isinstance(record, dict), "release record must be an object")
        validate_record(record, required_fields)
        for field, seen in (
            ("releaseId", release_ids), ("releaseTag", tags), ("commitSha", commits)
        ):
            value = record[field]
            require(value not in seen, f"duplicate registered {field}: {value}")
            seen.add(value)

    require(registry.get("approvedReleaseCount") == len(releases),
            "approvedReleaseCount does not match releases")
    if releases:
        require(registry.get("latestApprovedReleaseId") == releases[-1]["releaseId"],
                "latestApprovedReleaseId drift")
        eligible = [record["releaseId"] for record in releases
                    if record["rollbackEligibility"]["status"] in
                    {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"}]
        require(registry.get("latestRollbackEligibleReleaseId") ==
                (eligible[-1] if eligible else None),
                "latestRollbackEligibleReleaseId drift")
    else:
        require(registry.get("latestApprovedReleaseId") is None and
                registry.get("latestRollbackEligibleReleaseId") is None,
                "empty registry cannot name a release")

    candidate = load(CANDIDATE_CONTRACT_PATH)
    candidate_sha = candidate.get("candidateBaseline", {}).get("commitSha")
    rejected = load(REJECTION_PATH)
    rejected_shas = {item.get("commitSha") for item in rejected.get("candidates", [])
                     if isinstance(item, dict)}
    require(candidate_sha not in commits,
            "historical active candidate was registered as an approved release")
    require(not (rejected_shas & commits),
            "rejected candidate was registered as an approved release")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "release registry readiness missing")
    for field in (
        "contractDefined", "registryImplemented", "validatorImplemented", "writerImplemented"
    ):
        require(readiness.get(field) is True, f"release foundation missing: {field}")
    require(readiness.get("approvedReleaseCount") == len(releases),
            "contract approvedReleaseCount drift")
    require(readiness.get("approvedPredecessorAvailable") is (len(releases) >= 1),
            "approvedPredecessorAvailable drift")
    eligible_exists = any(record["rollbackEligibility"]["status"] in
                          {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"}
                          for record in releases)
    require(readiness.get("rollbackEligibleReleaseAvailable") is eligible_exists,
            "rollbackEligibleReleaseAvailable drift")
    require(readiness.get("independentReviewCompleted") is False and
            readiness.get("productionReady") is False,
            "release registry foundation cannot make production ready")

    refs = strings(contract.get("evidenceRefs"), "evidenceRefs", 7)
    require(str(writer_path.relative_to(ROOT)) in refs,
            "release writer is not registered as evidence")
    for ref in refs:
        require((ROOT / ref).is_file(), f"release registry evidence missing: {ref}")
    runbook = (ROOT / contract["canonicalRunbook"]).read_text(encoding="utf-8")
    for phrase in (
        "Candidate is not release", "Required approval", "Rollback eligibility",
        "No release is approved", "Production remains\n**NO_GO**",
    ):
        require(phrase in runbook, f"release runbook missing phrase: {phrase}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "release registry cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") != "READY",
            "release registry foundation cannot make OPS-P0-008 READY")
    if not releases:
        missing = [str(item).lower() for item in gate.get("missingEvidence", [])]
        require(any("approved" in item and "release" in item for item in missing),
                "OPS-P0-008 must retain the approved release baseline gap")
        require(any("rollback-eligible" in item for item in missing),
                "OPS-P0-008 must retain the rollback-eligible release gap")

    print("Memory OS release baseline registry validation PASS")
    print(f"approved releases: {len(releases)}")
    print(f"rollback eligible releases: {sum(1 for r in releases if r['rollbackEligibility']['status'] != 'NOT_ELIGIBLE')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"RELEASE BASELINE REGISTRY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
