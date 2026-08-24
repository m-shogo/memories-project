#!/usr/bin/env python3
"""Prove the strict OPS-P0-007 snapshot validator cannot bypass canonical runtime authorities."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-ops-p0-007-admission-snapshot.py"
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical strict snapshot validator missing or symlinked")
    require(VALIDATOR.resolve(strict=True).relative_to(ROOT.resolve()) == VALIDATOR.relative_to(ROOT), "strict snapshot validator path drift")
    spec = importlib.util.spec_from_file_location("memory_os_ops_p0_007_snapshot_validator_authority_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load strict snapshot validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(module: Any, field: str, replacement: Any) -> None:
    original = getattr(module, field)
    snapshot_before = SNAPSHOT.read_bytes()
    status_before = STATUS.read_bytes()
    setattr(module, field, replacement)
    rejected = False
    try:
        module.main()
    except module.Fail:
        rejected = True
    finally:
        setattr(module, field, original)
    require(rejected, f"strict snapshot validator accepted substituted runtime authority: {field}")
    require(SNAPSHOT.read_bytes() == snapshot_before, f"{field} rejection mutated canonical strict snapshot")
    require(STATUS.read_bytes() == status_before, f"{field} rejection mutated canonical Production Status")


def main() -> int:
    module = load_module()
    baseline_snapshot = SNAPSHOT.read_bytes()
    baseline_status = STATUS.read_bytes()

    substitutions = (
        ("enforce_runtime_authority", lambda: None),
        ("require", lambda *_args: None),
        ("valid_count", lambda _value: True),
        ("load", lambda _path: {}),
        ("load_module", lambda *_args: object()),
        ("validate_registry", lambda *_args: []),
        ("load_helper", lambda: object()),
        ("SNAPSHOT", module.OBJECTIVES),
        ("ELIGIBILITY_HELPER", module.OBJECTIVE_WRITER),
        ("BLOCKER_HELPER", module.OBJECTIVE_WRITER),
        ("OBJECTIVES", module.DRILL_REQUESTS),
        ("DRILL_REQUESTS", module.OBJECTIVES),
        ("GEN_EVIDENCE", module.TYPED),
        ("TYPED", module.GEN_EVIDENCE),
        ("STATUS", module.OBJECTIVES),
        ("OBJECTIVE_WRITER", module.DRILL_REQUEST_WRITER),
        ("DRILL_REQUEST_WRITER", module.OBJECTIVE_WRITER),
        ("GEN_EVIDENCE_WRITER", module.TYPED_WRITER),
        ("TYPED_WRITER", module.GEN_EVIDENCE_WRITER),
        ("SNAPSHOT_FIELDS", set()),
        ("DOWNSTREAM_REQUIREMENTS", []),
        ("NEXT_ACTIONS", {}),
    )
    for field, replacement in substitutions:
        expect_rejected(module, field, replacement)

    module.enforce_runtime_authority()
    require(SNAPSHOT.read_bytes() == baseline_snapshot, "runtime authority probes mutated canonical strict snapshot")
    require(STATUS.read_bytes() == baseline_status, "runtime authority probes mutated canonical Production Status")
    json.loads(baseline_snapshot.decode("utf-8"))
    json.loads(baseline_status.decode("utf-8"))

    print("Memory OS OPS-P0-007 strict snapshot validator authority negative PASS")
    print(f"runtime authority substitutions rejected: {len(substitutions)}")
    print("validator execution guard substitution accepted: false")
    print("validator helper substitution accepted: false")
    print("validator data/executable authority substitution accepted: false")
    print("validator projection-shape substitution accepted: false")
    print("rejected probes mutated canonical snapshot/status: false")
    print("production evidence created: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError, json.JSONDecodeError) as exc:
        print(f"OPS-P0-007 SNAPSHOT VALIDATOR AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
