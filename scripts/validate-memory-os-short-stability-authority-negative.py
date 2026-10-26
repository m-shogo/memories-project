#!/usr/bin/env python3
"""Prove short stability direct reconcile pins canonical source authorities."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-short-stability-status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("short_stability_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load short stability reconciler")
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



def verify_short_numeric_boundary() -> None:
    """Use the actual stability validator to reject nonfinite numeric input."""
    validator_path = ROOT / "scripts/validate-memory-os-short-stability-sample.py"
    spec = importlib.util.spec_from_file_location("short_stability_numeric_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("short stability numeric validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    if validator.finite_number(1.25, "synthetic-positive") != 1.25:
        raise RuntimeError("short stability numeric positive control failed")
    for label, bad in (
        ("Infinity", float("inf")),
        ("NaN", float("nan")),
        ("overflow integer", 10 ** 500),
    ):
        try:
            validator.finite_number(bad, "synthetic-negative")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"short stability accepted {label}")
    with tempfile.TemporaryDirectory(prefix=".short-stability-numeric-negative-", dir=ROOT) as tmp:
        path = Path(tmp) / "synthetic.json"
        for label, raw in (("JSON Infinity", '{"value": Infinity}'),
                           ("JSON float overflow", '{"value": 1e999}')):
            path.write_text(raw, encoding="utf-8")
            try:
                validator.load(path)
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError(f"short stability parser accepted {label}")
    print("PASS: short stability finite numeric positive and 5 negatives")



def verify_short_timestamp_semantics() -> None:
    """Prove UTC chronology for scenario and every observation using canonical validator."""
    validator_path = ROOT / "scripts/validate-memory-os-short-stability-sample.py"
    spec = importlib.util.spec_from_file_location("short_stability_timestamp_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("short stability timestamp validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical = validator.load(ROOT / "docs/fixtures/memory-os-operability/short-stability-sample-results.sample.v1.json")
    validator.validate_short_timestamps(copy.deepcopy(canonical))
    cases = (
        ("impossible calendar date", ("scenario", "startedAt"), "2026-02-30T22:21:32Z"),
        ("timezone offset", ("scenario", "startedAt"), "2026-09-21T22:21:32+00:00"),
        ("missing seconds", ("scenario", "startedAt"), "2026-09-21T22:21Z"),
        ("completion before start", ("scenario", "completedAt"), "2026-09-21T22:21:31Z"),
        ("generation before completion", ("generatedAt",), "2026-09-21T22:21:35Z"),
        ("observation before start", ("scenario", "observations", 0, "observedAt"), "2026-09-21T22:21:31Z"),
        ("observation after completion", ("scenario", "observations", 0, "observedAt"), "2026-09-21T22:21:37Z"),
        ("observation out of order", ("scenario", "observations", 1, "observedAt"), "2026-09-21T22:21:32Z"),
        ("observation nonstring", ("scenario", "observations", 0, "observedAt"), None),
    )
    for label, keys, value in cases:
        mutated = copy.deepcopy(canonical)
        cursor = mutated
        for key in keys[:-1]:
            cursor = cursor[key]
        cursor[keys[-1]] = value
        try:
            validator.validate_short_timestamps(mutated)
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"short stability timestamp validator accepted {label}")
    print("PASS: short stability UTC positive and 9 timestamp negatives")



def verify_short_slope_and_delta_provenance() -> None:
    """Exercise canonical full validator on disposable forged summary mutations."""
    validator_path = ROOT / "scripts/validate-memory-os-short-stability-sample.py"
    spec = importlib.util.spec_from_file_location("short_stability_slope_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("short stability slope validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical_contract = validator.load(validator.CONTRACT_PATH)
    canonical_result = validator.load(ROOT / canonical_contract["resultPath"])
    summary_fields = (
        "finalMinusBaselineHeapAllocBytes",
        "finalMinusBaselineHeapInuseBytes",
        "finalMinusBaselineRssBytes",
        "finalMinusBaselineGoroutines",
        "heapAllocSlopeBytesPerWindow",
        "heapInuseSlopeBytesPerWindow",
        "rssSlopeBytesPerWindow",
        "goroutineSlopePerWindow",
    )
    original_contract = validator.CONTRACT_PATH
    with tempfile.TemporaryDirectory(prefix=".short-stability-slope-negative-", dir=ROOT) as tmp:
        contract_path = Path(tmp) / "contract.json"
        result_path = Path(tmp) / "result.json"
        contract = copy.deepcopy(canonical_contract)
        contract["resultPath"] = str(result_path.relative_to(ROOT))
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        validator.CONTRACT_PATH = contract_path
        try:
            result_path.write_text(json.dumps(canonical_result), encoding="utf-8")
            if validator.main() != 0:
                raise RuntimeError("short stability slope positive control failed")
            for field in summary_fields:
                mutated = copy.deepcopy(canonical_result)
                mutated["scenario"][field] += 1
                result_path.write_text(json.dumps(mutated), encoding="utf-8")
                try:
                    validator.main()
                except validator.ValidationFailure:
                    pass
                else:
                    raise RuntimeError(f"short stability accepted forged {field}")
            mutated = copy.deepcopy(canonical_result)
            mutated["scenario"]["observations"][0]["heapAllocBytes"] += 1
            result_path.write_text(json.dumps(mutated), encoding="utf-8")
            try:
                validator.main()
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError("short stability accepted observation/summary provenance drift")
        finally:
            validator.CONTRACT_PATH = original_contract
    print("PASS: short stability slope/delta positive and 9 provenance negatives")



def verify_short_batch_accounting() -> None:
    """Execute the canonical short stability validator against seven disposable batch mutations."""
    validator_path = ROOT / "scripts/validate-memory-os-short-stability-sample.py"
    spec = importlib.util.spec_from_file_location("short_stability_batch_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("short stability batch validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical_contract = validator.load(validator.CONTRACT_PATH)
    canonical_result = validator.load(ROOT / canonical_contract["resultPath"])
    cases = (
        ("float request count", ("requests",), 300.0),
        ("float 2xx count", ("statusClassCounts", "2xx"), 300.0),
        ("boolean 5xx count", ("statusClassCounts", "5xx"), False),
        ("unknown status class", ("statusClassCounts", "6xx"), 1),
        ("unreported 3xx", ("statusClassCounts", "3xx"), 1),
        ("invented low throughput", ("throughput",), 0.001),
        ("derived throughput overflow", ("durationSeconds",), 5e-324),
    )
    original_contract = validator.CONTRACT_PATH
    with tempfile.TemporaryDirectory(prefix=".short-stability-batch-negative-", dir=ROOT) as tmp:
        contract_path = Path(tmp) / "contract.json"
        result_path = Path(tmp) / "result.json"
        contract = copy.deepcopy(canonical_contract)
        contract["resultPath"] = str(result_path.relative_to(ROOT))
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        validator.CONTRACT_PATH = contract_path
        try:
            result_path.write_text(json.dumps(canonical_result), encoding="utf-8")
            if validator.main() != 0:
                raise RuntimeError("short stability batch positive control failed")
            for label, keys, value in cases:
                mutated = copy.deepcopy(canonical_result)
                cursor = mutated["scenario"]["observations"][0]["batch"]
                for key in keys[:-1]:
                    cursor = cursor[key]
                cursor[keys[-1]] = value
                result_path.write_text(json.dumps(mutated), encoding="utf-8")
                try:
                    validator.main()
                except validator.ValidationFailure:
                    pass
                else:
                    raise RuntimeError(f"short stability accepted {label}")
        finally:
            validator.CONTRACT_PATH = original_contract
    print("PASS: short stability batch positive and 7 status/throughput negatives")


def main() -> int:
    module = load_module()
    verify_short_numeric_boundary()
    verify_short_timestamp_semantics()
    verify_short_slope_and_delta_provenance()
    verify_short_batch_accounting()
    substitutions = {
        "CONTRACT_PATH": module.LOAD_PATH,
        "LOAD_PATH": module.CONTRACT_PATH,
        "STATUS_PATH": module.LOAD_PATH,
        "RESULT_PATH": module.CONTRACT_PATH,
        "SHORT_VALIDATOR": module.LOAD_VALIDATOR,
        "SOAK_RECONCILER": module.SHORT_VALIDATOR,
        "LOAD_VALIDATOR": module.SHORT_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    print("PASS: short stability direct reconcile source authorities are canonical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
