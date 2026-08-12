#!/usr/bin/env python3
"""Reconcile drill-request binding to semantic environment-generation eligibility."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-generation-eligibility-binding-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
DRILL_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
ELIGIBILITY_HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    try:
        original_contract_text = CONTRACT.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {CONTRACT.relative_to(ROOT)}: {exc}") from exc
    contract = load(CONTRACT)
    registry = load(DRILL_REGISTRY)
    writer = load_module(DRILL_WRITER, "memory_os_drill_writer_binding_reconcile")
    helper = load_module(ELIGIBILITY_HELPER, "memory_os_generation_eligibility_binding_reconcile")
    try:
        requests = writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"drill request append-only authority invalid: {exc}") from exc
    eligibility = helper.derive()
    pair_count = eligibility["eligibleDirectedPairCount"]
    request_count = registry["registeredRequestCount"]
    current_count = registry["currentExecutableRequestCount"]
    historical_count = len(requests)

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "binding currentBoundary missing")
    boundary["eligibleDirectedRestorePairCount"] = pair_count
    boundary["reviewedDrillRequestCount"] = request_count
    boundary["currentExecutableDrillRequestCount"] = current_count
    boundary["historicalAuditableRequestCount"] = historical_count
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"

    try:
        CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        require(completed.returncode == 0, f"post-reconcile binding validator failed:\n{completed.stdout[-9000:]}{completed.stderr[-9000:]}")
    except Exception:
        try:
            CONTRACT.write_text(original_contract_text, encoding="utf-8")
        except OSError as restore_exc:
            raise Fail(f"drill generation eligibility binding rollback failed: {restore_exc}") from restore_exc
        raise

    print("Memory OS drill request semantic generation binding reconciliation PASS")
    print(f"eligible directed restore pairs: {pair_count}")
    print(f"reviewed/current drill requests: {request_count}/{current_count}")
    print(f"historical auditable requests: {historical_count}")
    print("failed post-validation leaves semantic binding authority mutation behind: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL REQUEST GENERATION ELIGIBILITY BINDING RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
