#!/usr/bin/env python3
"""Read-only, bounded LOCAL synthetic diagnostic for load foundation ordering negatives."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEGATIVE = ROOT / "scripts/validate-memory-os-short-stability-reconcile-negative.py"
PROTECTED = (
    "contracts/operations/short-stability-sample-contract.v1.json",
    "contracts/operations/capacity-ramp-contract.v1.json",
    "contracts/operations/controlled-saturation-ramp-contract.v1.json",
    "contracts/operations/deletion-under-load-contract.v1.json",
    "contracts/operations/load-test-scenario-contract.v1.json",
    "contracts/operations/production-operability-status.json",
    "contracts/operations/ops-p0-007-admission-snapshot.v1.json",
)
CASES = (
    ("short-preservation", "short", "run_short_preservation_case"),
    ("short-rollback", "short", "run_short_rollback_case"),
    ("capacity-rollback", "capacity", "run_capacity_rollback_case"),
    ("controlled-preservation", "controlled", "run_controlled_saturation_preservation_case"),
    ("controlled-rollback", "controlled", "run_controlled_saturation_rollback_case"),
    ("deletion-preservation", "deletion", "run_deletion_preservation_case"),
    ("deletion-rollback", "deletion", "run_deletion_rollback_case"),
)
EXCEPTION_CLASSES = {
    "NegativeFailure", "ReconcileFailure", "Fail", "AssertionError",
    "RuntimeError", "SystemExit", "OSError", "KeyError", "ValueError",
}

def snapshot() -> dict[str, tuple[str, int]]:
    result = {}
    for name in PROTECTED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("protected local fixture missing or symlinked")
        result[name] = (hashlib.sha256(path.read_bytes()).hexdigest(), stat.S_IMODE(path.stat().st_mode))
    return result

def make_report(stage: str, exception_class: str, drift: bool) -> dict[str, object]:
    allowed = {row[0] for row in CASES}
    stage = stage if stage in allowed else "unknown"
    exception_class = exception_class if exception_class in EXCEPTION_CLASSES else "UNKNOWN"
    return {
        "schemaVersion": "memory-os-load-foundation-ordering-diagnostic.v1",
        "classification": "LOCAL_SYNTHETIC_DIAGNOSTIC",
        "subcase": stage,
        "exceptionClass": exception_class,
        "protectedDrift": drift,
        "result": "FAIL" if stage != "unknown" or drift else "PASS",
        "diagnosticOnly": True,
        "productionEvidence": False,
        "productionReady": False,
        "leakProof": False,
        "productionDecision": "NO_GO",
    }

def write_report(value: dict[str, object]) -> None:
    path = Path(os.environ.get("DIAGNOSTIC_RESULT_PATH", ""))
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or not path.parent.is_dir():
        raise RuntimeError("diagnostic output must be existing non-symlink temporary file")
    payload = (json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    mode = stat.S_IMODE(path.stat().st_mode)
    fd, name = tempfile.mkstemp(prefix=".ordering-diagnostic-", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass

def run_diagnostic() -> int:
    before = snapshot()
    spec = importlib.util.spec_from_file_location("load_foundation_ordering_negative", NEGATIVE)
    if spec is None or spec.loader is None:
        write_report(make_report("unknown", "RuntimeError", True))
        return 1
    negative = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(negative)
    modules = {
        "short": negative.load_module("ordering_short", negative.SHORT_SCRIPT),
        "capacity": negative.load_module("ordering_capacity", negative.CAPACITY_SCRIPT),
        "controlled": negative.load_module("ordering_controlled", negative.CONTROLLED_SCRIPT),
        "deletion": negative.load_module("ordering_deletion", negative.DELETION_SCRIPT),
    }
    for label, key, method in CASES:
        failure = None
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as sink:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                try:
                    getattr(negative, method)(modules[key])
                except BaseException as exc:
                    failure = type(exc).__name__
        try:
            drift = snapshot() != before
        except Exception:
            drift = True
        if failure is not None or drift:
            write_report(make_report(label, failure or "RuntimeError", drift))
            return 1
    write_report(make_report("unknown", "UNKNOWN", False))
    return 0

def self_test() -> None:
    failure = make_report("short-preservation", "SYNTHETIC_SECRET_CANARY", False)
    if (failure["subcase"] != "short-preservation" or failure["exceptionClass"] != "UNKNOWN"
            or failure["result"] != "FAIL" or "SYNTHETIC_SECRET_CANARY" in json.dumps(failure)):
        raise AssertionError("diagnostic report allowlist drift")
    positive = make_report("unknown", "UNKNOWN", False)
    if positive["result"] != "PASS" or positive["productionDecision"] != "NO_GO":
        raise AssertionError("diagnostic positive/nonpromotion drift")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    return run_diagnostic()

if __name__ == "__main__":
    raise SystemExit(main())
