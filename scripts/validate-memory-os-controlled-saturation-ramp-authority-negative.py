#!/usr/bin/env python3
"""Prove controlled saturation direct reconcile pins canonical source authorities and atomic rollback."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-controlled-saturation-ramp-status.py"


def load_module():
    spec = importlib.util.spec_from_file_location("controlled_saturation_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load controlled saturation reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except SystemExit:
            pass
        else:
            raise RuntimeError(f"{attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def temp_residue(path: Path) -> list[Path]:
    return list(path.parent.glob(f".{path.name}.*.tmp"))


def verify_atomic_replace_failure(module) -> None:
    module.enforce_runtime_authorities()
    paths = module.TRANSACTION_PATHS
    originals = {path: path.read_bytes() for path in paths}
    residues_before = set(path for authority in paths for path in temp_residue(authority))
    original_replace = module.os.replace
    calls = 0

    def fail_first_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("synthetic controlled saturation atomic replacement failure")
        original_replace(src, dst)

    module.os.replace = fail_first_replace
    try:
        rejected = False
        try:
            module.write_transactionally(
                module.load(module.CONTROLLED_CONTRACT),
                module.load(module.LOAD_CONTRACT),
                module.load(module.STATUS_PATH),
                module.load(module.RESULT_PATH)["commitSha"],
            )
        except BaseException as exc:
            rejected = True
            if "synthetic controlled saturation atomic replacement failure" not in str(exc):
                raise RuntimeError(f"unexpected atomic rejection: {exc}") from exc
        if not rejected:
            raise RuntimeError("controlled saturation accepted synthetic atomic replacement failure")
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                raise RuntimeError(f"atomic replacement failure mutated {path.relative_to(ROOT)}")
        residues_after = set(path for authority in paths for path in temp_residue(authority))
        if residues_after != residues_before:
            raise RuntimeError("controlled saturation atomic failure left temporary authority residue")
    finally:
        module.os.replace = original_replace
        for path, payload in originals.items():
            if path.read_bytes() != payload:
                module.atomic_write_bytes(path, payload)


def verify_nonfinite_ramp_measurements() -> None:
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_numeric_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation numeric validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    result = validator.load(validator.RESULT_PATH)
    batch = result["scenario"]["steps"][0]["batch"]
    if not validator.validate_batch(copy.deepcopy(batch), 4, 64, "synthetic-positive"):
        raise RuntimeError("controlled saturation numeric positive control failed")
    for label, field, bad in (
        ("infinite throughput", "throughput", float("inf")),
        ("infinite p95", "latencyP95Ms", float("inf")),
        ("nan p99", "latencyP99Ms", float("nan")),
        ("overflow duration", "durationSeconds", 10 ** 500),
    ):
        mutated = copy.deepcopy(batch)
        mutated[field] = bad
        try:
            validator.validate_batch(mutated, 4, 64, "synthetic-negative")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    for label, value in (("infinite pool duration", float("inf")),
                         ("overflow pool duration", 10 ** 500)):
        try:
            validator.number(value, "synthetic-pool-delta")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    with tempfile.TemporaryDirectory(prefix=".saturation-numeric-negative-", dir=ROOT) as temp:
        path = Path(temp) / "synthetic.json"
        for raw in ('{"value": Infinity}', '{"value": 1e999}'):
            path.write_text(raw, encoding="utf-8")
            try:
                validator.load(path)
            except validator.ValidationFailure:
                pass
            else:
                raise RuntimeError("controlled saturation accepted nonfinite JSON")
    print("PASS: controlled saturation numeric parser and measurement negatives (8 cases)")



def verify_ramp_timestamp_semantics() -> None:
    """Exercise the actual ramp timestamp validator with a positive fixture and failures."""
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_timestamp_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation timestamp validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical = validator.load(validator.RESULT_PATH)
    # A real positive control catches double-escaped raw regexes that reject every timestamp.
    validator.validate_ramp_timestamps(copy.deepcopy(canonical))
    negatives = (
        ("invalid calendar day", ("scenario", "startedAt"), "2026-02-30T23:00:44Z"),
        ("timezone offset", ("scenario", "startedAt"), "2026-09-23T23:00:44+00:00"),
        ("missing seconds", ("scenario", "startedAt"), "2026-09-23T23:00Z"),
        ("fraction without digits", ("scenario", "startedAt"), "2026-09-23T23:00:44.Z"),
        ("non-string timestamp", ("scenario", "startedAt"), None),
        ("completion before start", ("scenario", "completedAt"), "2026-09-23T23:00:43Z"),
        ("generation before completion", ("generatedAt",), "2026-09-23T23:00:46Z"),
    )
    for label, keys, value in negatives:
        mutated = copy.deepcopy(canonical)
        cursor = mutated
        for key in keys[:-1]:
            cursor = cursor[key]
        cursor[keys[-1]] = value
        try:
            validator.validate_ramp_timestamps(mutated)
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    print("PASS: controlled saturation RFC3339 UTC positive and 7 timestamp negatives")



def verify_pool_snapshot_and_delta_accounting() -> None:
    """Use the canonical ramp validator on disposable full-result pool mutations."""
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_pool_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation pool validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    canonical = validator.load(validator.RESULT_PATH)
    cases = (
        ("negative total", ("poolBefore", "totalConns"), -1),
        ("negative acquired", ("poolBefore", "acquiredConns"), -1),
        ("negative canceled", ("poolAfter", "canceledAcquireCount"), -1),
        ("negative empty", ("poolBefore", "emptyAcquireCount"), -1),
        ("total exceeds max", ("poolBefore", "totalConns"), 100),
        ("acquired exceeds total", ("poolBefore", "acquiredConns"), 100),
        ("idle exceeds total", ("poolAfter", "idleConns"), 100),
        ("duration delta mismatch", ("poolDelta", "acquireDurationMs"), 999),
    )
    original_result_path = validator.RESULT_PATH
    with tempfile.TemporaryDirectory(prefix=".saturation-pool-negative-", dir=ROOT) as tmp:
        result_path = Path(tmp) / "synthetic-ramp.json"
        validator.RESULT_PATH = result_path
        try:
            result_path.write_text(json.dumps(canonical), encoding="utf-8")
            if validator.main() != 0:
                raise RuntimeError("controlled saturation pool positive control failed")
            for label, keys, value in cases:
                mutated = copy.deepcopy(canonical)
                mutated["scenario"]["steps"][0][keys[0]][keys[1]] = value
                result_path.write_text(json.dumps(mutated), encoding="utf-8")
                try:
                    validator.main()
                except validator.ValidationFailure:
                    pass
                else:
                    raise RuntimeError(f"controlled saturation accepted {label}")
        finally:
            validator.RESULT_PATH = original_result_path
    print("PASS: controlled saturation pool full-validator positive and 8 negatives")



def verify_batch_status_accounting() -> None:
    """Reject impossible signed-upload lifecycle counts using the actual validator."""
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_status_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation status validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    batch = validator.load(validator.RESULT_PATH)["scenario"]["steps"][0]["batch"]
    if not validator.validate_batch(copy.deepcopy(batch), 4, 64, "synthetic-positive"):
        raise RuntimeError("controlled saturation status positive control failed")
    cases = (
        ("negative 5xx offset", {"5xx": -1, "transport_error": 1}, 64, 0),
        ("negative transport offset", {"5xx": 1, "transport_error": -1}, 64, 0),
        ("negative successes", {"2xx": -1, "5xx": 65}, -1, 65),
        ("negative failures", {"2xx": 65, "5xx": -1}, 65, -1),
        ("unknown status class", {"6xx": 1}, 64, 0),
    )
    for label, classes, successes, failures in cases:
        mutated = copy.deepcopy(batch)
        mutated["statusClassCounts"].update(classes)
        mutated["successes"] = successes
        mutated["failures"] = failures
        try:
            validator.validate_batch(mutated, 4, 64, "synthetic-negative")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    print("PASS: controlled saturation status accounting positive and 5 negatives")



def verify_batch_metric_coherence() -> None:
    """Exercise canonical throughput and percentile checks with real validator calls."""
    validator_path = ROOT / "scripts/validate-memory-os-controlled-saturation-ramp.py"
    spec = importlib.util.spec_from_file_location("controlled_saturation_metric_validator", validator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("controlled saturation metric validator import failed")
    validator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validator)
    result = validator.load(validator.RESULT_PATH)
    for index, step in enumerate(result["scenario"]["steps"]):
        if not validator.validate_batch(copy.deepcopy(step["batch"]), step["concurrency"], 64,
                                        f"synthetic-positive-{index}"):
            raise RuntimeError("controlled saturation metric positive control failed")
    if not validator.validate_batch(copy.deepcopy(result["scenario"]["postRampRecoveryProbe"]),
                                    1, 1, "synthetic-recovery-positive"):
        raise RuntimeError("controlled saturation recovery metric positive control failed")
    batch = result["scenario"]["steps"][0]["batch"]
    cases = (
        ("zero duration", "durationSeconds", 0),
        ("zero throughput", "throughput", 0),
        ("invented throughput", "throughput", batch["throughput"] + 10),
        ("p50 greater than p95", "latencyP50Ms", batch["latencyP95Ms"] + 1),
        ("p95 greater than p99", "latencyP95Ms", batch["latencyP99Ms"] + 1),
        ("derived throughput overflow", "durationSeconds", 5e-324),
    )
    for label, key, value in cases:
        mutated = copy.deepcopy(batch)
        mutated[key] = value
        try:
            validator.validate_batch(mutated, 4, 64, "synthetic-negative")
        except validator.ValidationFailure:
            pass
        else:
            raise RuntimeError(f"controlled saturation accepted {label}")
    print("PASS: controlled saturation metric positives and 6 coherence negatives")


def main() -> int:
    module = load_module()
    verify_nonfinite_ramp_measurements()
    verify_ramp_timestamp_semantics()
    verify_pool_snapshot_and_delta_accounting()
    verify_batch_status_accounting()
    verify_batch_metric_coherence()
    substitutions = {
        "CONTROLLED_CONTRACT": module.LOAD_CONTRACT,
        "LOAD_CONTRACT": module.CONTROLLED_CONTRACT,
        "STATUS_PATH": module.LOAD_CONTRACT,
        "RESULT_PATH": module.CONTROLLED_CONTRACT,
        "CONTROLLED_VALIDATOR": module.LOAD_VALIDATOR,
        "LOAD_VALIDATOR": module.CONTROLLED_VALIDATOR,
        "LOAD_INDEX_VALIDATOR": module.LOAD_VALIDATOR,
        "OPERABILITY_VALIDATOR": module.LOAD_VALIDATOR,
        "WORKFLOW": module.CONTROLLED_VALIDATOR,
    }
    for attr, replacement in substitutions.items():
        expect_rejection(module, attr, replacement)
    module.enforce_runtime_authorities()
    verify_atomic_replace_failure(module)
    print("PASS: controlled saturation direct reconcile source authorities are canonical and atomic")
    print("atomic replacement failure: rejected without authority mutation")
    print("temporary authority residue: none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
