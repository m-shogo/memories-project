#!/usr/bin/env python3
"""Prove environment review-independence reconciliation is canonical and transactionally fail-closed."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-equivalent-environment-review-independence.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-review-independence-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_environment_review_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load environment review reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_direct_authority_rejected(
    reconciler: Any,
    *,
    name: str,
    field: str,
    attribute: str,
    replacement: Path,
    canonical_contract: bytes,
    canonical_generation_registry: bytes,
) -> None:
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct reconciler unexpectedly accepted: {name}")
        require(CONTRACT.read_bytes() == canonical_contract, f"canonical review-independence contract mutated while rejecting {name}")
        require(GEN_REGISTRY.read_bytes() == canonical_generation_registry, f"canonical generation registry mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_direct_authority_identity(reconciler: Any) -> None:
    canonical_contract = CONTRACT.read_bytes()
    canonical_generation_registry = GEN_REGISTRY.read_bytes()
    cases = (
        ("review contract substitution", "review independence contract", "CONTRACT", reconciler.GEN_REGISTRY),
        ("generation registry substitution", "generation registry", "GEN_REGISTRY", reconciler.CONTRACT),
        ("eligibility helper substitution", "generation eligibility helper", "HELPER", reconciler.VALIDATOR),
        ("review validator substitution", "review independence validator", "VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
        ("operability validator substitution", "operability validator", "OPERABILITY_VALIDATOR", reconciler.VALIDATOR),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(
            reconciler,
            name=name,
            field=field,
            attribute=attribute,
            replacement=replacement,
            canonical_contract=canonical_contract,
            canonical_generation_registry=canonical_generation_registry,
        )
    print(f"PASS boundary: direct review-independence data/executable substitutions rejected: {len(cases)}")


def main() -> int:
    require(RECONCILER.is_file(), "environment review reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()
    prove_direct_authority_identity(reconciler)

    original_enforcer = reconciler.enforce_runtime_authorities
    original_contract_path = reconciler.CONTRACT
    original_generation_registry_path = reconciler.GEN_REGISTRY
    original_post_validator = reconciler.run_post_validator
    original_atomic_write = reconciler.atomic_write_text
    original_os_replace = reconciler.os.replace
    canonical_contract = CONTRACT.read_bytes()
    canonical_generation_registry = GEN_REGISTRY.read_bytes()

    # Fixture mutation is below the production authority boundary. Direct runtime
    # invocation remains canonical-only; this block exercises transaction failure paths.
    reconciler.enforce_runtime_authorities = lambda: None
    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-environment-review-reconcile-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            contract_copy = tmp / CONTRACT.name
            generation_registry_copy = tmp / GEN_REGISTRY.name
            shutil.copyfile(CONTRACT, contract_copy)
            shutil.copyfile(GEN_REGISTRY, generation_registry_copy)
            reconciler.CONTRACT = contract_copy
            reconciler.GEN_REGISTRY = generation_registry_copy

            # A failed atomic replacement must preserve bytes and clean its temp file.
            atomic_original = contract_copy.read_bytes()
            replace_calls = 0

            def fail_first_replace(source: str | Path, destination: str | Path) -> None:
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == 1:
                    raise OSError("synthetic review-independence atomic replacement failure")
                original_os_replace(source, destination)

            reconciler.os.replace = fail_first_replace
            try:
                try:
                    reconciler.main()
                except OSError as exc:
                    require("synthetic review-independence atomic replacement failure" in str(exc), f"atomic failure rejected at wrong boundary: {exc}")
                except Exception as exc:
                    raise Fail(f"atomic failure leaked unexpected exception: {type(exc).__name__}: {exc}") from exc
                else:
                    raise Fail("synthetic review-independence atomic replacement failure unexpectedly accepted")
                require(replace_calls == 2, f"atomic failure did not perform exactly one rollback replace: {replace_calls}")
                require(contract_copy.read_bytes() == atomic_original, "failed atomic replacement mutated review-independence contract")
                require(
                    not list(contract_copy.parent.glob(f".{contract_copy.name}.*.tmp")),
                    "failed atomic replacement left temporary review-independence authority behind",
                )
            finally:
                reconciler.os.replace = original_os_replace
            print("PASS atomic replacement failure: contract bytes preserved and temp cleaned")

            # Force a byte-distinct but semantically equivalent source so the post
            # validator hook proves the publication happened before aggregate failure.
            import json

            parsed = json.loads(contract_copy.read_text(encoding="utf-8"))
            contract_copy.write_text(json.dumps(parsed, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            rollback_original = contract_copy.read_bytes()
            observed: list[str] = []

            def aggregate_failure_after_review_success(path: Path, expected_relative: Path, field: str) -> None:
                require(contract_copy.read_bytes() != rollback_original, "post-validator invoked before review-independence write")
                observed.append(field)
                if len(observed) == 1:
                    require(field == "review independence validator", "review validator was not first post-write validator")
                    return
                require(len(observed) == 2, "unexpected extra review-independence post-validator invocation")
                require(field == "operability validator", "operability validator was not second post-write validator")
                raise reconciler.Fail("synthetic aggregate operability rejection")

            reconciler.run_post_validator = aggregate_failure_after_review_success
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("synthetic aggregate operability rejection" in str(exc), f"aggregate failure rejected at wrong boundary: {exc}")
            except Exception as exc:
                raise Fail(f"aggregate failure leaked unexpected exception: {type(exc).__name__}: {exc}") from exc
            else:
                raise Fail("forced aggregate review-independence validation failure unexpectedly accepted")
            require(observed == ["review independence validator", "operability validator"], "canonical post-write validator order drift")
            require(contract_copy.read_bytes() == rollback_original, "aggregate rejection left review-independence contract mutation")
            print("PASS rollback: aggregate rejection restored review-independence contract byte-for-byte")

            reconciler.run_post_validator = original_post_validator
            diagnostic_original = contract_copy.read_bytes()
            write_calls = 0

            def fail_rollback_write(path: Path, text: str) -> None:
                nonlocal write_calls
                require(path == contract_copy, f"unexpected review-independence diagnostic write target: {path}")
                write_calls += 1
                if write_calls == 1:
                    return
                raise reconciler.Fail("synthetic review-independence rollback rejection")

            def fail_post_validator(path: Path, expected_relative: Path, field: str) -> None:
                raise reconciler.Fail("synthetic review-independence post-validator rejection")

            reconciler.atomic_write_text = fail_rollback_write
            reconciler.run_post_validator = fail_post_validator
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                message = str(exc)
                require("review independence reconcile failed" in message, f"rollback failure missing reconcile context: {message}")
                require("synthetic review-independence post-validator rejection" in message, f"rollback failure lost primary error: {message}")
                require("rollback incomplete" in message, f"rollback failure missing incomplete marker: {message}")
                require("synthetic review-independence rollback rejection" in message, f"rollback failure lost rollback error: {message}")
            except Exception as exc:
                raise Fail(f"review-independence rollback diagnostic leaked unexpected exception: {type(exc).__name__}: {exc}") from exc
            else:
                raise Fail("synthetic review-independence rollback failure unexpectedly accepted")
            finally:
                reconciler.atomic_write_text = original_atomic_write
                reconciler.run_post_validator = original_post_validator
            require(write_calls == 2, f"review-independence diagnostic did not attempt publication and rollback exactly once: {write_calls}")
            require(contract_copy.read_bytes() == diagnostic_original, "review-independence rollback diagnostic mutated fixture contract")
            require(CONTRACT.read_bytes() == canonical_contract, "canonical review-independence contract mutated by diagnostic fixture")
            require(GEN_REGISTRY.read_bytes() == canonical_generation_registry, "canonical generation registry mutated by diagnostic fixture")
            print("PASS rollback diagnostics: primary rejection and rollback failure are both preserved")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.CONTRACT = original_contract_path
        reconciler.GEN_REGISTRY = original_generation_registry_path
        reconciler.run_post_validator = original_post_validator
        reconciler.atomic_write_text = original_atomic_write
        reconciler.os.replace = original_os_replace

    require(CONTRACT.read_bytes() == canonical_contract, "canonical review-independence contract changed during negative suite")
    require(GEN_REGISTRY.read_bytes() == canonical_generation_registry, "canonical generation registry changed during negative suite")
    print("Environment review-independence reconcile negative suite PASS")
    print("direct data/executable authority substitutions accepted: false")
    print("atomic replacement failure preserves canonical authority: true")
    print("atomic replacement temp cleanup: true")
    print("aggregate operability failure rolls back review-independence authority: true")
    print("rollback failure preserves primary diagnostic: true")
    print("review evidence created: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT REVIEW RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
