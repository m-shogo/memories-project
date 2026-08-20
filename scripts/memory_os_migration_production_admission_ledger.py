#!/usr/bin/env python3
"""Canonical migration rehearsal-ledger binding for production-shaped admission."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
LEDGER_CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
LEDGER_WRITER = ROOT / "scripts/register-memory-os-migration-rehearsal-evidence.py"
LEDGER_VALIDATOR = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"
LEDGER_LOCK = ROOT / "contracts/operations/.migration-evidence-registry.lock"
LEDGER_WRITER_REL = Path("scripts/register-memory-os-migration-rehearsal-evidence.py")
LEDGER_VALIDATOR_REL = Path("scripts/validate-memory-os-migration-evidence-registry.py")


class LedgerBindingFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LedgerBindingFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise LedgerBindingFailure(f"cannot load canonical migration ledger authority: {exc}") from exc
    require(isinstance(value, dict), "canonical migration ledger authority root must be object")
    return value


def canonical_repo_file(path: Path, relative: Path, label: str) -> Path:
    expected = ROOT / relative
    require(path == expected, f"canonical {label} executable authority drift")
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise LedgerBindingFailure(f"canonical {label} missing or escapes repository") from exc
    require(resolved == relative and path.is_file(), f"canonical {label} must resolve to repository file")
    return path


def load_writer() -> ModuleType:
    writer_path = canonical_repo_file(LEDGER_WRITER, LEDGER_WRITER_REL, "migration rehearsal writer")
    spec = importlib.util.spec_from_file_location("memory_os_migration_rehearsal_writer_for_admission", writer_path)
    require(spec is not None and spec.loader is not None, "cannot load canonical migration rehearsal writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "REGISTRY", None) == LEDGER, "canonical migration rehearsal writer registry authority drift")
    require(getattr(module, "CONTRACT", None) == LEDGER_CONTRACT, "canonical migration rehearsal writer contract authority drift")
    require(getattr(module, "LOCK", None) == LEDGER_LOCK, "canonical migration rehearsal writer append lock authority drift")
    require(callable(getattr(module, "validate_registry_for_append", None)), "canonical migration rehearsal registry validator missing")
    return module


def validate_canonical_ledger() -> dict[str, Any]:
    validator_path = canonical_repo_file(LEDGER_VALIDATOR, LEDGER_VALIDATOR_REL, "migration rehearsal validator")
    completed = subprocess.run(
        [sys.executable, str(validator_path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(completed.returncode == 0, "canonical migration rehearsal ledger validation failed")
    ledger = load(LEDGER)
    contract = load(LEDGER_CONTRACT)
    writer = load_writer()
    try:
        writer.validate_registry_for_append(ledger, contract)
    except Exception as exc:
        raise LedgerBindingFailure(f"canonical migration rehearsal append-only authority invalid: {exc}") from exc
    return ledger


def require_registered_production_equivalent_rehearsal(
    *, migration_run_id: str, source_commit_sha: str, environment_generation_id: str
) -> dict[str, Any]:
    ledger = validate_canonical_ledger()
    records = ledger.get("records")
    require(isinstance(records, list), "canonical migration ledger records missing")
    matches = [
        row for row in records
        if isinstance(row, dict) and row.get("migrationRunId") == migration_run_id
    ]
    require(len(matches) == 1, "migrationRunId is not registered exactly once in canonical migration ledger")
    row = matches[0]
    require(
        row.get("environmentClass") == "PRODUCTION_EQUIVALENT_REHEARSAL",
        "canonical migration ledger row is not production-equivalent rehearsal class",
    )
    require(row.get("sourceCommitSha") == source_commit_sha, "canonical migration ledger source commit mismatch")
    require(
        row.get("environmentGenerationId") == environment_generation_id,
        "canonical migration ledger environment generation mismatch",
    )
    require(row.get("productionTraffic") is False, "canonical migration ledger row used production traffic")
    require(row.get("productionCredentials") is False, "canonical migration ledger row used production credentials")
    require(row.get("productionEvidence") is False, "canonical migration ledger row cannot already be production evidence")
    return row
