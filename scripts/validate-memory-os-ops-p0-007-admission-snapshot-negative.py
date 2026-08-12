#!/usr/bin/env python3
"""Prove the standalone OPS-P0-007 snapshot validator rejects corrupt authorities."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-ops-p0-007-admission-snapshot.py"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
REQUESTS = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
GENERATION = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
TYPED = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Fail(f"expected object: {path.relative_to(ROOT)}")
    return value


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run_validator(expect_success: bool, label: str) -> None:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if expect_success:
        if proc.returncode != 0:
            raise Fail(f"{label}: baseline validator failed: {proc.stderr or proc.stdout}")
        return
    if proc.returncode != 1:
        raise Fail(f"{label}: expected fail-closed exit 1, got {proc.returncode}: {proc.stderr or proc.stdout}")
    if "OPS-P0-007 ADMISSION SNAPSHOT FAILED:" not in proc.stderr:
        raise Fail(f"{label}: rejection did not come from canonical fail-closed boundary: {proc.stderr or proc.stdout}")
    if "Traceback (most recent call last)" in proc.stderr:
        raise Fail(f"{label}: rejection surfaced an implementation exception instead of a controlled failure")


def mutate_field(field: str, value: Any) -> Callable[[dict[str, Any]], None]:
    def apply(registry: dict[str, Any]) -> None:
        registry[field] = value
    return apply


def mutate_ops7_missing(reorder: bool) -> Callable[[dict[str, Any]], None]:
    def apply(status: dict[str, Any]) -> None:
        areas = status.get("areas")
        if not isinstance(areas, list):
            raise Fail("status areas missing")
        ops7 = next((row for row in areas if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
        if not isinstance(ops7, dict) or not isinstance(ops7.get("missingEvidence"), list):
            raise Fail("OPS-P0-007 missingEvidence missing")
        if reorder:
            ops7["missingEvidence"] = list(reversed(ops7["missingEvidence"]))
        else:
            replacement = list(ops7["missingEvidence"])
            replacement[0] = "fabricated replacement blocker with unchanged list length"
            ops7["missingEvidence"] = replacement
    return apply


def main() -> int:
    originals = {
        OBJECTIVES: OBJECTIVES.read_bytes(),
        REQUESTS: REQUESTS.read_bytes(),
        GENERATION: GENERATION.read_bytes(),
        TYPED: TYPED.read_bytes(),
        STATUS: STATUS.read_bytes(),
    }
    cases: list[tuple[str, Path, Callable[[dict[str, Any]], None]]] = [
        ("objective boolean aggregate count", OBJECTIVES, mutate_field("approvedObjectiveCount", True)),
        ("objective append-only boundary", OBJECTIVES, mutate_field("appendOnly", False)),
        ("objective schema boundary", OBJECTIVES, mutate_field("schemaVersion", "memory-os-recovery-objectives-registry.corrupt")),
        ("objective production evidence boundary", OBJECTIVES, mutate_field("productionEvidence", True)),
        ("objective production readiness boundary", OBJECTIVES, mutate_field("productionReady", True)),
        ("drill boolean aggregate count", REQUESTS, mutate_field("registeredRequestCount", True)),
        ("drill append-only boundary", REQUESTS, mutate_field("appendOnly", False)),
        ("drill production evidence boundary", REQUESTS, mutate_field("productionEvidence", True)),
        ("generation boolean aggregate count", GENERATION, mutate_field("registeredEvidenceCount", True)),
        ("generation append-only boundary", GENERATION, mutate_field("appendOnly", False)),
        ("generation production readiness boundary", GENERATION, mutate_field("productionReady", True)),
        ("typed boolean aggregate count", TYPED, mutate_field("completeRecordCount", True)),
        ("typed append-only boundary", TYPED, mutate_field("appendOnly", False)),
        ("typed production evidence boundary", TYPED, mutate_field("productionEvidence", True)),
        ("canonical blocker replacement with unchanged count", STATUS, mutate_ops7_missing(False)),
        ("canonical blocker ordering drift", STATUS, mutate_ops7_missing(True)),
        ("production decision promotion", STATUS, mutate_field("productionDecision", "GO")),
    ]

    try:
        run_validator(True, "clean baseline")
        for label, path, mutate in cases:
            for restore_path, payload in originals.items():
                restore_path.write_bytes(payload)
            authority = copy.deepcopy(load(path))
            mutate(authority)
            write(path, authority)
            run_validator(False, label)
        for restore_path, payload in originals.items():
            restore_path.write_bytes(payload)
        run_validator(True, "restored baseline")
    finally:
        for path, payload in originals.items():
            path.write_bytes(payload)

    for path, payload in originals.items():
        if path.read_bytes() != payload:
            raise Fail(f"negative suite mutated canonical authority: {path.relative_to(ROOT)}")

    print("Memory OS OPS-P0-007 strict admission snapshot negative validation PASS")
    print(f"controlled authority corruption cases rejected: {len(cases)}")
    print("canonical authority files preserved byte-for-byte: true")
    print("canonical six-blocker content and ordering preserved: true")
    print("production evidence/readiness/decision promotion rejected: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, json.JSONDecodeError, OSError) as exc:
        print(f"OPS-P0-007 ADMISSION SNAPSHOT NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
