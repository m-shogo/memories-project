#!/usr/bin/env python3
"""Canonical migration rehearsal-ledger binding for production-shaped admission."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
LEDGER_VALIDATOR = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"


class LedgerBindingFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LedgerBindingFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise LedgerBindingFailure(f"cannot load canonical migration ledger: {exc}") from exc
    require(isinstance(value, dict), "canonical migration ledger root must be object")
    return value


def validate_canonical_ledger() -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(LEDGER_VALIDATOR)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    require(completed.returncode == 0, "canonical migration rehearsal ledger validation failed")
    return load(LEDGER)


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
