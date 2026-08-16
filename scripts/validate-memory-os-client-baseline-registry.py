#!/usr/bin/env python3
"""Fail-closed validator for reviewed immutable client baseline authority."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/client-baseline-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/client-baseline-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-client-baseline.py"
RUNBOOK = ROOT / "docs/evidence/clients/README.md"
WORKFLOW = ROOT / ".github/workflows/client-baseline-registry.yml"

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
BASELINE_ID = re.compile(r"^clb_[0-9]{8}_[a-z0-9][a-z0-9._-]{2,63}$")
APPROVER = re.compile(r"^apr_[a-z0-9][a-z0-9_-]{7,63}$")
VERSION = re.compile(r"^[0-9]+(?:\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?$")
BUILD = re.compile(r"^[0-9A-Za-z._-]{1,64}$")
CLIENT_CLASSES = {"IOS_APP", "PORTAL"}
ARTIFACT_KINDS = {"IOS_IPA", "IOS_XCARCHIVE_EXPORT", "PORTAL_BUNDLE"}
REQUIRED_ROLES = {"CLIENT_OWNER", "SECURITY_REVIEWER", "COMPATIBILITY_REVIEWER"}


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


def load_writer() -> Any:
    require(WRITER.is_file(), "writer missing")
    spec = importlib.util.spec_from_file_location("memory_os_client_baseline_writer", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load canonical client writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(Path(module.REGISTRY).resolve() == REGISTRY.resolve(), "writer registry authority drift")
    require(Path(module.CONTRACT).resolve() == CONTRACT.resolve(), "writer contract authority drift")
    return module


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value), f"{field} contains invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def utc_timestamp(value: Any, field: str) -> None:
    require(isinstance(value, str) and value.endswith("Z"), f"{field} must be RFC3339 UTC")
    try:
        parsed = dt.datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise Fail(f"{field} invalid timestamp") from exc
    require(parsed.utcoffset() == dt.timedelta(0), f"{field} must be UTC")


def commit_is_ancestor(sha: str) -> bool:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if head.returncode != 0:
        return False
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, head.stdout.strip()],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def validate_record(record: dict[str, Any], required_fields: set[str], index: int) -> None:
    prefix = f"clients[{index}]"
    require(set(record) >= required_fields, f"{prefix} missing fields: {sorted(required_fields - set(record))}")
    require(record.get("schemaVersion") == "memory-os-client-baseline-record.v1", f"{prefix} schema drift")
    baseline_id = record.get("clientBaselineId")
    require(isinstance(baseline_id, str) and BASELINE_ID.fullmatch(baseline_id) is not None, f"{prefix}.clientBaselineId invalid")
    client_class = record.get("clientClass")
    require(client_class in CLIENT_CLASSES, f"{prefix}.clientClass invalid")
    require(isinstance(record.get("marketingVersion"), str) and VERSION.fullmatch(record["marketingVersion"]) is not None, f"{prefix}.marketingVersion invalid")
    require(isinstance(record.get("buildNumber"), str) and BUILD.fullmatch(record["buildNumber"]) is not None, f"{prefix}.buildNumber invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source) is not None and commit_is_ancestor(source), f"{prefix}.sourceCommitSha invalid or not an ancestor of current HEAD")
    artifact_kind = record.get("artifactKind")
    require(artifact_kind in ARTIFACT_KINDS, f"{prefix}.artifactKind invalid")
    if client_class == "IOS_APP":
        require(artifact_kind in {"IOS_IPA", "IOS_XCARCHIVE_EXPORT"}, f"{prefix} iOS artifact kind mismatch")
    if client_class == "PORTAL":
        require(artifact_kind == "PORTAL_BUNDLE", f"{prefix} Portal artifact kind mismatch")
    utc_timestamp(record.get("approvedAt"), f"{prefix}.approvedAt")
    require(record.get("approvalClass") == "REVIEWED_CLIENT_BASELINE", f"{prefix}.approvalClass invalid")
    require(record.get("apiMajor") == "v1", f"{prefix}.apiMajor drift")
    require(record.get("signedUploadContract") == "memory-os-signed-upload.v1", f"{prefix}.signedUploadContract drift")
    for field in ("artifactSha256", "apiContractSha256", "clientBehaviorContractSha256"):
        value = record.get(field)
        require(isinstance(value, str) and SHA256.fullmatch(value) is not None, f"{prefix}.{field} invalid")
    require(isinstance(record.get("artifactByteLength"), int) and not isinstance(record.get("artifactByteLength"), bool) and record["artifactByteLength"] > 0, f"{prefix}.artifactByteLength invalid")
    require(record.get("evidenceComplete") is True, f"{prefix} evidence must be complete")
    require(record.get("approvedForPairing") is True, f"{prefix} must be explicitly approved for pairing")
    require(record.get("productionEvidence") is False, f"{prefix} cannot be production evidence")
    require(record.get("productionReady") is False, f"{prefix} cannot claim production readiness")

    approvers = record.get("approvers")
    require(isinstance(approvers, list) and len(approvers) == 3, f"{prefix} requires exactly three approvers")
    roles: set[str] = set()
    identities: set[str] = set()
    for item in approvers:
        require(isinstance(item, dict), f"{prefix} approver entry invalid")
        role = item.get("role")
        identity = item.get("approverRef")
        require(role in REQUIRED_ROLES and role not in roles, f"{prefix} approval role invalid/duplicate: {role}")
        require(isinstance(identity, str) and APPROVER.fullmatch(identity) is not None, f"{prefix} approverRef invalid")
        require(identity not in identities, f"{prefix} duplicate/self approval")
        roles.add(role)
        identities.add(identity)
    require(roles == REQUIRED_ROLES, f"{prefix} approval roles incomplete")

    for field in ("buildProvenanceEvidenceRefs", "securityEvidenceRefs", "compatibilityEvidenceRefs", "artifactRetentionEvidenceRefs"):
        for ref in strings(record.get(field), f"{prefix}.{field}"):
            relative = Path(ref)
            require(not relative.is_absolute() and ".." not in relative.parts, f"{prefix} unsafe evidence ref: {ref}")
            require((ROOT / relative).is_file(), f"{prefix} evidence ref missing: {ref}")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "postgres://", "postgresql://", "authorization: bearer", "password=", "minioadmin",
        "secretaccesskey", "apple developer", "account_id", "session_id", "job_id", "preview_id", "object_key", "@",
    ):
        require(forbidden not in serialized, f"{prefix} contains forbidden content: {forbidden}")


def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    writer = load_writer()
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"canonical writer rejected client registry authority: {exc}") from exc

    require(contract.get("schemaVersion") == "memory-os-client-baseline-registry-contract.v1", "contract schema drift")
    require(contract.get("registryPath") == str(REGISTRY.relative_to(ROOT)), "registryPath drift")
    require(contract.get("writer") == str(WRITER.relative_to(ROOT)), "writer path drift")
    require(contract.get("validator") == str(Path(__file__).resolve().relative_to(ROOT)), "validator path drift")
    require(contract.get("recordSchemaVersion") == "memory-os-client-baseline-record.v1", "record schema version drift")
    require(contract.get("appendOnly") is True and contract.get("productionDecision") == "NO_GO", "contract authority boundary drift")
    require(set(contract.get("allowedClientClasses", [])) == CLIENT_CLASSES, "allowed client classes drift")
    require(WRITER.is_file() and RUNBOOK.is_file(), "writer/runbook missing")

    policy = contract.get("approvalPolicy")
    require(isinstance(policy, dict), "approvalPolicy missing")
    require(policy.get("approvalClass") == "REVIEWED_CLIENT_BASELINE", "approval class drift")
    require(policy.get("minimumDistinctApprovers") == 3, "approver count drift")
    require(set(policy.get("requiredRoles", [])) == REQUIRED_ROLES, "approval roles drift")
    for key in ("selfApprovalForbidden", "sourceCommitIsInsufficient", "ciPassIsInsufficient", "marketingVersionIsInsufficient", "artifactDigestWithoutBytesIsInsufficient", "productionTrafficForbiddenForRegistration"):
        require(policy.get(key) is True, f"approval policy weakened: {key}")

    required_fields = set(strings(contract.get("requiredRecordFields"), "requiredRecordFields", 20))
    for required in ("artifactSha256", "artifactByteLength", "approvers", "approvedForPairing", "productionEvidence", "productionReady"):
        require(required in required_fields, f"requiredRecordFields omits {required}")

    guards = strings(contract.get("registrationGuards"), "registrationGuards", 12)
    require(any("ancestor of current HEAD" in guard for guard in guards),
            "registration guards must require source lineage ancestry")
    require(any("sourceCommitSha" in guard and "current bytes" in guard for guard in guards),
            "registration guards must require immutable source-bound evidence")

    require(registry.get("schemaVersion") == "memory-os-client-baseline-registry.v1", "registry schema drift")
    require(registry.get("registryClass") == "APPROVED_CLIENT_BASELINES", "registry class drift")
    require(registry.get("appendOnly") is True, "registry must be append-only")
    require(registry.get("productionEvidence") is False, "registry cannot itself be production evidence")
    clients = registry.get("clients")
    count = registry.get("approvedClientBaselineCount")
    latest = registry.get("latestApprovedClientByClass")
    require(isinstance(clients, list), "registry clients must be list")
    require(isinstance(count, int) and not isinstance(count, bool) and count == len(clients), "approved client count mismatch")
    require(isinstance(latest, dict) and set(latest) == CLIENT_CLASSES, "latestApprovedClientByClass drift")

    ids: set[str] = set()
    artifact_hashes: set[str] = set()
    last_by_class: dict[str, str | None] = {"IOS_APP": None, "PORTAL": None}
    for index, record in enumerate(clients):
        require(isinstance(record, dict), f"clients[{index}] must be object")
        validate_record(record, required_fields, index)
        baseline_id = record["clientBaselineId"]
        artifact_hash = record["artifactSha256"]
        require(baseline_id not in ids, f"duplicate clientBaselineId: {baseline_id}")
        require(artifact_hash not in artifact_hashes, f"duplicate artifactSha256: {artifact_hash}")
        ids.add(baseline_id)
        artifact_hashes.add(artifact_hash)
        last_by_class[record["clientClass"]] = baseline_id
    require(latest == last_by_class, f"latest client map drift: expected {last_by_class}, got {latest}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    require(readiness.get("contractDefined") is True and readiness.get("registryImplemented") is True, "definition readiness drift")
    require(readiness.get("writerImplemented") is WRITER.is_file(), "writerImplemented drift")
    require(readiness.get("validatorImplemented") is True, "validatorImplemented must be true")
    require(readiness.get("automaticWorkflowImplemented") is WORKFLOW.is_file(), "automaticWorkflowImplemented drift")
    require(readiness.get("approvedClientBaselineCount") == count, "readiness client count drift")
    require(readiness.get("approvedIOSBaselineAvailable") is (latest["IOS_APP"] is not None), "iOS availability drift")
    require(readiness.get("approvedPortalBaselineAvailable") is (latest["PORTAL"] is not None), "Portal availability drift")
    require(readiness.get("clientServerSkewEvidence") is False, "client baseline registry cannot prove skew")
    require(readiness.get("productionReady") is False, "client baseline registry cannot prove production readiness")

    print("Memory OS reviewed client baseline registry validation PASS")
    print(f"approved client baselines: {count}")
    print(f"approved iOS baseline available: {str(latest['IOS_APP'] is not None).lower()}")
    print(f"approved Portal baseline available: {str(latest['PORTAL'] is not None).lower()}")
    print("client/server skew evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CLIENT BASELINE REGISTRY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
