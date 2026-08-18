#!/usr/bin/env python3
"""Fail-closed validator for reviewed immutable client baseline authority."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/client-baseline-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/client-baseline-registry.v1.json"
WRITER = ROOT / "scripts/register-memory-os-client-baseline.py"
LOCK = ROOT / "contracts/operations/.client-baseline-registry.lock"
RUNBOOK = ROOT / "docs/evidence/clients/README.md"
WORKFLOW = ROOT / ".github/workflows/client-baseline-registry.yml"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CLIENT_CLASSES = {"IOS_APP", "PORTAL"}
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
    require(Path(module.LOCK).resolve() == LOCK.resolve(), "writer append lock authority drift")
    return module


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list) and len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value), f"{field} contains invalid value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def safe_ref(value: Any, field: str) -> str:
    require(isinstance(value, str) and value, f"{field} is required")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts,
            f"{field} contains an unsafe path")
    require((ROOT / path).is_file(), f"{field} path missing: {value}")
    return value


def commit_is_ancestor(sha: str) -> bool:
    """Compatibility helper for lineage negatives; canonical semantics live in the writer guard."""
    if not isinstance(sha, str) or not sha:
        return False
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
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)), "append lock binding drift")
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
    for key in (
        "selfApprovalForbidden", "sourceCommitIsInsufficient", "ciPassIsInsufficient",
        "marketingVersionIsInsufficient", "artifactDigestWithoutBytesIsInsufficient",
        "productionTrafficForbiddenForRegistration",
    ):
        require(policy.get(key) is True, f"approval policy weakened: {key}")

    required_fields = set(strings(contract.get("requiredRecordFields"), "requiredRecordFields", 20))
    for required in (
        "artifactSha256", "artifactByteLength", "approvers", "approvedForPairing",
        "productionEvidence", "productionReady",
    ):
        require(required in required_fields, f"requiredRecordFields omits {required}")

    guards = strings(contract.get("registrationGuards"), "registrationGuards", 12)
    require(any("ancestor of current HEAD" in guard for guard in guards),
            "registration guards must require source lineage ancestry")
    require(any("sourceCommitSha" in guard and "current bytes" in guard for guard in guards),
            "registration guards must require immutable source-bound evidence")
    require(any("historical registered evidence" in guard for guard in guards),
            "registration guards must require historical evidence revalidation")
    require(any("canonical exclusive append lock" in guard for guard in guards),
            "registration guards must require canonical append lock")

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

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "client baseline registry cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL" and gate.get("blocking") is True,
            "client baseline registry cannot make OPS-P0-008 ready")

    for field, expected in {
        "registryPath": str(REGISTRY.relative_to(ROOT)),
        "writer": str(WRITER.relative_to(ROOT)),
        "validator": str(Path(__file__).resolve().relative_to(ROOT)),
    }.items():
        require(contract.get(field) == expected, f"contract path drift: {field}")
        safe_ref(expected, field)

    print("Memory OS reviewed client baseline registry validation PASS")
    print(f"approved client baselines: {count}")
    print(f"approved iOS baseline available: {str(latest['IOS_APP'] is not None).lower()}")
    print(f"approved Portal baseline available: {str(latest['PORTAL'] is not None).lower()}")
    print("historical record semantics: enforced by canonical writer append guard")
    print("client/server skew evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CLIENT BASELINE REGISTRY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
