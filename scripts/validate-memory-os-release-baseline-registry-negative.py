#!/usr/bin/env python3
"""Fail-closed corruption negatives for the append-only release baseline registry."""

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
CONTRACT = ROOT / "contracts/operations/release-baseline-registry-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/release-baseline-registry.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-release-baseline.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-release-baseline-registry.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_release_baseline_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load release baseline writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_writer_rejected(
    writer: ModuleType,
    contract: dict[str, Any],
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    corrupt = copy.deepcopy(load(REGISTRY))
    mutate(corrupt)
    try:
        writer.validate_registry_for_append(corrupt, contract)
    except Exception:
        return
    raise Fail(f"release writer accepted corrupt registry: {name}")


def expect_reconcile_rejected_without_mutation(
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    registry_before = REGISTRY.read_bytes()
    status_before = STATUS.read_bytes()
    corrupt = load(REGISTRY)
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
        require(completed.returncode != 0, f"release reconciler auto-healed corrupt registry: {name}")
        require(STATUS.read_bytes() == status_before, f"release reconciler mutated status after rejecting: {name}")
    finally:
        REGISTRY.write_bytes(registry_before)
        STATUS.write_bytes(status_before)


def main() -> int:
    writer = load_writer()
    contract = load(CONTRACT)
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        ("registry class drift", lambda value: value.__setitem__("registryClass", "CANDIDATE_RELEASES")),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("boolean approved count", lambda value: value.__setitem__("approvedReleaseCount", True)),
        ("approved count drift", lambda value: value.__setitem__("approvedReleaseCount", len(value.get("releases", [])) + 1)),
        ("latest approved pointer drift", lambda value: value.__setitem__("latestApprovedReleaseId", "rel_20991231_invalid")),
        ("latest rollback pointer drift", lambda value: value.__setitem__("latestRollbackEligibleReleaseId", "rel_20991231_invalid")),
        ("unknown registry field", lambda value: value.__setitem__("unexpectedAuthority", True)),
    ]
    for name, mutate in cases:
        expect_writer_rejected(writer, contract, name, mutate)
        expect_reconcile_rejected_without_mutation(name, mutate)
    print("PASS: release baseline registry corruption is rejected before append/reconcile")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE BASELINE REGISTRY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
