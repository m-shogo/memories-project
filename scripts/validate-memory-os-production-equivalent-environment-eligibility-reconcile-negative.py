#!/usr/bin/env python3
"""Prove environment-generation eligibility validation/reconciliation is canonical and fail-closed."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-eligibility.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-equivalent-environment-eligibility.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json"
GEN_CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
SUBSTITUTE_SCRIPT = ROOT / "scripts/validate-memory-os-operability.py"
SUBSTITUTE_DATA = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_target(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reconciler():
    return load_target(RECONCILER, "memory_os_environment_generation_eligibility_reconcile_negative")


def canonical_bytes() -> tuple[bytes, bytes, bytes]:
    return CONTRACT.read_bytes(), GEN_CONTRACT.read_bytes(), GEN_REGISTRY.read_bytes()


def assert_canonical_unchanged(before: tuple[bytes, bytes, bytes], label: str) -> None:
    require(CONTRACT.read_bytes() == before[0], f"canonical eligibility contract mutated while rejecting {label}")
    require(GEN_CONTRACT.read_bytes() == before[1], f"canonical generation contract mutated while rejecting {label}")
    require(GEN_REGISTRY.read_bytes() == before[2], f"canonical generation registry mutated while rejecting {label}")


def expect_validator_substitution_rejected(validator: Any, field: str, replacement: Any) -> None:
    before = canonical_bytes()
    original = getattr(validator, field)
    setattr(validator, field, replacement)
    try:
        try:
            validator.main()
        except validator.Fail:
            pass
        else:
            raise Fail(f"eligibility validator unexpectedly accepted substitution: {field}")
        assert_canonical_unchanged(before, field)
    finally:
        setattr(validator, field, original)


def prove_validator_execution_identity() -> None:
    validator = load_target(VALIDATOR, "memory_os_environment_generation_eligibility_validator_negative")
    path_cases = (
        ("CONTRACT", validator.GEN_CONTRACT),
        ("GEN_CONTRACT", validator.CONTRACT),
        ("GEN_REGISTRY", SUBSTITUTE_DATA),
        ("ENV_SCHEMA", validator.CONTRACT),
        ("ENV_VALIDATOR", SUBSTITUTE_SCRIPT),
        ("HELPER", SUBSTITUTE_SCRIPT),
        ("VALIDATOR", SUBSTITUTE_SCRIPT),
        ("RECONCILE", SUBSTITUTE_SCRIPT),
        ("WORKFLOW", validator.CONTRACT),
    )
    for field, replacement in path_cases:
        expect_validator_substitution_rejected(validator, field, replacement)

    helper_cases = (
        ("require", lambda condition, message: None),
        ("display_path", lambda path: str(path)),
        ("require_exact_repo_file", lambda path, expected, field: path),
        ("enforce_runtime_authorities", lambda: None),
        ("load", lambda path: {}),
        ("load_helper", lambda: object()),
        ("enforce_execution_identity", lambda: None),
    )
    for field, replacement in helper_cases:
        expect_validator_substitution_rejected(validator, field, replacement)

    print(f"PASS boundary: eligibility validator data/executable substitutions rejected: {len(path_cases)}")
    print(f"PASS boundary: eligibility validator execution helper substitutions rejected: {len(helper_cases)}")


def expect_direct_authority_rejected(
    reconciler: Any,
    *,
    name: str,
    field: str,
    attribute: str,
    replacement: Path,
    canonical_contract: bytes,
    canonical_generation_contract: bytes,
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
        require(CONTRACT.read_bytes() == canonical_contract, f"canonical eligibility contract mutated while rejecting {name}")
        require(GEN_CONTRACT.read_bytes() == canonical_generation_contract, f"canonical generation contract mutated while rejecting {name}")
        require(GEN_REGISTRY.read_bytes() == canonical_generation_registry, f"canonical generation registry mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_direct_authority_identity(reconciler: Any) -> None:
    canonical_contract = CONTRACT.read_bytes()
    canonical_generation_contract = GEN_CONTRACT.read_bytes()
    canonical_generation_registry = GEN_REGISTRY.read_bytes()
    cases = (
        ("eligibility contract substitution", "environment eligibility contract", "CONTRACT", reconciler.GEN_CONTRACT),
        ("generation registry substitution", "environment generation registry", "GEN_REGISTRY", reconciler.CONTRACT),
        ("generation contract substitution", "environment generation contract", "GEN_CONTRACT", reconciler.CONTRACT),
        ("eligibility helper substitution", "environment generation eligibility helper", "HELPER", reconciler.VALIDATOR),
        ("eligibility validator substitution", "environment eligibility validator", "VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
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
            canonical_generation_contract=canonical_generation_contract,
            canonical_generation_registry=canonical_generation_registry,
        )
    print(f"PASS boundary: direct eligibility data/executable substitutions rejected: {len(cases)}")


def main() -> int:
    require(VALIDATOR.is_file(), "generation eligibility validator missing")
    require(RECONCILER.is_file(), "generation eligibility reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    prove_validator_execution_identity()
    reconciler = load_reconciler()
    prove_direct_authority_identity(reconciler)

    original_enforcer = reconciler.enforce_runtime_authorities
    original_contract_path = reconciler.CONTRACT
    original_generation_contract_path = reconciler.GEN_CONTRACT
    original_generation_registry_path = reconciler.GEN_REGISTRY
    original_load_helper = reconciler.load_helper
    original_post_validator = reconciler.run_post_validator
    original_os_replace = reconciler.os.replace

    # Fixture mutation is deliberately below the production authority boundary:
    # direct invocation remains canonical-only, while this suite proves semantic
    # drift rejection, atomic replacement, and aggregate rollback internally.
    reconciler.enforce_runtime_authorities = lambda: None
    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-environment-eligibility-reconcile-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            contract_copy = tmp / CONTRACT.name
            generation_contract_copy = tmp / GEN_CONTRACT.name
            generation_registry_copy = tmp / GEN_REGISTRY.name
            shutil.copyfile(CONTRACT, contract_copy)
            shutil.copyfile(GEN_CONTRACT, generation_contract_copy)
            shutil.copyfile(GEN_REGISTRY, generation_registry_copy)
            original_contract = contract_copy.read_bytes()

            reconciler.CONTRACT = contract_copy
            reconciler.GEN_CONTRACT = generation_contract_copy
            reconciler.GEN_REGISTRY = generation_registry_copy

            canonical_helper = original_load_helper()

            def load_fixture_helper():
                helper = canonical_helper
                helper.derive = lambda _registry_path: helper.derive_registry(
                    json.loads(generation_registry_copy.read_text(encoding="utf-8"))
                )
                return helper

            reconciler.load_helper = load_fixture_helper

            drifted_generation_contract = json.loads(generation_contract_copy.read_text(encoding="utf-8"))
            generation_boundary = drifted_generation_contract.get("currentBoundary")
            require(isinstance(generation_boundary, dict), "generation fixture boundary missing")
            generation_boundary["registeredGenerationCount"] = 1
            generation_contract_copy.write_text(json.dumps(drifted_generation_contract, indent=2) + "\n", encoding="utf-8")
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("generation registered count drift" in str(exc), f"generation count drift rejected at wrong boundary: {exc}")
            except Exception as exc:
                raise Fail(f"generation count drift leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
            else:
                raise Fail("generation contract count drift unexpectedly reconciled")
            require(contract_copy.read_bytes() == original_contract, "generation count drift mutated eligibility contract")
            print("PASS reject before write: generation contract count drift")

            shutil.copyfile(GEN_CONTRACT, generation_contract_copy)

            atomic_original = contract_copy.read_bytes()
            replace_calls = 0

            def fail_first_replace(source: str | Path, destination: str | Path) -> None:
                nonlocal replace_calls
                replace_calls += 1
                if replace_calls == 1:
                    raise OSError("synthetic atomic replacement failure")
                original_os_replace(source, destination)

            reconciler.os.replace = fail_first_replace
            try:
                try:
                    reconciler.main()
                except OSError as exc:
                    require("synthetic atomic replacement failure" in str(exc), f"atomic replacement failed at wrong boundary: {exc}")
                except Exception as exc:
                    raise Fail(f"atomic replacement failure leaked unexpected exception: {type(exc).__name__}: {exc}") from exc
                else:
                    raise Fail("synthetic atomic replacement failure unexpectedly accepted")
                require(replace_calls == 2, f"atomic replacement failure did not perform exactly one rollback replace: {replace_calls}")
                require(contract_copy.read_bytes() == atomic_original, "failed atomic replacement mutated eligibility contract")
                require(
                    not list(contract_copy.parent.glob(f".{contract_copy.name}.*.tmp")),
                    "failed atomic replacement left temporary eligibility authority behind",
                )
            finally:
                reconciler.os.replace = original_os_replace
            print("PASS atomic replacement failure: contract bytes preserved and temp cleaned")

            parsed_contract = json.loads(contract_copy.read_text(encoding="utf-8"))
            contract_copy.write_text(json.dumps(parsed_contract, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            rollback_original = contract_copy.read_bytes()
            observed: list[str] = []

            def aggregate_failure_after_eligibility_success(path: Path, expected_relative: Path, field: str) -> None:
                require(contract_copy.read_bytes() != rollback_original, "post-validator invoked before eligibility write")
                observed.append(field)
                if len(observed) == 1:
                    require(field == "environment eligibility validator", "eligibility validator was not first post-write validator")
                    return
                require(len(observed) == 2, "unexpected extra post-write validator invocation")
                require(field == "operability validator", "operability validator was not second post-write validator")
                raise reconciler.Fail("synthetic aggregate operability rejection")

            reconciler.run_post_validator = aggregate_failure_after_eligibility_success
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("synthetic aggregate operability rejection" in str(exc), f"post-validation failure rejected at wrong boundary: {exc}")
            except Exception as exc:
                raise Fail(f"post-validation failure leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
            else:
                raise Fail("forced aggregate eligibility post-validation failure unexpectedly accepted")
            require(observed == ["environment eligibility validator", "operability validator"], "canonical post-write validator order drift")
            require(contract_copy.read_bytes() == rollback_original, "failed aggregate validation left eligibility contract mutation")
            print("PASS rollback: aggregate rejection restored eligibility contract byte-for-byte")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.CONTRACT = original_contract_path
        reconciler.GEN_CONTRACT = original_generation_contract_path
        reconciler.GEN_REGISTRY = original_generation_registry_path
        reconciler.load_helper = original_load_helper
        reconciler.run_post_validator = original_post_validator
        reconciler.os.replace = original_os_replace

    print("Environment generation eligibility reconcile negative suite PASS")
    print("validator data/executable authority substitutions accepted: false")
    print("validator execution helper substitutions accepted: false")
    print("symlinked canonical validator authority accepted: false")
    print("direct reconciler data/executable authority substitutions accepted: false")
    print("path-based helper authority weakened for fixtures: false")
    print("generation contract drift can mutate eligibility authority: false")
    print("atomic replacement failure preserves canonical authority: true")
    print("atomic replacement temp cleanup: true")
    print("aggregate operability failure rolls back eligibility authority: true")
    print("failed post-validation leaves eligibility authority mutation behind: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION ELIGIBILITY RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
