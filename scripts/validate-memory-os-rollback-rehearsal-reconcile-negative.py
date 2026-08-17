#!/usr/bin/env python3
"""Prove rollback rehearsal reconcile refuses corrupt upstream authority before writes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
RECONCILER = ROOT / "scripts/reconcile-memory-os-rollback-rehearsal-gate.py"


def run_reconciler() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RECONCILER)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def mutate_registry(value: dict[str, Any], case: str) -> None:
    if case == "registryClass":
        value["registryClass"] = "OTHER"
    elif case == "appendOnly":
        value["appendOnly"] = False
    elif case == "booleanCount":
        value["rehearsalRequestCount"] = False
    elif case == "productionEvidence":
        value["productionEvidence"] = True
    else:
        raise RuntimeError(f"unknown case: {case}")


def main() -> int:
    registry_bytes = REGISTRY_PATH.read_bytes()
    status_bytes = STATUS_PATH.read_bytes()
    for case in ("registryClass", "appendOnly", "booleanCount", "productionEvidence"):
        try:
            registry = json.loads(registry_bytes.decode("utf-8"))
            if not isinstance(registry, dict):
                raise RuntimeError("rollback registry root is not an object")
            mutate_registry(registry, case)
            REGISTRY_PATH.write_text(
                json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            completed = run_reconciler()
            if completed.returncode == 0:
                raise RuntimeError(f"reconciler accepted corrupt registry: {case}")
            if STATUS_PATH.read_bytes() != status_bytes:
                raise RuntimeError(f"reconciler mutated production status on rejection: {case}")
        finally:
            REGISTRY_PATH.write_bytes(registry_bytes)
            STATUS_PATH.write_bytes(status_bytes)

    print("PASS: rollback rehearsal reconcile rejects corrupt registry before status writes")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ROLLBACK REHEARSAL RECONCILE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
