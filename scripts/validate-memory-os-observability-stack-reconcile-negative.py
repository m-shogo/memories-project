#!/usr/bin/env python3
"""Reject corrupt observability-stack authority before reconcile mutation."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/observability-stack-deployment-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-observability-stack-deployment.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-observability-stack-deployment.py"


def load_writer():
    spec = importlib.util.spec_from_file_location("observability_stack_writer", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load observability stack writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_writer_rejected(writer, registry, label: str) -> None:
    try:
        writer.validate_registry_for_append(registry, validate_rows=False)
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted corrupt observability stack registry: {label}")


def main() -> int:
    writer = load_writer()
    registry_bytes = REGISTRY.read_bytes()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    registry = json.loads(registry_bytes.decode("utf-8"))

    cases = []
    candidate = copy.deepcopy(registry)
    candidate["admittedStackCount"] = True
    cases.append(("boolean admitted count", candidate))
    candidate = copy.deepcopy(registry)
    candidate["appendOnly"] = False
    cases.append(("append-only disabled", candidate))
    candidate = copy.deepcopy(registry)
    candidate["productionReady"] = True
    cases.append(("production ready escalation", candidate))
    candidate = copy.deepcopy(registry)
    candidate["schemaVersion"] = "memory-os-observability-stack-deployment-registry.v999"
    cases.append(("registry schema drift", candidate))

    for label, candidate in cases:
        expect_writer_rejected(writer, candidate, label)

    try:
        corrupted = copy.deepcopy(registry)
        corrupted["admittedStackCount"] = True
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
            raise RuntimeError("reconciler accepted corrupt observability stack registry")
        if CONTRACT.read_bytes() != contract_bytes:
            raise RuntimeError("rejected reconcile mutated observability stack contract")
        if STATUS.read_bytes() != status_bytes:
            raise RuntimeError("rejected reconcile mutated production operability status")
    finally:
        REGISTRY.write_bytes(registry_bytes)
        CONTRACT.write_bytes(contract_bytes)
        STATUS.write_bytes(status_bytes)

    print("PASS: observability stack registry corruption is rejected without mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
