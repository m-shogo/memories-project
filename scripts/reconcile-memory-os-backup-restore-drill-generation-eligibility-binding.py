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
    except (FileNotFoundError, json.JSONDecodeError) as exc:
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
    contract = load(CONTRACT)
    registry = load(DRILL_REGISTRY)
    writer = load_module(DRILL_WRITER, "memory_os_drill_writer_binding_reconcile")
    helper = load_module(ELIGIBILITY_HELPER, "memory_os_generation_eligibility_binding_reconcile")
    eligibility = helper.derive()
    pair_count = eligibility["eligibleDirectedPairCount"]

    requests = registry.get("requests")
    request_count = registry.get("registeredRequestCount")
    require(isinstance(requests, list) and isinstance(request_count, int) and request_count == len(requests), "drill request registry count drift")
    historical_count = 0
    current_count = 0
    for row in requests:
        require(isinstance(row, dict), "drill request row invalid")
        try:
            writer.validate_request(row, require_current=False)
        except Exception as exc:
            raise Fail(f"historical request lost structural audit validity: {row.get('requestId')}: {exc}") from exc
        historical_count += 1
        if writer.request_currently_executable(row):
            current_count += 1
    require(registry.get("currentExecutableRequestCount") == current_count, "drill request current count drift")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "binding currentBoundary missing")
    boundary["eligibleDirectedRestorePairCount"] = pair_count
    boundary["reviewedDrillRequestCount"] = request_count
    boundary["currentExecutableDrillRequestCount"] = current_count
    boundary["historicalAuditableRequestCount"] = historical_count
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"post-reconcile binding validator failed:\n{completed.stdout[-9000:]}{completed.stderr[-9000:]}")
    print("Memory OS drill request semantic generation binding reconciliation PASS")
    print(f"eligible directed restore pairs: {pair_count}")
    print(f"reviewed/current drill requests: {request_count}/{current_count}")
    print(f"historical auditable requests: {historical_count}")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL REQUEST GENERATION ELIGIBILITY BINDING RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
