#!/usr/bin/env python3
"""Reject corrupt contact-routing authority before append/reconcile mutation."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/incident-contact-routing-admission-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/incident-contact-routing-admission-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-incident-contact-routing.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-incident-contact-routing.py"


def load_writer():
    spec = importlib.util.spec_from_file_location("incident_contact_routing_writer", WRITER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load contact routing writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_writer_rejected(writer, registry, label: str) -> None:
    try:
        writer.validate_registry_for_append(registry, validate_rows=False)
    except writer.Fail:
        return
    raise RuntimeError(f"writer accepted corrupt contact routing registry: {label}")


def main() -> int:
    writer = load_writer()
    registry_bytes = REGISTRY.read_bytes()
    contract_bytes = CONTRACT.read_bytes()
    status_bytes = STATUS.read_bytes()
    registry = json.loads(registry_bytes.decode("utf-8"))

    cases = []
    candidate = copy.deepcopy(registry)
    candidate["admittedRoutingCount"] = True
    cases.append(("boolean admitted count", candidate))
    candidate = copy.deepcopy(registry)
    candidate["appendOnly"] = False
    cases.append(("append-only disabled", candidate))
    candidate = copy.deepcopy(registry)
    candidate["productionReady"] = True
    cases.append(("production ready escalation", candidate))
    candidate = copy.deepcopy(registry)
    candidate["schemaVersion"] = "memory-os-incident-contact-routing-admission-registry.v999"
    cases.append(("registry schema drift", candidate))

    for label, candidate in cases:
        expect_writer_rejected(writer, candidate, label)

    try:
        corrupted = copy.deepcopy(registry)
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

    if REGISTRY.read_bytes() != registry_bytes:
        raise RuntimeError("negative validation failed to restore contact routing registry")
    print("PASS: contact routing writer/reconciler reject registry corruption without mutation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
