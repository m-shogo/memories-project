#!/usr/bin/env python3
"""Reconcile drill-request binding to semantic environment-generation eligibility."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-drill-generation-eligibility-binding-contract.v1.json")
DRILL_REGISTRY_REL = Path("contracts/operations/backup-restore-drill-request-registry.v1.json")
DRILL_WRITER_REL = Path("scripts/request-memory-os-backup-restore-drill.py")
ELIGIBILITY_HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-drill-generation-eligibility-binding.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
CONTRACT = ROOT / CONTRACT_REL
DRILL_REGISTRY = ROOT / DRILL_REGISTRY_REL
DRILL_WRITER = ROOT / DRILL_WRITER_REL
ELIGIBILITY_HELPER = ROOT / ELIGIBILITY_HELPER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "drill generation binding contract"),
        (DRILL_REGISTRY, DRILL_REGISTRY_REL, "drill request registry"),
        (DRILL_WRITER, DRILL_WRITER_REL, "drill request writer"),
        (ELIGIBILITY_HELPER, ELIGIBILITY_HELPER_REL, "semantic generation eligibility helper"),
        (VALIDATOR, VALIDATOR_REL, "drill generation binding validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
    ):
        require_exact_repo_file(path, expected, field)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, expected_relative: Path, name: str, field: str):
    require_exact_repo_file(path, expected_relative, field)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_post_validator(path: Path, expected_relative: Path, field: str) -> None:
    require_exact_repo_file(path, expected_relative, field)
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"post-reconcile {field} failed:\n{completed.stdout[-9000:]}{completed.stderr[-9000:]}",
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    enforce_runtime_authorities()
    try:
        original_contract_text = CONTRACT.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {CONTRACT.relative_to(ROOT)}: {exc}") from exc
    contract = load(CONTRACT)
    registry = load(DRILL_REGISTRY)
    writer = load_module(
        DRILL_WRITER,
        DRILL_WRITER_REL,
        "memory_os_drill_writer_binding_reconcile",
        "drill request writer",
    )
    helper = load_module(
        ELIGIBILITY_HELPER,
        ELIGIBILITY_HELPER_REL,
        "memory_os_generation_eligibility_binding_reconcile",
        "semantic generation eligibility helper",
    )
    try:
        requests = writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"drill request append-only authority invalid: {exc}") from exc
    eligibility = helper.derive()
    pair_count = eligibility["eligibleDirectedPairCount"]
    request_count = registry["registeredRequestCount"]
    current_count = registry["currentExecutableRequestCount"]
    historical_count = len(requests)

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "binding currentBoundary missing")
    boundary["eligibleDirectedRestorePairCount"] = pair_count
    boundary["reviewedDrillRequestCount"] = request_count
    boundary["currentExecutableDrillRequestCount"] = current_count
    boundary["historicalAuditableRequestCount"] = historical_count
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"

    updated_contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    try:
        atomic_write_text(CONTRACT, updated_contract_text)
        run_post_validator(VALIDATOR, VALIDATOR_REL, "drill generation binding validator")
        run_post_validator(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    except Exception:
        try:
            atomic_write_text(CONTRACT, original_contract_text)
        except OSError as restore_exc:
            raise Fail(f"drill generation eligibility binding rollback failed: {restore_exc}") from restore_exc
        raise

    print("Memory OS drill request semantic generation binding reconciliation PASS")
    print(f"eligible directed restore pairs: {pair_count}")
    print(f"reviewed/current drill requests: {request_count}/{current_count}")
    print(f"historical auditable requests: {historical_count}")
    print("canonical data/executable authorities enforced: true")
    print("atomic contract replacement: true")
    print("aggregate operability validation inside transaction: true")
    print("failed post-validation leaves semantic binding authority mutation behind: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DRILL REQUEST GENERATION ELIGIBILITY BINDING RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
