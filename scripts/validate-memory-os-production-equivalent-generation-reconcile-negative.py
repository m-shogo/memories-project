#!/usr/bin/env python3
"""Prove environment-generation reconciliation load boundaries and transactional rollback."""

from __future__ import annotations

import importlib.util
import json
import shutil
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


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    require(RECONCILER.is_file(), "environment generation reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

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

        contract_copy = tmp / CONTRACT.name
        registry_copy = tmp / REGISTRY.name
        status_copy = tmp / STATUS.name
        shutil.copyfile(CONTRACT, contract_copy)
        shutil.copyfile(REGISTRY, registry_copy)
        shutil.copyfile(STATUS, status_copy)
        reconciler.CONTRACT = contract_copy
        reconciler.REGISTRY = registry_copy
        reconciler.STATUS = status_copy
        original_contract = contract_copy.read_bytes()
        original_registry = registry_copy.read_bytes()
        original_status = status_copy.read_bytes()
        canonical_registry: dict[str, Any] = json.loads(original_registry.decode("utf-8"))

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
            corrupted = json.loads(json.dumps(canonical_registry))
            mutate(corrupted)
            registry_copy.write_text(json.dumps(corrupted, indent=2) + "\n", encoding="utf-8")
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("generation registry append-only authority invalid" in str(exc), f"{name} rejected at wrong boundary: {exc}")
            except Exception as exc:
                raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
            else:
                raise Fail(f"corrupt generation registry unexpectedly reconciled: {name}")
            require(contract_copy.read_bytes() == original_contract, f"{name} mutated generation contract")
            require(status_copy.read_bytes() == original_status, f"{name} mutated operability status")
            print(f"PASS reject before reconcile: {name}")
        registry_copy.write_bytes(original_registry)

        observed_commands: list[list[str]] = []

        def aggregate_failure_after_generation_success(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            command = [str(item) for item in (args[0] if args else [])]
            observed_commands.append(command)
            if len(observed_commands) == 1:
                require(command[-1] == str(reconciler.VALIDATOR), "generation validator was not first post-write validator")
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="synthetic generation validator success\n", stderr="")
            require(len(observed_commands) == 2, "unexpected extra generation post-write validator invocation")
            require(command[-1] == str(reconciler.OPERABILITY_VALIDATOR), "operability validator was not second post-write validator")
            return subprocess.CompletedProcess(args=command, returncode=31, stdout="synthetic operability failure\n", stderr="")

        real_run = reconciler.subprocess.run
        reconciler.subprocess.run = aggregate_failure_after_generation_success
        try:
            try:
                reconciler.main()
            except reconciler.Fail as exc:
                require("operability validator failed" in str(exc), f"unexpected reconcile failure: {exc}")
            else:
                raise Fail("forced operability post-validation failure unexpectedly accepted")
        finally:
            reconciler.subprocess.run = real_run

        require(len(observed_commands) == 2, "generation and operability validators were not both invoked")
        require(contract_copy.read_bytes() == original_contract, "generation contract rollback drift")
        require(registry_copy.read_bytes() == original_registry, "generation registry mutation drift")
        require(status_copy.read_bytes() == original_status, "operability status rollback drift")

    print("PASS rollback: environment generation contract/registry/status preserved byte-for-byte")
    print("generation validator succeeds before aggregate failure: true")
    print("aggregate operability failure triggers rollback: true")
    print("Environment generation reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
