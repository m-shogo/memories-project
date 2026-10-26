#!/usr/bin/env python3
"""Prove deletion-under-load direct reconcile pins canonical source authorities."""

from __future__ import annotations

import copy
import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-under-load-status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("deletion_load_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load deletion-under-load reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)



def verify_deletion_numeric_boundary() -> None:
    """Reject nonfinite deletion-load JSON and overflow using the actual validator."""
    validator_path = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
    spec = importlib.util.spec_from_file_location("deletion_load_numeric_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("deletion load numeric validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    if validator.positive_number(1.25, "synthetic-positive") != 1.25:
        raise RuntimeError("deletion load numeric positive control failed")
    for label, bad in (
        ("Infinity", float("inf")),
        ("NaN", float("nan")),
        ("overflow integer", 10 ** 500),
    ):
        try:
            validator.positive_number(bad, "synthetic-negative")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"deletion load numeric validator accepted {label}")
    with tempfile.TemporaryDirectory(prefix=".deletion-load-numeric-negative-", dir=ROOT) as tmp:
        path = Path(tmp) / "synthetic.json"
        for label, raw in (("JSON Infinity", '{"value": Infinity}'),
                           ("JSON float overflow", '{"value": 1e999}')):
            path.write_text(raw, encoding="utf-8")
            try:
                validator.load(path)
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError(f"deletion load parser accepted {label}")
    print("PASS: deletion load numeric positive and 5 nonfinite negatives")



def verify_deletion_timestamp_semantics() -> None:
    """Exercise the actual deletion-load UTC validator with positive and negative cases."""
    validator_path = ROOT / "scripts/validate-memory-os-deletion-under-load.py"
    spec = importlib.util.spec_from_file_location("deletion_load_timestamp_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("deletion load timestamp validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical = validator.load(ROOT / "docs/fixtures/memory-os-operability/deletion-under-load-results.sample.v1.json")
    validator.validate_deletion_timestamps(copy.deepcopy(canonical))
    cases = (
        ("impossible date", ("scenario", "startedAt"), "2026-02-30T22:17:18Z"),
        ("timezone offset", ("scenario", "startedAt"), "2026-09-23T22:17:18+00:00"),
        ("missing seconds", ("scenario", "startedAt"), "2026-09-23T22:17Z"),
        ("fraction without digits", ("scenario", "startedAt"), "2026-09-23T22:17:18.Z"),
        ("nonstring", ("scenario", "startedAt"), None),
        ("completion before start", ("scenario", "completedAt"), "2026-09-23T22:17:17Z"),
        ("generation before completion", ("generatedAt",), "2026-09-23T22:17:18Z"),
    )
    for label, keys, value in cases:
        mutated = copy.deepcopy(canonical)
        cursor = mutated
        for key in keys[:-1]:
            cursor = cursor[key]
        cursor[keys[-1]] = value
        try:
            validator.validate_deletion_timestamps(mutated)
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"deletion load timestamp validator accepted {label}")
    print("PASS: deletion load UTC positive and 7 timestamp negatives")


def main() -> int:
    module = load_module()
    verify_deletion_numeric_boundary()
    verify_deletion_timestamp_semantics()
    substitutions = {
        "CONTRACT_PATH": module.LOAD_PATH,
        "LOAD_PATH": module.CONTRACT_PATH,
        "STATUS_PATH": module.LOAD_PATH,
        "RESULT_PATH": module.CONTRACT_PATH,
        "DELETION_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.DELETION_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    print("PASS: deletion-under-load direct reconcile source authorities are canonical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
