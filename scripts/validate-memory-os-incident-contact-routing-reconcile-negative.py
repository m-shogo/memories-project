#!/usr/bin/env python3
"""Reject corrupt contact-routing authority before reconcile mutates derived files."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/incident-contact-routing-admission-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/incident-contact-routing-admission-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
RECONCILER = ROOT / "scripts/reconcile-memory-os-incident-contact-routing.py"


def main() -> int:
    registry_bytes = REGISTRY.read_bytes()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    registry = json.loads(registry_bytes.decode("utf-8"))

    try:
        corrupted = dict(registry)
        corrupted["admittedRoutingCount"] = True
        REGISTRY.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")

        completed = subprocess.run(
            ["python", str(RECONCILER)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode == 0:
            raise RuntimeError("reconciler accepted corrupt contact routing registry")
        if CONTRACT.read_bytes() != contract_bytes:
            raise RuntimeError("rejected reconcile mutated contact routing contract")
        if STATUS.read_bytes() != status_bytes:
            raise RuntimeError("rejected reconcile mutated production operability status")
    finally:
        REGISTRY.write_bytes(registry_bytes)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)

    print("PASS: corrupt contact routing registry is rejected before derived authority mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
