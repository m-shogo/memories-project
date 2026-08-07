#!/usr/bin/env python3
"""Register backup/restore generation-binding foundation while keeping production restore blocked."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "future production-equivalent restore promotion is generation-bound: backup artifact/manifest hashes, source environment generation/manifest, "
    "source commit, restore target generation/manifest and restore evidence bundle must match append-only registered generations; legacy local restore "
    "evidence cannot be relabeled and cross-generation restores require material-delta review"
)
REFS = (
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "scripts/validate-memory-os-backup-restore-generation-binding.py",
    ".github/workflows/backup-restore-generation-binding.yml",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"root must be object: {path.relative_to(ROOT)}")
    return value


def append_once(items: list[Any], value: str) -> None:
    if value not in items:
        items.append(value)


def main() -> int:
    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
    contract = load(CONTRACT)
    boundary = contract.get("currentBoundary", {})
    if boundary.get("registeredProductionEquivalentGenerationCount") != 0:
        raise SystemExit("production-equivalent generation unexpectedly registered")
    if boundary.get("generationBoundBackupCount") != 0 or boundary.get("generationBoundRestoreCount") != 0:
        raise SystemExit("generation-bound restore evidence unexpectedly exists")
    for key in ("productionEquivalentRestoreEvidence", "productionEvidence", "productionReady"):
        if boundary.get(key) is not False:
            raise SystemExit(f"restore foundation cannot enable {key}")
    if boundary.get("productionDecision") != "NO_GO":
        raise SystemExit("restore foundation cannot change production decision")

    status = load(STATUS)
    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("productionDecision must remain NO_GO")
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-003"), None)
    if not isinstance(gate, dict):
        raise SystemExit("OPS-P0-003 missing")
    if gate.get("status") != "PARTIAL" or gate.get("blocking") is not True:
        raise SystemExit("OPS-P0-003 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    refs = gate.get("evidenceRefs")
    missing = gate.get("missingEvidence")
    if not isinstance(existing, list) or not isinstance(refs, list) or not isinstance(missing, list):
        raise SystemExit("OPS-P0-003 authority arrays missing")
    append_once(existing, EVIDENCE)
    for ref in REFS:
        if not (ROOT / ref).is_file():
            raise SystemExit(f"missing restore-generation ref: {ref}")
        append_once(refs, ref)
    joined = "\n".join(str(item).lower() for item in missing)
    for term in ("production-shaped restore", "production-equivalent", "independent review"):
        if term not in joined:
            raise SystemExit(f"actual restore blocker must remain: {term}")

    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Memory OS backup/restore generation status reconciliation PASS")
    print("generation binding foundation: registered")
    print("production-equivalent restore evidence: false")
    print("OPS-P0-003: PARTIAL")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
