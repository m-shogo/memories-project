#!/usr/bin/env python3
"""Prove drill-generation binding reconcile rejects corrupt planning authority transactionally."""

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


def main() -> int:
    require(RECONCILER.is_file(), "drill generation binding reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

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

        failing_validator = tmp / "forced-validator-failure.py"
        failing_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(43)\n", encoding="utf-8")
        reconciler.VALIDATOR = failing_validator
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("post-reconcile binding validator failed" in str(exc), f"post-validation failure rejected at wrong boundary: {exc}")
        except Exception as exc:
            raise Fail(f"post-validation failure leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
        else:
            raise Fail("forced semantic binding post-validation failure unexpectedly accepted")
        require(contract_copy.read_bytes() == original_contract, "failed semantic binding validation left contract mutation")

    print("Drill generation eligibility binding reconcile negative suite PASS")
    print("corrupt planning authority can be auto-healed: false")
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
