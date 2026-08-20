#!/usr/bin/env python3
"""Fold exact-source upload-completion pre-fence evidence into OPS-P0-006 without widening its scope."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROOF_CONTRACT = ROOT / "contracts/operations/deletion-prefence-upload-completion-contract.v1.json"
PROOF_RESULT = ROOT / "docs/fixtures/memory-os-operability/deletion-prefence-upload-completion-results.sample.v1.json"
PROOF_VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-prefence-upload-completion.py"
LOAD_CONTRACT = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"

PROOF_REFS = [
    "contracts/operations/deletion-prefence-upload-completion-contract.v1.json",
    "services/import-api/internal/httpserver/deletion_prefence_upload_completion_test.go",
    "scripts/validate-memory-os-deletion-prefence-upload-completion.py",
    "scripts/reconcile-memory-os-deletion-prefence-upload-completion.py",
    ".github/workflows/deletion-prefence-upload-completion.yml",
    "docs/fixtures/memory-os-operability/deletion-prefence-upload-completion-results.sample.v1.json",
]

EVIDENCE_TEXT = (
    "exact-source local pre-fence upload-completion proof issues and uploads 16 real versioned MinIO objects, "
    "lets all 16 completion requests pass authentication, the outer epoch guard, the initial authorization "
    "snapshot and real MinIO HEAD, durably advances account deletion to epoch 2, then proves every resumed "
    "completion returns 401 with zero consumed authorizations or quarantine rows before worker erasure; the "
    "worker subsequently removes all 16 object versions and all owned database rows"
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def append_unique(values: list[Any], item: str) -> None:
    if item not in values:
        values.append(item)


def replace_exact(values: list[Any], old: str, new: str) -> None:
    for index, value in enumerate(values):
        if value == old:
            values[index] = new
            return


def main() -> int:
    subprocess.run(["python", str(PROOF_VALIDATOR), "--require-result"], cwd=ROOT, check=True)

    proof_contract = load(PROOF_CONTRACT)
    proof_result = load(PROOF_RESULT)
    readiness = proof_contract.get("readiness", {})
    if readiness.get("exactSourceResultCommitted") is not True:
        raise SystemExit("upload-completion proof is not reconciled")
    if readiness.get("preFenceUploadCompletionLinearizationProven") is not True:
        raise SystemExit("upload-completion linearization is not proven")
    environment = proof_result.get("environment", {})
    scenario = proof_result.get("scenario", {})
    if scenario.get("result") != "PASS" or scenario.get("integrityResult") != "PASS":
        raise SystemExit("upload-completion proof result must PASS")
    for key in ("productionEvidence", "productionEquivalentDependencies", "containsSecrets"):
        if environment.get(key) is not False:
            raise SystemExit(f"upload-completion local proof cannot enable {key}")

    load_contract = load(LOAD_CONTRACT)
    load_readiness = load_contract.setdefault("readiness", {})
    if not all(
        load_readiness.get(key) is True
        for key in (
            "previewPreFenceInFlightLinearizationProven",
            "applyPreFenceInFlightLinearizationProven",
            "uploadAuthorizationPreFenceInFlightLinearizationProven",
        )
    ):
        raise SystemExit("earlier pre-fence proofs must remain proven before aggregate promotion")
    load_readiness["uploadCompletionPreFenceInFlightLinearizationProven"] = True
    load_readiness["primaryAccountBoundPreFenceLinearizationAggregateProven"] = True
    load_readiness["note"] = (
        "Mock and local dependency checkpoints include bounded ramp, short CI stability, post-fence deletion load, "
        "Preview pre-fence linearization, Apply/upload-authorization zero-mutation pre-fence linearization, "
        "post-HEAD upload-completion pre-fence linearization, and bounded multi-account deletion-worker saturation. "
        "They still establish neither production capacity, sustained-soak/leak proof, host/process failure recovery, "
        "production-equivalent behavior nor independently reviewed operating thresholds; OPS-P0-006 remains PARTIAL."
    )

    for scenario_entry in load_contract.get("deferredScenarios", []):
        if scenario_entry.get("scenarioId") == "deletion-under-load":
            scenario_entry["reason"] = (
                "post-fence former-session load, Preview requests authenticated before the fence, Apply and "
                "upload-authorization requests authenticated before the fence with zero pre-worker durable mutation, "
                "upload-completion requests paused after real MinIO HEAD and rejected after the epoch-2 fence, and "
                "bounded 24-account/four-worker deletion saturation now pass against local PostgreSQL and MinIO; "
                "host/process failure behavior, production dependency behavior and independently reviewed deletion-load "
                "thresholds remain deferred"
            )
            break
    else:
        raise SystemExit("deletion-under-load deferred scenario missing")

    load_refs = load_contract.setdefault("evidenceRefs", [])
    for ref in PROOF_REFS:
        append_unique(load_refs, ref)

    status = load(STATUS)
    ops = None
    for area in status.get("areas", []):
        if area.get("id") == "OPS-P0-006":
            ops = area
            break
    if ops is None:
        raise SystemExit("OPS-P0-006 missing")
    if ops.get("status") != "PARTIAL" or ops.get("blocking") is not True:
        raise SystemExit("OPS-P0-006 must remain blocking PARTIAL")

    existing = ops.setdefault("existingEvidence", [])
    append_unique(existing, EVIDENCE_TEXT)
    missing = ops.setdefault("missingEvidence", [])
    replace_exact(
        missing,
        "pre-fence in-flight linearization for upload-completion requests, host/process failure behavior, production topology and independently reviewed deletion-load thresholds",
        "host/process failure behavior during deletion-worker execution, production topology and independently reviewed deletion-load thresholds",
    )
    replace_exact(
        missing,
        "request-linearization proof for operations already in flight before the deletion fence plus multi-account worker saturation, production topology and independently reviewed deletion-load thresholds",
        "deletion-worker process/host interruption recovery, production topology and independently reviewed deletion-load thresholds",
    )
    refs = ops.setdefault("evidenceRefs", [])
    for ref in PROOF_REFS:
        append_unique(refs, ref)

    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("productionDecision must remain NO_GO")

    original_load = LOAD_CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    try:
        write(LOAD_CONTRACT, load_contract)
        write(STATUS, status)
        subprocess.run(["python", str(LOAD_VALIDATOR)], cwd=ROOT, check=True)
        subprocess.run(["python", str(OPERABILITY_VALIDATOR)], cwd=ROOT, check=True)
    except BaseException:
        LOAD_CONTRACT.write_bytes(original_load)
        STATUS.write_bytes(original_status)
        raise

    print("Memory OS upload-completion load authority reconciliation PASS")
    print("upload completion pre-fence linearization proven: true")
    print("OPS-P0-006: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
