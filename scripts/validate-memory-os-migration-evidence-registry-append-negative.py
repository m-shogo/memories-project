#!/usr/bin/env python3
"""Fail-closed corruption negatives for the append-only migration rehearsal ledger."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-migration-rehearsal-evidence.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-evidence-registry.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_migration_rehearsal_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load migration rehearsal writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_writer_rejected(writer: ModuleType, contract: dict[str, Any], name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    corrupt = copy.deepcopy(load_json(REGISTRY))
    mutate(corrupt)
    try:
        writer.validate_registry_for_append(corrupt, contract)
    except Exception:
        return
    raise Fail(f"writer accepted corrupt migration ledger: {name}")


def expect_reconcile_rejected_without_mutation(name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    originals = {path: path.read_bytes() for path in (REGISTRY, CONTRACT, LIFECYCLE, STATUS)}
    corrupt = load_json(REGISTRY)
    mutate(corrupt)
    REGISTRY.write_text(json.dumps(corrupt, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, f"reconciler auto-healed corrupt migration ledger: {name}")
        for path in (CONTRACT, LIFECYCLE, STATUS):
            require(path.read_bytes() == originals[path], f"reconciler mutated {path.relative_to(ROOT)} after rejecting {name}")
    finally:
        for path, data in originals.items():
            path.write_bytes(data)


def main() -> int:
    writer = load_writer()
    contract = load_json(CONTRACT)
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        ("registry class drift", lambda value: value.__setitem__("registryClass", "PRODUCTION_MIGRATION_EVIDENCE")),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("boolean rehearsal count", lambda value: value.__setitem__("rehearsalEvidenceCount", True)),
        ("rehearsal count drift", lambda value: value.__setitem__("rehearsalEvidenceCount", len(value.get("records", [])) + 1)),
        ("passing count drift", lambda value: value.__setitem__("passingRehearsalCount", 0)),
        ("production-equivalent count drift", lambda value: value.__setitem__("productionEquivalentRehearsalCount", 1)),
        ("latest pointer drift", lambda value: value.__setitem__("latestRehearsalRunId", "mig_20991231_invalid")),
        ("unknown registry field", lambda value: value.__setitem__("unexpected", True)),
    ]
    for name, mutate in cases:
        expect_writer_rejected(writer, contract, name, mutate)
        expect_reconcile_rejected_without_mutation(name, mutate)
    print("PASS: migration rehearsal ledger corruption is rejected before append/reconcile")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION EVIDENCE APPEND NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
