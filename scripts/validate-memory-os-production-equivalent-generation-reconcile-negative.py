#!/usr/bin/env python3
"""Prove environment-generation reconciliation authority identity, ordering and rollback."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-equivalent-generation-status.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation reconciler")
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


def assert_canonical_unchanged(contract_bytes: bytes, registry_bytes: bytes, status_bytes: bytes, label: str) -> None:
    require(CONTRACT.read_bytes() == contract_bytes, f"{label} changed canonical generation contract")
    require(REGISTRY.read_bytes() == registry_bytes, f"{label} changed canonical generation registry")
    require(STATUS.read_bytes() == status_bytes, f"{label} changed canonical production status")


def main() -> int:
    require(RECONCILER.is_file(), "environment generation reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    canonical_contract = CONTRACT.read_bytes()
    canonical_registry = REGISTRY.read_bytes()
    canonical_status = STATUS.read_bytes()

    substitutions = (
        ("CONTRACT", reconciler.REGISTRY, "environment generation contract authority drift"),
        ("REGISTRY", reconciler.CONTRACT, "environment generation registry authority drift"),
        ("GEN_SCHEMA", reconciler.CONTRACT, "environment generation record schema authority drift"),
        ("ENV_VALIDATOR", reconciler.VALIDATOR, "environment semantic validator authority drift"),
        ("WRITER", reconciler.VALIDATOR, "environment generation writer authority drift"),
        ("VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "environment generation validator authority drift"),
        ("OPERABILITY_VALIDATOR", reconciler.VALIDATOR, "operability validator authority drift"),
        ("NEGATIVE", reconciler.VALIDATOR, "environment generation negative suite authority drift"),
        ("STATUS", reconciler.CONTRACT, "production operability status authority drift"),
    )
    for attribute, replacement, expected in substitutions:
        original = getattr(reconciler, attribute)
        setattr(reconciler, attribute, replacement)
        try:
            expect_domain_fail(f"{attribute.lower()} substitution", reconciler.main, reconciler.Fail, expected)
            assert_canonical_unchanged(canonical_contract, canonical_registry, canonical_status, attribute.lower())
        finally:
            setattr(reconciler, attribute, original)

    with tempfile.TemporaryDirectory(prefix=".tmp-environment-generation-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 generation authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("unreadable generation authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-environment-generation-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("generation authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

        absolute_ref = str((ROOT / "README.md").resolve())
        expect_domain_fail("absolute current environment ref", lambda: reconciler.canonical_repo_ref(absolute_ref, "invalid ref"), reconciler.Fail)
        expect_domain_fail("parent traversal current environment ref", lambda: reconciler.canonical_repo_ref("scripts/../README.md", "invalid ref"), reconciler.Fail)

    writer = reconciler.load_writer()
    canonical_registry_obj: dict[str, Any] = json.loads(canonical_registry.decode("utf-8"))
    corruption_cases: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
        ("registry schema drift", lambda value: value.__setitem__("schemaVersion", "broken")),
        ("registry class drift", lambda value: value.__setitem__("registryClass", "BROKEN")),
        ("append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promoted", lambda value: value.__setitem__("productionEvidence", True)),
        ("registered generation boolean count", lambda value: value.__setitem__("registeredGenerationCount", True)),
        ("registered generation count drift", lambda value: value.__setitem__("registeredGenerationCount", 1)),
        ("empty registry current pointer drift", lambda value: value.__setitem__("currentGenerationId", "pegen_invalid_current")),
    )
    for name, mutate in corruption_cases:
        corrupted = json.loads(json.dumps(canonical_registry_obj))
        mutate(corrupted)
        try:
            writer.validate_registry_for_append(corrupted)
        except Exception:
            print(f"PASS reject before reconcile: {name}")
        else:
            raise Fail(f"corrupt generation registry unexpectedly accepted: {name}")
        assert_canonical_unchanged(canonical_contract, canonical_registry, canonical_status, name)

    prefix = reconciler.EVIDENCE_PREFIX
    old = prefix + " old"
    new = prefix + " new"
    values = ["before", old, "after"]
    reconciler.replace_single_prefixed(values, prefix, new)
    require(values == ["before", new, "after"], "environment generation evidence moved during replacement")
    values = [old, prefix + " duplicate"]
    expect_domain_fail(
        "duplicate environment generation evidence prefix",
        lambda: reconciler.replace_single_prefixed(values, prefix, new),
        reconciler.Fail,
        "duplicate authority evidence prefix",
    )
    require(values == [old, prefix + " duplicate"], "duplicate generation evidence rejection mutated ordering")
    print("PASS preserve: environment generation evidence ordering is deterministic")

    observed: list[str] = []
    original_run_validator = reconciler.run_validator

    def fail_after_generation_validator(path: Path, expected_relative: Path, label: str) -> None:
        observed.append(label)
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail("operability validator failed: synthetic aggregate failure")
        return None

    reconciler.run_validator = fail_after_generation_validator
    try:
        expect_domain_fail(
            "post-write aggregate operability failure",
            reconciler.main,
            reconciler.Fail,
            "operability validator failed",
        )
    finally:
        reconciler.run_validator = original_run_validator

    require(observed == ["generation validator", "operability validator"], f"post-write validator order drift: {observed}")
    assert_canonical_unchanged(canonical_contract, canonical_registry, canonical_status, "aggregate rollback")

    print("PASS rollback: environment generation contract/registry/status preserved byte-for-byte")
    print("canonical generation data/executable substitutions accepted: false")
    print("generation evidence reordering accepted: false")
    print("aggregate operability failure triggers rollback: true")
    print("Environment generation reconcile negative suite PASS")
    print("production generation created: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
