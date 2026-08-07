#!/usr/bin/env python3
"""Register immutable environment-generation admission without claiming any environment exists."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "production-equivalent environment generation admission is machine-readable and append-only: load, restore, failure-drill and review evidence "
    "must bind an immutable generationId plus environment/dependency/evidence/material-delta hashes and source commit; cross-generation reuse, unknown "
    "generations and mutable latest aliases are forbidden, while the current registry remains empty and creates no production-equivalent claim"
)
REFS = (
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    "scripts/validate-memory-os-production-equivalent-environment-generation.py",
    ".github/workflows/production-equivalent-environment-generation.yml",
)


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
    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    boundary = contract.get("currentBoundary", {})
    require(registry.get("registeredGenerationCount") == 0, "environment generation unexpectedly registered")
    require(boundary.get("registeredGenerationCount") == 0, "generation boundary unexpectedly nonzero")
    require(boundary.get("currentGenerationId") is None, "current generation must remain null")
    for key in ("environmentProvisioned", "environmentValidated", "productionEquivalentDependencies", "productionEvidence", "productionReady"):
        require(boundary.get(key) is False, f"generation foundation cannot enable {key}")
    require(boundary.get("productionDecision") == "NO_GO", "generation foundation cannot change production decision")

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-006"), None)
    require(isinstance(gate, dict), "OPS-P0-006 missing")
    require(gate.get("status") == "PARTIAL" and gate.get("blocking") is True, "OPS-P0-006 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    require(isinstance(existing, list) and isinstance(refs, list) and isinstance(missing, list), "OPS-P0-006 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        require((ROOT / ref).is_file(), f"generation evidence ref missing: {ref}")
        append_once(refs, ref)

    joined = "\n".join(str(item).lower() for item in missing)
    for term in ("production-equivalent dependency behavior", "production topology"):
        require(term in joined, f"actual production-equivalent blocker must remain: {term}")

    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Memory OS production-equivalent generation status reconciliation PASS")
    print("generation registry entries: 0")
    print("cross-generation evidence reuse: forbidden")
    print("production-equivalent environment: not provisioned")
    print("OPS-P0-006: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION STATUS FAILED: {exc}")
        raise SystemExit(1)
