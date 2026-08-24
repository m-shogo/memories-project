#!/usr/bin/env python3
"""Create one append-only migration operation evidence record."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from migration_operation_evidence_lib import (
    EvidenceValidationError,
    ROOT,
    expected_filename,
    load_json,
    validate_record,
)

CANONICAL_DEFAULT_LEDGER = ROOT / "docs/evidence/migration-operations"
CANONICAL_VALIDATOR = ROOT / "scripts/validate-memory-os-migration-operation-evidence.py"
DEFAULT_LEDGER = CANONICAL_DEFAULT_LEDGER
VALIDATOR = CANONICAL_VALIDATOR


def require_actual_cli_authorities() -> None:
    if DEFAULT_LEDGER != CANONICAL_DEFAULT_LEDGER:
        raise EvidenceValidationError("migration operation CLI default ledger authority substitution rejected")
    if VALIDATOR != CANONICAL_VALIDATOR:
        raise EvidenceValidationError("migration operation CLI validator authority substitution rejected")
    if DEFAULT_LEDGER.is_symlink():
        raise EvidenceValidationError("migration operation CLI default ledger authority must be symlink-free")
    if VALIDATOR.is_symlink():
        raise EvidenceValidationError("migration operation CLI validator authority must be symlink-free")
    try:
        if DEFAULT_LEDGER.resolve(strict=True) != CANONICAL_DEFAULT_LEDGER.resolve(strict=True):
            raise EvidenceValidationError("migration operation CLI default ledger authority drift")
        if VALIDATOR.resolve(strict=True) != CANONICAL_VALIDATOR.resolve(strict=True):
            raise EvidenceValidationError("migration operation CLI validator authority drift")
    except FileNotFoundError as exc:
        raise EvidenceValidationError("migration operation CLI canonical authority missing") from exc


def run_canonical_validator() -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise EvidenceValidationError(
            "canonical migration operation ledger failed validation"
            + (f": {detail}" if detail else "")
        )


def validate_canonical_ledger_before_append(ledger: Path) -> None:
    if ledger.resolve() != DEFAULT_LEDGER.resolve():
        return
    try:
        run_canonical_validator()
    except EvidenceValidationError as exc:
        detail = str(exc).removeprefix("canonical migration operation ledger failed validation")
        raise EvidenceValidationError(
            "canonical migration operation ledger failed validation before append" + detail
        ) from exc


def validate_canonical_ledger_after_append(ledger: Path) -> None:
    if ledger.resolve() != DEFAULT_LEDGER.resolve():
        return
    try:
        run_canonical_validator()
    except EvidenceValidationError as exc:
        detail = str(exc).removeprefix("canonical migration operation ledger failed validation")
        raise EvidenceValidationError(
            "canonical migration operation ledger failed validation after append" + detail
        ) from exc


def main() -> int:
    require_actual_cli_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("record", help="path to the JSON record to append")
    parser.add_argument("--ledger-dir", default=str(DEFAULT_LEDGER))
    args = parser.parse_args()

    record_path = Path(args.record)
    if not record_path.is_absolute():
        record_path = Path.cwd() / record_path
    record = load_json(record_path)
    validate_record(record)

    ledger = Path(args.ledger_dir)
    if not ledger.is_absolute():
        ledger = Path.cwd() / ledger
    validate_canonical_ledger_before_append(ledger)
    ledger.mkdir(parents=True, exist_ok=True)
    target = ledger / expected_filename(record)
    payload = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise EvidenceValidationError(
            f"migrationRunId already exists and cannot be overwritten: {record['migrationRunId']}"
        ) from exc

    try:
        validate_canonical_ledger_after_append(ledger)
    except Exception:
        target.unlink(missing_ok=True)
        raise

    print(f"Created append-only migration operation evidence: {target}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceValidationError as exc:
        print(f"MIGRATION OPERATION EVIDENCE CREATE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
