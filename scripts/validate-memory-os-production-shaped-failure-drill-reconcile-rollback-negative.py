#!/usr/bin/env python3
"""Prove failure-drill reconcile is transactional, monotonic, and exact-authority bound."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-shaped-failure-drill-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/production-shaped-failure-drill-registry.v1.json"
WORKFLOW = ROOT / ".github/workflows/production-shaped-failure-drills.yml"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-shaped-failure-drills.py"
SUBSTITUTE = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def temp_names(path: Path) -> set[str]:
    return {candidate.name for candidate in path.parent.glob(f".{path.name}.*.tmp")}


def restore(path: Path, data: bytes, original_mode: int) -> None:
    path.write_bytes(data)
    os.chmod(path, original_mode)


def status_gate(status: dict[str, Any]) -> dict[str, Any]:
    gate = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-009"), None)
    if not isinstance(gate, dict):
        raise RuntimeError("OPS-P0-009 missing in test status")
    return gate


def prove_authority_substitutions(reconciler: Any, contract_before: bytes, status_before: bytes) -> None:
    cases = (
        ("CONTRACT", "failure-drill contract authority drift"),
        ("REGISTRY", "failure-drill registry authority drift"),
        ("WRITER", "failure-drill writer authority drift"),
        ("VALIDATOR", "failure-drill validator authority drift"),
        ("WORKFLOW", "failure-drill workflow authority drift"),
        ("STATUS", "production operability status authority drift"),
        ("CHAOS_VALIDATOR", "chaos validator authority drift"),
        ("OPERABILITY_VALIDATOR", "operability validator authority drift"),
    )
    for attr, expected in cases:
        original = getattr(reconciler, attr)
        try:
            setattr(reconciler, attr, SUBSTITUTE)
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.Fail as exc:
                if expected not in str(exc):
                    raise RuntimeError(f"unexpected {attr} authority rejection: {exc}") from exc
            else:
                raise RuntimeError(f"reconciler accepted substituted authority: {attr}")
            if CONTRACT.read_bytes() != contract_before:
                raise RuntimeError(f"{attr}: authority rejection mutated failure-drill contract")
            if STATUS.read_bytes() != status_before:
                raise RuntimeError(f"{attr}: authority rejection mutated production status")
        finally:
            setattr(reconciler, attr, original)


def prove_corrupt_status_rollback(reconciler: Any, contract_before: bytes, status_before: bytes) -> None:
    status = json.loads(status_before.decode("utf-8"))
    status["productionDecision"] = "GO"
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    corrupt_status = STATUS.read_bytes()
    try:
        try:
            reconciler.main()
        except reconciler.Fail:
            pass
        else:
            raise RuntimeError("reconciler accepted productionDecision=GO")
        if CONTRACT.read_bytes() != contract_before:
            raise RuntimeError("reconciler partially mutated failure-drill contract before rejecting status")
        if STATUS.read_bytes() != corrupt_status:
            raise RuntimeError("reconciler mutated corrupt production status while rejecting it")
    finally:
        CONTRACT.write_bytes(contract_before)
        STATUS.write_bytes(status_before)


def prove_second_replace_rollback(reconciler: Any, contract_before: bytes, status_before: bytes) -> None:
    contract_mode = mode(CONTRACT)
    status_mode = mode(STATUS)
    contract_temps = temp_names(CONTRACT)
    status_temps = temp_names(STATUS)
    original_replace = reconciler.os.replace
    replace_count = 0

    def fail_second_replace(source: str, destination: Path) -> None:
        nonlocal replace_count
        replace_count += 1
        if replace_count == 2:
            raise OSError("synthetic second authority replace rejection")
        original_replace(source, destination)

    try:
        os.chmod(CONTRACT, 0o640)
        os.chmod(STATUS, 0o640)
        reconciler.os.replace = fail_second_replace
        try:
            reconciler.main()
        except reconciler.Fail:
            pass
        else:
            raise RuntimeError("reconciler accepted second authority replace rejection")
        if replace_count < 2:
            raise RuntimeError("reconciler did not attempt both canonical authority replacements")
        if CONTRACT.read_bytes() != contract_before or STATUS.read_bytes() != status_before:
            raise RuntimeError("reconciler retained partial bytes after second authority replace rejection")
        if mode(CONTRACT) != 0o640 or mode(STATUS) != 0o640:
            raise RuntimeError("reconciler changed authority mode during second replace rollback")
        if temp_names(CONTRACT) != contract_temps or temp_names(STATUS) != status_temps:
            raise RuntimeError("reconciler left temp residue after second authority replace rejection")
    finally:
        reconciler.os.replace = original_replace
        restore(CONTRACT, contract_before, contract_mode)
        restore(STATUS, status_before, status_mode)


def prove_aggregate_validator_rollback(reconciler: Any, contract_before: bytes, status_before: bytes) -> None:
    original_run = reconciler.subprocess.run
    contract_mode = mode(CONTRACT)
    status_mode = mode(STATUS)
    contract_temps = temp_names(CONTRACT)
    status_temps = temp_names(STATUS)
    calls: list[Path] = []

    class Result:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command: list[str], **_: Any) -> Result:
        path = Path(command[1]).resolve()
        calls.append(path)
        if path == reconciler.CHAOS_VALIDATOR.resolve():
            return Result(1, stderr="synthetic chaos aggregate rejection")
        return Result(0)

    reconciler.subprocess.run = fake_run
    try:
        os.chmod(CONTRACT, 0o640)
        os.chmod(STATUS, 0o640)
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            if "chaos authority rejected after failure-drill reconcile" not in str(exc):
                raise RuntimeError(f"unexpected aggregate rejection: {exc}") from exc
        else:
            raise RuntimeError("reconciler accepted rejected chaos aggregate authority")
        if reconciler.CHAOS_VALIDATOR.resolve() not in calls:
            raise RuntimeError("reconciler did not invoke canonical chaos aggregate validator")
        if reconciler.OPERABILITY_VALIDATOR.resolve() in calls:
            raise RuntimeError("reconciler continued after chaos aggregate rejection")
        if CONTRACT.read_bytes() != contract_before:
            raise RuntimeError("reconciler retained failure-drill contract after chaos aggregate rejection")
        if STATUS.read_bytes() != status_before:
            raise RuntimeError("reconciler retained production status after chaos aggregate rejection")
        if mode(CONTRACT) != 0o640 or mode(STATUS) != 0o640:
            raise RuntimeError("reconciler aggregate rollback did not preserve authority modes")
        if temp_names(CONTRACT) != contract_temps or temp_names(STATUS) != status_temps:
            raise RuntimeError("reconciler aggregate rollback left temp residue")
    finally:
        reconciler.subprocess.run = original_run
        restore(CONTRACT, contract_before, contract_mode)
        restore(STATUS, status_before, status_mode)


def prove_legacy_empty_evidence_is_monotonic(reconciler: Any, contract_before: bytes, status_before: bytes) -> None:
    contract_mode = mode(CONTRACT)
    status_mode = mode(STATUS)
    status = json.loads(status_before.decode("utf-8"))
    gate = status_gate(status)
    existing = gate.get("existingEvidence")
    if not isinstance(existing, list):
        raise RuntimeError("OPS-P0-009 existingEvidence missing")
    existing[:] = [value for value in existing if value not in {reconciler.LEGACY_EMPTY_EVIDENCE, reconciler.EVIDENCE}]
    existing.append(reconciler.LEGACY_EMPTY_EVIDENCE)
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        reconciler.main()
        reconciled = json.loads(STATUS.read_text(encoding="utf-8"))
        reconciled_gate = status_gate(reconciled)
        reconciled_existing = reconciled_gate.get("existingEvidence")
        if not isinstance(reconciled_existing, list):
            raise RuntimeError("reconciled OPS-P0-009 existingEvidence missing")
        if reconciler.LEGACY_EMPTY_EVIDENCE in reconciled_existing:
            raise RuntimeError("reconciler retained superseded empty-registry evidence")
        if reconciler.EVIDENCE not in reconciled_existing:
            raise RuntimeError("reconciler did not install stable registry-derived evidence")
        if reconciled.get("productionDecision") != "NO_GO":
            raise RuntimeError("evidence normalization changed productionDecision")
        if mode(CONTRACT) != contract_mode or mode(STATUS) != status_mode:
            raise RuntimeError("successful failure-drill reconcile changed canonical authority mode")
    finally:
        restore(CONTRACT, contract_before, contract_mode)
        restore(STATUS, status_before, status_mode)


def main() -> int:
    reconciler = load_module(RECONCILER, "failure_drill_reconcile_rollback_negative")
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()
    contract_mode = mode(CONTRACT)
    status_mode = mode(STATUS)
    try:
        prove_authority_substitutions(reconciler, contract_before, status_before)
        prove_corrupt_status_rollback(reconciler, contract_before, status_before)
        prove_second_replace_rollback(reconciler, contract_before, status_before)
        prove_aggregate_validator_rollback(reconciler, contract_before, status_before)
        prove_legacy_empty_evidence_is_monotonic(reconciler, contract_before, status_before)
    finally:
        restore(CONTRACT, contract_before, contract_mode)
        restore(STATUS, status_before, status_mode)

    print("PASS: failure-drill reconcile is exact-authority bound, mode-preserving and transactional across second-replace/direct/aggregate failures, and removes superseded empty-registry evidence")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
