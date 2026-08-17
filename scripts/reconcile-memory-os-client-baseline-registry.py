#!/usr/bin/env python3
"""Reconcile reviewed client baseline authority without creating skew or production claims."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/client-baseline-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/client-baseline-registry.v1.json"
SUPPORT = ROOT / "contracts/operations/client-server-support-window-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-client-baseline.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-client-baseline-registry.py"
SUPPORT_VALIDATOR = ROOT / "scripts/validate-memory-os-client-server-support-window.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
WORKFLOW = ROOT / ".github/workflows/client-baseline-registry.yml"
RUNBOOK = ROOT / "docs/evidence/clients/README.md"

EVIDENCE = (
    "append-only reviewed client baseline authority now has an external-byte-verifying writer, fail-closed validator and operator runbook: exact iOS/Portal artifact SHA-256 and byte length are recomputed, source provenance and repository evidence are bound, CLIENT_OWNER/Security/Compatibility approvals must be distinct, and baseline approval remains explicitly separate from client/server skew and Production readiness"
)
REFS = (
    "contracts/operations/client-baseline-registry-contract.v1.json",
    "contracts/operations/client-baseline-registry.v1.json",
    "scripts/register-memory-os-client-baseline.py",
    "scripts/validate-memory-os-client-baseline-registry.py",
    "scripts/reconcile-memory-os-client-baseline-registry.py",
    "docs/evidence/clients/README.md",
    ".github/workflows/client-baseline-registry.yml",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def run_validator(path: Path, label: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"{label} failed:\n{completed.stdout[-4000:]}{completed.stderr[-4000:]}",
    )


def write_and_validate_transactionally(
    contract: dict[str, Any], support: dict[str, Any], status: dict[str, Any]
) -> None:
    paths = (CONTRACT, SUPPORT, STATUS)
    originals = {path: path.read_bytes() for path in paths}
    try:
        write(CONTRACT, contract)
        write(SUPPORT, support)
        write(STATUS, status)
        run_validator(VALIDATOR, "post-write client registry validator")
        run_validator(SUPPORT_VALIDATOR, "post-write support-window validator")
        run_validator(OPERABILITY_VALIDATOR, "post-write operability validator")
    except Exception:
        for path in paths:
            path.write_bytes(originals[path])
        raise


def main() -> int:
    for path in (WRITER, VALIDATOR, SUPPORT_VALIDATOR, OPERABILITY_VALIDATOR, WORKFLOW, RUNBOOK):
        require(path.is_file(), f"client baseline foundation missing: {path.relative_to(ROOT)}")

    registry = load(REGISTRY)
    clients = registry.get("clients")
    count = registry.get("approvedClientBaselineCount")
    latest = registry.get("latestApprovedClientByClass")
    require(
        isinstance(clients, list)
        and isinstance(count, int)
        and not isinstance(count, bool)
        and count == len(clients),
        "client registry count drift",
    )
    require(isinstance(latest, dict) and set(latest) == {"IOS_APP", "PORTAL"}, "client latest map drift")

    contract = load(CONTRACT)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "client baseline readiness missing")
    readiness["writerImplemented"] = True
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["approvedClientBaselineCount"] = count
    readiness["approvedIOSBaselineAvailable"] = latest["IOS_APP"] is not None
    readiness["approvedPortalBaselineAvailable"] = latest["PORTAL"] is not None
    readiness["clientServerSkewEvidence"] = False
    readiness["productionReady"] = False
    contract["productionDecision"] = "NO_GO"

    releases = load(RELEASES)
    release_count = releases.get("approvedReleaseCount")
    require(
        isinstance(release_count, int) and not isinstance(release_count, bool) and release_count >= 0,
        "release registry count invalid",
    )

    support = load(SUPPORT)
    boundary = support.get("currentBoundary")
    support_readiness = support.get("readiness")
    require(isinstance(boundary, dict) and isinstance(support_readiness, dict), "support window boundary/readiness missing")
    boundary["approvedBackendReleaseCount"] = release_count
    boundary["approvedClientBaselineCount"] = count
    if release_count == 0 or count == 0:
        boundary["admissibleSkewPairCount"] = 0
    boundary["implementedClientSupportWindow"] = False
    boundary["clientServerSkewEvidence"] = False
    boundary["releaseCompatibilityEvidence"] = False
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    support_readiness["approvedBackendReleaseAvailable"] = release_count > 0
    support_readiness["approvedClientBaselineAvailable"] = count > 0
    support_readiness["supportWindowImplemented"] = False
    support_readiness["skewPairExecuted"] = False
    support_readiness["independentReviewCompleted"] = False
    support_readiness["productionReady"] = False

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "client baseline authority cannot change production decision")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict), "OPS-P0-008 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-008 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-008 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"client baseline evidence ref missing: {ref}")
        append_once(refs, ref)
    joined = "\n".join(str(item).lower() for item in missing)
    require("client/server" in joined and "skew" in joined, "runtime client/server skew blocker must remain")
    require("approved predecessor" in joined and "successor" in joined, "approved release-pair blocker must remain")

    write_and_validate_transactionally(contract, support, status)

    print("Memory OS client baseline authority reconciliation PASS")
    print(f"approved client baselines: {count}")
    print("external artifact writer: implemented")
    print("client/server skew evidence: false")
    print("OPS-P0-008: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CLIENT BASELINE AUTHORITY RECONCILE FAILED: {exc}")
        raise SystemExit(1)
