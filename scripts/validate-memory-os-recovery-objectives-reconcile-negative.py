#!/usr/bin/env python3
"""Prove recovery-objective reconciliation authority identity, ordering and transactional rollback."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-recovery-objectives.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load recovery objective reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException], expected: str | None = None) -> None:
    try:
        action()
    except fail_type as exc:
        if expected is not None:
            require(expected in str(exc), f"{name} rejected at wrong boundary: {exc}")
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def assert_canonical_unchanged(contract_bytes: bytes, status_bytes: bytes, label: str) -> None:
    require(CONTRACT.read_bytes() == contract_bytes, f"{label} changed canonical recovery objective contract")
    require(STATUS.read_bytes() == status_bytes, f"{label} changed canonical production status")


def main() -> int:
    require(RECONCILER.is_file(), "recovery objective reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    canonical_contract = CONTRACT.read_bytes()
    canonical_status = STATUS.read_bytes()

    substitutions = (
        ("CONTRACT", reconciler.REGISTRY, "recovery objective contract authority drift"),
        ("REGISTRY", reconciler.CONTRACT, "recovery objective registry authority drift"),
        ("WRITER", reconciler.VALIDATOR, "recovery objective writer authority drift"),
        ("VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "recovery objective validator authority drift"),
        ("OPERABILITY_VALIDATOR", reconciler.VALIDATOR, "operability validator authority drift"),
        ("STATUS", reconciler.CONTRACT, "production operability status authority drift"),
    )
    for attribute, replacement, expected in substitutions:
        original = getattr(reconciler, attribute)
        setattr(reconciler, attribute, replacement)
        try:
            expect_domain_fail(f"{attribute.lower()} substitution", reconciler.main, reconciler.Fail, expected)
            assert_canonical_unchanged(canonical_contract, canonical_status, attribute.lower())
        finally:
            setattr(reconciler, attribute, original)

    original_contract_path = reconciler.CONTRACT
    original_status_path = reconciler.STATUS
    reconciler.CONTRACT = reconciler.REGISTRY
    reconciler.STATUS = reconciler.REGISTRY
    try:
        expect_domain_fail(
            "paired contract/status fixture substitution",
            reconciler.main,
            reconciler.Fail,
            "recovery objective contract authority drift",
        )
        assert_canonical_unchanged(canonical_contract, canonical_status, "paired fixture substitution")
    finally:
        reconciler.CONTRACT = original_contract_path
        reconciler.STATUS = original_status_path

    prefix = reconciler.EVIDENCE_PREFIX
    old = prefix + " old"
    new = prefix + " new"
    values = ["before", old, "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", new, "after"], "recovery objective evidence moved during replacement")
    values = [old, prefix + " duplicate"]
    expect_domain_fail(
        "duplicate recovery objective status evidence",
        lambda: reconciler.replace_single_prefixed(values, prefix, new),
        reconciler.Fail,
        "duplicate authority evidence prefix",
    )
    require(values == [old, prefix + " duplicate"], "duplicate evidence rejection mutated status ordering")
    print("PASS preserve: recovery objective evidence ordering is deterministic")

    with tempfile.TemporaryDirectory(prefix=".tmp-recovery-objective-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 objective authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("unreadable objective authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-objective-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("objective authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

    original_run_validator = reconciler.run_validator
    validator_calls: list[tuple[Path, str]] = []

    def fail_aggregate_validator(path: Path, label: str) -> None:
        validator_calls.append((path, label))
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail("post-reconcile aggregate operability validator failed: forced negative")
        return None

    reconciler.run_validator = fail_aggregate_validator
    try:
        expect_domain_fail(
            "post-write aggregate operability rejection",
            reconciler.main,
            reconciler.Fail,
            "aggregate operability validator failed",
        )
    finally:
        reconciler.run_validator = original_run_validator

    require(
        validator_calls
        == [
            (reconciler.VALIDATOR, "recovery objective validator"),
            (reconciler.OPERABILITY_VALIDATOR, "aggregate operability validator"),
        ],
        f"recovery objective post-write validator order drift: {validator_calls}",
    )
    assert_canonical_unchanged(canonical_contract, canonical_status, "aggregate rollback")
    print("PASS rollback: aggregate operability rejection restores recovery objective contract/status byte-for-byte")
    print("PASS boundary: post-write validator order is recovery objective then aggregate Operability")
    print("paired recovery objective fixture substitution accepted: false")
    print("recovery objective data/executable substitution accepted: false")
    print("recovery objective evidence reordering accepted: false")
    print("Recovery objective reconcile negative suite PASS")
    print("objective created or defaulted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
