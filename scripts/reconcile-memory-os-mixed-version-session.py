#!/usr/bin/env python3
"""Register exact-source mixed-version session evidence without over-promoting compatibility."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json"
CONTRACT = ROOT / "contracts/operations/mixed-version-session-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "pinned old/current Import API two-process compatibility drill proving sessions issued by either version are resolved by the other against the complete current PostgreSQL schema while account-epoch fencing remains enforced",
)
REFS = (
    "contracts/operations/mixed-version-session-contract.v1.json",
    "scripts/run-memory-os-mixed-version-session-drill.sh",
    "scripts/validate-memory-os-mixed-version-session.py",
    "scripts/reconcile-memory-os-mixed-version-session.py",
    "docs/fixtures/memory-os-operability/mixed-version-session-results.sample.v1.json",
    ".github/workflows/mixed-version-session.yml",
)
PRECISE_GAP = (
    "full old/current backend mixed-version route, mutation, persisted-state and rollback coverage beyond the proven session/authentication slice"
)


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"root must be object: {path}")
    return value


def append_unique(values: list[str], additions: tuple[str, ...]) -> list[str]:
    result = list(values)
    for item in additions:
        if item not in result:
            result.append(item)
    return result


def main() -> int:
    result = load(RESULT)
    contract = load(CONTRACT)
    expected = os.getenv("EXPECTED_COMMIT_SHA")
    if result.get("schemaVersion") != contract.get("resultsSchemaVersion"):
        raise RuntimeError("mixed-version result schema mismatch")
    if result.get("result") != "PASS" or result.get("integrityResult") != "PASS":
        raise RuntimeError("mixed-version result is not PASS/PASS")
    if result.get("oldBackendCommitSha") != contract.get("oldBackendCommitSha"):
        raise RuntimeError("old backend SHA mismatch")
    if expected and result.get("commitSha") != expected:
        raise RuntimeError("result is not bound to the expected source SHA")
    environment = result.get("environment", {})
    if environment.get("productionEvidence") is not False or environment.get("containsSecrets") is not False:
        raise RuntimeError("mixed-version evidence boundary changed")

    status = load(STATUS)
    if status.get("productionDecision") != "NO_GO":
        raise RuntimeError("reconcile cannot change productionDecision")
    areas = status.get("areas")
    if not isinstance(areas, list):
        raise RuntimeError("status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-008"]
    if len(matches) != 1:
        raise RuntimeError("OPS-P0-008 must exist exactly once")
    area = matches[0]
    if area.get("status") != "PARTIAL":
        raise RuntimeError("session slice cannot reconcile a non-PARTIAL OPS-P0-008")

    existing = area.get("existingEvidence")
    missing = area.get("missingEvidence")
    refs = area.get("evidenceRefs")
    if not all(isinstance(value, list) for value in (existing, missing, refs)):
        raise RuntimeError("OPS-P0-008 evidence fields must be lists")
    area["existingEvidence"] = append_unique(existing, EVIDENCE)
    area["evidenceRefs"] = append_unique(refs, REFS)

    filtered = [
        item for item in missing
        if item != "old/current backend mixed-version executable tests against an expanded schema"
    ]
    if PRECISE_GAP not in filtered:
        filtered.append(PRECISE_GAP)
    # The slice must not erase the broad remaining compatibility classes.
    for phrase in ("persisted-state", "parser artifact", "client/server", "PostgreSQL"):
        if not any(phrase in item for item in filtered):
            raise RuntimeError(f"required compatibility gap disappeared: {phrase}")
    area["missingEvidence"] = filtered

    STATUS.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print("Mixed-version session evidence reconciled without readiness promotion")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"MIXED-VERSION SESSION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
