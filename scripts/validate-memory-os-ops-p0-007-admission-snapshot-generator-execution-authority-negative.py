#!/usr/bin/env python3
"""Prove the strict OPS-P0-007 snapshot generator cannot bypass canonical execution helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    require(GENERATOR.is_file() and not GENERATOR.is_symlink(), "canonical strict snapshot generator missing or symlinked")
    require(GENERATOR.resolve(strict=True).relative_to(ROOT.resolve()) == GENERATOR.relative_to(ROOT), "strict snapshot generator path drift")
    spec = importlib.util.spec_from_file_location("memory_os_ops_p0_007_snapshot_generator_execution_authority_negative", GENERATOR)
    require(spec is not None and spec.loader is not None, "cannot load strict snapshot generator")
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
    except SystemExit as exc:
        require(exc.code not in (None, 0), f"{field} substitution produced successful SystemExit")
        rejected = True
    finally:
        setattr(module, field, original)
    require(rejected, f"strict snapshot generator accepted substituted execution authority: {field}")
    require(SNAPSHOT.read_bytes() == snapshot_before, f"{field} rejection mutated canonical strict snapshot")
    require(STATUS.read_bytes() == status_before, f"{field} rejection mutated canonical Production Status")


def main() -> int:
    module = load_module()
    baseline_snapshot = SNAPSHOT.read_bytes()
    baseline_status = STATUS.read_bytes()

    substitutions = (
        ("enforce_execution_authority", lambda: None),
        ("require_exact_repo_file", lambda *_args: None),
        ("enforce_runtime_authorities", lambda: None),
        ("atomic_write_text", lambda *_args: None),
        ("load", lambda _path: {}),
        ("load_module", lambda *_args: object()),
        ("validate_registry", lambda *_args: []),
        ("run_canonical_validator", lambda *_args: None),
        ("run_full_admission_validators", lambda: None),
        ("validate_generated_snapshot", lambda: None),
        ("load_helper", lambda: object()),
    )
    for field, replacement in substitutions:
        expect_rejected(module, field, replacement)

    module.enforce_execution_authority()
    require(SNAPSHOT.read_bytes() == baseline_snapshot, "generator execution authority probes mutated canonical strict snapshot")
    require(STATUS.read_bytes() == baseline_status, "generator execution authority probes mutated canonical Production Status")
    json.loads(baseline_snapshot.decode("utf-8"))
    json.loads(baseline_status.decode("utf-8"))

    print("Memory OS OPS-P0-007 strict snapshot generator execution authority negative PASS")
    print(f"execution helper substitutions rejected: {len(substitutions)}")
    print("full admission validator no-op substitution accepted: false")
    print("post-write validator no-op substitution accepted: false")
    print("atomic publication helper substitution accepted: false")
    print("rejected probes mutated canonical snapshot/status: false")
    print("production evidence created: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError, json.JSONDecodeError) as exc:
        print(f"OPS-P0-007 SNAPSHOT GENERATOR EXECUTION AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
