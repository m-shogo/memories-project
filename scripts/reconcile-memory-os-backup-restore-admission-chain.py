#!/usr/bin/env python3
"""Reconcile bounded counters for the end-to-end backup/restore admission chain."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TYPED_REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-admission-chain.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


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


def load_generation_writer():
    spec = importlib.util.spec_from_file_location("memory_os_generation_writer_admission_chain_reconcile", GEN_WRITER)
    require(spec is not None and spec.loader is not None, "cannot load generation recovery writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    contract = load(CONTRACT)
    drill_registry = load(DRILL_REGISTRY)
    gen_registry = load(GEN_REGISTRY)
    typed_registry = load(TYPED_REGISTRY)
    status = load(STATUS)
    gen_writer = load_generation_writer()

    drill_rows = drill_registry.get("requests")
    drill_count = drill_registry.get("registeredRequestCount")
    current_drill_count = drill_registry.get("currentExecutableRequestCount")
    require(isinstance(drill_rows, list) and isinstance(drill_count, int) and drill_count == len(drill_rows), "drill request registry count drift")
    require(isinstance(current_drill_count, int) and 0 <= current_drill_count <= drill_count, "current drill request count invalid")

    gen_rows = gen_registry.get("records")
    gen_count = gen_registry.get("registeredEvidenceCount")
    bound_count = gen_registry.get("drillRequestBoundEvidenceCount")
    require(isinstance(gen_rows, list) and isinstance(gen_count, int) and gen_count == len(gen_rows), "generation evidence count drift")
    require(isinstance(bound_count, int) and bound_count == gen_count, "every generation evidence row must be drill-request-bound")
    for row in gen_rows:
        gen_writer.validate_record(row, require_current_drill_request=False)
    candidate_count = sum(1 for row in gen_rows if gen_writer.candidate(row))
    require(gen_registry.get("productionEquivalentRecoveryCandidateCount") == candidate_count, "generation candidate count drift")

    typed_rows = typed_registry.get("records")
    typed_complete_count = typed_registry.get("completeRecordCount")
    typed_covered_count = typed_registry.get("candidateCoveredCount")
    require(isinstance(typed_rows, list) and isinstance(typed_complete_count, int) and isinstance(typed_covered_count, int), "typed registry counters invalid")
    require(0 <= typed_covered_count <= typed_complete_count <= len(typed_rows), "typed registry count ordering invalid")
    require(typed_covered_count == candidate_count, "typed candidate coverage must equal final candidate count")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "chain currentBoundary missing")
    boundary["reviewedDrillRequestCount"] = drill_count
    boundary["currentExecutableDrillRequestCount"] = current_drill_count
    boundary["generationEvidenceCount"] = gen_count
    boundary["drillRequestBoundGenerationEvidenceCount"] = bound_count
    boundary["completeTypedNonResurrectionRecordCount"] = typed_complete_count
    boundary["finalProductionEquivalentRecoveryCandidateCount"] = candidate_count
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    require(status.get("productionDecision") == "NO_GO", "chain reconcile cannot change production decision")
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and gate.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    missing = gate.get("missingEvidence")
    require(isinstance(missing, list) and len(missing) == 6, "canonical OPS-P0-007 six-blocker boundary drift")

    completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"post-reconcile admission-chain validator failed:\n{completed.stdout[-6000:]}{completed.stderr[-6000:]}")

    print("Memory OS backup/restore admission chain reconciliation PASS")
    print(f"reviewed/current drill requests: {drill_count}/{current_drill_count}")
    print(f"generation/drill-bound evidence: {gen_count}/{bound_count}")
    print(f"complete typed records/final candidates: {typed_complete_count}/{candidate_count}")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE ADMISSION CHAIN RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
