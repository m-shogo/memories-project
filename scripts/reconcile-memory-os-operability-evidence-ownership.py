#!/usr/bin/env python3
"""Mark evidence-ownership validation infrastructure implemented after validation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/operability-evidence-ownership-contract.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-operability-evidence-ownership.py"
WORKFLOW = ROOT / ".github/workflows/operability-evidence-ownership.yml"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"root must be object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    if not VALIDATOR.is_file() or not WORKFLOW.is_file():
        raise SystemExit("ownership validator/workflow missing")
    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
    contract = load(CONTRACT)
    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        raise SystemExit("ownership readiness missing")
    readiness["validatorImplemented"] = True
    readiness["automaticWorkflowImplemented"] = True
    readiness["productionReady"] = False
    if contract.get("productionDecision") != "NO_GO":
        raise SystemExit("ownership contract cannot change production decision")
    CONTRACT.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
    print("Memory OS operability evidence ownership readiness reconciliation PASS")
    print("validator implemented: true")
    print("automatic workflow implemented: true")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
