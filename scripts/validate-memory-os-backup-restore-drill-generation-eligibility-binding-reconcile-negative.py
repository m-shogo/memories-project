#!/usr/bin/env python3
"""Prove drill-generation binding reconcile is canonical and transactionally fail-closed."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-generation-eligibility-binding.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-generation-eligibility-binding-contract.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_drill_generation_binding_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load drill generation binding reconciler")
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
    canonical_registry: bytes,
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
        require(CONTRACT.read_bytes() == canonical_contract, f"canonical binding contract mutated while rejecting {name}")
        require(DRILL_REGISTRY.read_bytes() == canonical_registry, f"canonical drill registry mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_direct_authority_identity(reconciler: Any) -> None:
    canonical_contract = CONTRACT.read_bytes()
    canonical_registry = DRILL_REGISTRY.read_bytes()
    cases = (
        ("binding contract substitution", "drill generation binding contract", "CONTRACT", reconciler.DRILL_REGISTRY),
        ("drill registry substitution", "drill request registry", "DRILL_REGISTRY", reconciler.CONTRACT),
        ("drill writer substitution", "drill request writer", "DRILL_WRITER", reconciler.VALIDATOR),
        ("semantic helper substitution", "semantic generation eligibility helper", "ELIGIBILITY_HELPER", reconciler.DRILL_WRITER),
        ("binding validator substitution", "drill generation binding validator", "VALIDATOR", reconciler.OPERABILITY_VALIDATOR),
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
            canonical_registry=canonical_registry,
        )
    print(f"PASS boundary: direct semantic-binding data/executable substitutions rejected: {len(cases)}")


def main() -> int:
    require(RECONCILER.is_file(), "drill generation binding reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()
    prove_direct_authority_identity(reconciler)

    original_enforcer = reconciler.enforce_runtime_authorities
    original_contract_path = reconciler.CONTRACT
    original_registry_path = reconciler.DRILL_REGISTRY
    original_post_validator = reconciler.run_post_validator
    original_os_replace = reconciler.os.replace

    # Fixture mutation is deliberately below the production authority boundary:
    # direct invocation remains canonical-only, while this suite can still prove
    # append-only corruption rejection and transactional rollback internally.
    reconciler.enforce_runtime_authorities = lambda: None
    try:
        with tempfile.TemporaryDirectory(prefix=".tmp-drill-generation-binding-reconcile-", dir=TMP_PARENT) as tmpdir:
            tmp = Path(tmpdir)
            contract_copy = tmp / CONTRACT.name
            registry_copy = tmp / DRILL_REGISTRY.name
            shutil.copyfile(CONTRACT, contract_copy)
            shutil.copyfile(DRILL_REGISTRY, registry_copy)
            original_contract = contract_copy.read_bytes()
            canonical_registry: dict[str, Any] = json.loads(registry_copy.read_text(encoding="utf-8"))

            reconciler.CONTRACT = contract_copy
            reconciler.DRILL_REGISTRY = registry_copy

            corruption_cases: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
                ("request registry schema drift", lambda value: value.__setitem__("schemaVersion", "broken")),
                ("request registry class drift", lambda value: value.__setitem__("registryClass", "BROKEN")),
                ("request registry append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
                ("request registry production evidence promoted", lambda value: value.__setitem__("productionEvidence", True)),
                ("request registry production ready promoted", lambda value: value.__setitem__("productionReady", True)),
                ("registered request boolean count", lambda value: value.__setitem__("registeredRequestCount", True)),
                ("current executable boolean count", lambda value: value.__setitem__("currentExecutableRequestCount", True)),
                ("registered request count drift", lambda value: value.__setitem__("registeredRequestCount", len(value.get("requests", [])) + 1)),
                ("current executable count drift", lambda value: value.__setitem__("currentExecutableRequestCount", len(value.get("requests", [])) + 1)),
            )
            for name, mutate in corruption_cases:
                corrupted = json.loads(json.dumps(canonical_registry))
                mutate(corrupted)
                registry_copy.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")
                try:
                    reconciler.main()
                except reconciler.Fail as exc:
                    require("drill request append-only authority invalid" in str(exc), f"{name} rejected at wrong boundary: {exc}")
                except Exception as exc:
                    raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
                else:
                    raise Fail(f"corrupt drill request authority unexpectedly reconciled: {name}")
                require(contract_copy.read_bytes() == original_contract, f"{name} mutated semantic binding contract")
                print(f"PASS reject before reconcile: {name}")
            registry_copy.write_text(json.dumps(canonical_registry, indent=2) + "\n", encoding="utf-8")

            # A failed atomic replacement must never mutate the canonical contract,
            # and its temporary file must be removed before control returns.
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
                require(contract_copy.read_bytes() == atomic_original, "failed atomic replacement mutated semantic binding contract")
                require(
                    not list(contract_copy.parent.glob(f".{contract_copy.name}.*.tmp")),
                    "failed atomic replacement left temporary binding authority behind",
                )
            finally:
                reconciler.os.replace = original_os_replace
            print("PASS atomic replacement failure: contract bytes preserved and temp cleaned")

            # Make the contract byte-distinct but semantically equivalent so the
            # post-validator hook proves a write occurred before aggregate failure.
            parsed_contract = json.loads(contract_copy.read_text(encoding="utf-8"))
            contract_copy.write_text(json.dumps(parsed_contract, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            rollback_original = contract_copy.read_bytes()
            observed: list[str] = []

            def aggregate_failure_after_binding_success(path: Path, expected_relative: Path, field: str) -> None:
                require(contract_copy.read_bytes() != rollback_original, "post-validator invoked before semantic binding write")
                observed.append(field)
                if len(observed) == 1:
                    require(field == "drill generation binding validator", "binding validator was not first post-write validator")
                    return
                require(len(observed) == 2, "unexpected extra post-write validator invocation")
                require(field == "operability validator", "operability validator was not second post-write validator")
                raise reconciler.Fail("synthetic aggregate operability rejection")

            reconciler.run_post_validator = aggregate_failure_after_binding_success
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("synthetic aggregate operability rejection" in str(exc), f"post-validation failure rejected at wrong boundary: {exc}")
            except Exception as exc:
                raise Fail(f"post-validation failure leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
            else:
                raise Fail("forced aggregate semantic binding post-validation failure unexpectedly accepted")
            require(observed == ["drill generation binding validator", "operability validator"], "canonical post-write validator order drift")
            require(contract_copy.read_bytes() == rollback_original, "failed aggregate validation left binding contract mutation")
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.CONTRACT = original_contract_path
        reconciler.DRILL_REGISTRY = original_registry_path
        reconciler.run_post_validator = original_post_validator
        reconciler.os.replace = original_os_replace

    print("Drill generation eligibility binding reconcile negative suite PASS")
    print("direct data/executable authority substitutions accepted: false")
    print("corrupt planning authority can be auto-healed: false")
    print("atomic replacement failure preserves canonical authority: true")
    print("atomic replacement temp cleanup: true")
    print("aggregate operability failure rolls back binding authority: true")
    print("failed post-validation leaves binding authority mutation behind: false")
    print("request created: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL GENERATION BINDING RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
