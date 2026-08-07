#!/usr/bin/env python3
"""Reconcile local multi-process shared-store rehearsal without promoting distributed runtime admission."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/rate-limit-local-multiprocess-shared-store-contract.v1.json"
RESULT = ROOT / "docs/fixtures/memory-os-operability/rate-limit-local-multiprocess-shared-store-results.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
REFS = (
    "contracts/operations/rate-limit-local-multiprocess-shared-store-contract.v1.json",
    "services/import-api/internal/ratelimit/shared_store_multiprocess_test.go",
    "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py",
    "scripts/reconcile-memory-os-rate-limit-local-multiprocess-shared-store.py",
    ".github/workflows/rate-limit-local-multiprocess-shared-store.yml",
)
EVIDENCE_PREFIX = "exact-source local multi-process rate-limit shared-store rehearsal"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def main() -> int:
    contract = load(CONTRACT)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    result_present = RESULT.is_file()
    readiness["contractDefined"] = True
    readiness["runnerImplemented"] = (ROOT / contract["runner"]).is_file()
    readiness["validatorImplemented"] = VALIDATOR.is_file()
    readiness["automaticWorkflowImplemented"] = (ROOT / contract["workflow"]).is_file()
    readiness["exactSourcePassCommitted"] = result_present
    readiness["localCrossProcessStoreSemanticsProven"] = result_present
    readiness["distributedSharedStoreImplemented"] = False
    readiness["productionEquivalentRuntimeEvidence"] = False
    readiness["productionReady"] = False
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-005"), None)
    require(isinstance(gate, dict), "OPS-P0-005 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-005 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(refs, list), "OPS-P0-005 authority arrays missing")
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(EVIDENCE_PREFIX))]
    if result_present:
        append_once(existing, (
            EVIDENCE_PREFIX + " proves two independent OS test clients consume one atomic shared budget through the canonical Store interface, a fresh client process cannot reset exhausted backend state, and a loopback shared-store outage maps to fail-closed store_unavailable; the broker is test-only MemoryStore-backed HTTP, so this is not a distributed production store, runtime-host restart, TLS/trusted-proxy deployment or production-equivalent evidence"
        ))
    else:
        append_once(existing, (
            EVIDENCE_PREFIX + " foundation is implemented but no exact-source PASS result is committed yet; no distributed-runtime claim is created"
        ))
    for ref in REFS:
        require((ROOT / ref).is_file(), f"local shared-store evidence ref missing: {ref}")
        append_once(refs, ref)
    if result_present:
        append_once(refs, str(RESULT.relative_to(ROOT)))

    joined = "\n".join(str(item).lower() for item in missing)
    for phrase in (
        "production-equivalent distributed enforcement",
        "trusted-proxy configuration",
        "load-calibrated limits",
        "completed emergency-mode",
        "production emergency control plane",
    ):
        require(phrase in joined, f"OPS-P0-005 production blocker must remain: {phrase}")
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Memory OS local multi-process shared-store reconciliation PASS")
    print(f"exact-source result committed: {str(result_present).lower()}")
    print(f"local cross-process store semantics proven: {str(result_present).lower()}")
    print("distributed shared store implemented: false")
    print("production-equivalent runtime evidence: false")
    print("OPS-P0-005: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE LIMIT LOCAL MULTIPROCESS SHARED STORE RECONCILE FAILED: {exc}")
        raise SystemExit(1)
