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

_CANONICAL_ROOT = ROOT
_CANONICAL_DEFAULT_LEDGER = _CANONICAL_ROOT / "docs/evidence/migration-operations"
_CANONICAL_VALIDATOR = _CANONICAL_ROOT / "scripts/validate-memory-os-migration-operation-evidence.py"

CANONICAL_DEFAULT_LEDGER = _CANONICAL_DEFAULT_LEDGER
CANONICAL_VALIDATOR = _CANONICAL_VALIDATOR
DEFAULT_LEDGER = _CANONICAL_DEFAULT_LEDGER
VALIDATOR = _CANONICAL_VALIDATOR


def require_actual_cli_authorities(
    _canonical_root: Path = _CANONICAL_ROOT,
    _canonical_default_ledger: Path = _CANONICAL_DEFAULT_LEDGER,
    _canonical_validator: Path = _CANONICAL_VALIDATOR,
    _canonical_subprocess_run=subprocess.run,
    _canonical_load_json=load_json,
    _canonical_validate_record=validate_record,
    _canonical_expected_filename=expected_filename,
) -> None:
    if ROOT != _canonical_root:
        raise EvidenceValidationError("migration operation CLI repository authority substitution rejected")
    if CANONICAL_DEFAULT_LEDGER != _canonical_default_ledger:
        raise EvidenceValidationError("migration operation CLI canonical ledger authority substitution rejected")
    if CANONICAL_VALIDATOR != _canonical_validator:
        raise EvidenceValidationError("migration operation CLI canonical validator authority substitution rejected")
    if DEFAULT_LEDGER != _canonical_default_ledger:
        raise EvidenceValidationError("migration operation CLI default ledger authority substitution rejected")
    if VALIDATOR != _canonical_validator:
        raise EvidenceValidationError("migration operation CLI validator authority substitution rejected")
    if subprocess.run is not _canonical_subprocess_run:
        raise EvidenceValidationError("migration operation CLI subprocess transport substitution rejected")
    if load_json is not _canonical_load_json:
        raise EvidenceValidationError("migration operation CLI JSON loader authority substitution rejected")
    if validate_record is not _canonical_validate_record:
        raise EvidenceValidationError("migration operation CLI record validator authority substitution rejected")
    if expected_filename is not _canonical_expected_filename:
        raise EvidenceValidationError("migration operation CLI filename authority substitution rejected")

    for path, expected, label in (
        (DEFAULT_LEDGER, _canonical_default_ledger, "default ledger"),
        (VALIDATOR, _canonical_validator, "validator"),
    ):
        if path.is_symlink():
            raise EvidenceValidationError(f"migration operation CLI {label} authority must be symlink-free")
        try:
            resolved = path.resolve(strict=True)
            expected_resolved = expected.resolve(strict=True)
        except FileNotFoundError as exc:
            raise EvidenceValidationError(f"migration operation CLI canonical {label} authority missing") from exc
        if resolved != expected_resolved:
            raise EvidenceValidationError(f"migration operation CLI {label} authority drift")


def run_canonical_validator(
    _canonical_run=subprocess.run,
    _canonical_validator: Path = _CANONICAL_VALIDATOR,
    _canonical_root: Path = _CANONICAL_ROOT,
) -> None:
    if subprocess.run is not _canonical_run:
        raise EvidenceValidationError("migration operation validator subprocess transport substitution rejected")
    if VALIDATOR != _canonical_validator or ROOT != _canonical_root:
        raise EvidenceValidationError("migration operation canonical validator execution authority drift")
    completed = _canonical_run(
        [sys.executable, str(_canonical_validator)],
        cwd=_canonical_root,
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


def validate_canonical_ledger_before_append(
    ledger: Path,
    _canonical_runner=run_canonical_validator,
) -> None:
    if ledger.resolve() != _CANONICAL_DEFAULT_LEDGER.resolve():
        return
    if run_canonical_validator is not _canonical_runner:
        raise EvidenceValidationError("migration operation pre-append runner authority substitution rejected")
    try:
        _canonical_runner()
    except EvidenceValidationError as exc:
        detail = str(exc).removeprefix("canonical migration operation ledger failed validation")
        raise EvidenceValidationError(
            "canonical migration operation ledger failed validation before append" + detail
        ) from exc


def validate_canonical_ledger_after_append(
    ledger: Path,
    _canonical_runner=run_canonical_validator,
) -> None:
    if ledger.resolve() != _CANONICAL_DEFAULT_LEDGER.resolve():
        return
    if run_canonical_validator is not _canonical_runner:
        raise EvidenceValidationError("migration operation post-append runner authority substitution rejected")
    try:
        _canonical_runner()
    except EvidenceValidationError as exc:
        detail = str(exc).removeprefix("canonical migration operation ledger failed validation")
        raise EvidenceValidationError(
            "canonical migration operation ledger failed validation after append" + detail
        ) from exc


def append_record(
    record_path: Path,
    ledger: Path,
    *,
    before_validator=validate_canonical_ledger_before_append,
    after_validator=validate_canonical_ledger_after_append,
    record_loader=load_json,
    record_validator=validate_record,
    filename_builder=expected_filename,
) -> Path:
    record = record_loader(record_path)
    record_validator(record)
    before_validator(ledger)
    ledger.mkdir(parents=True, exist_ok=True)
    target = ledger / filename_builder(record)
    payload = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    try:
        with target.open("x", encoding="utf-8") as handle:
            handle.write(payload)
    except FileExistsError as exc:
        raise EvidenceValidationError(
            f"migrationRunId already exists and cannot be overwritten: {record['migrationRunId']}"
        ) from exc

    try:
        after_validator(ledger)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def main(
    _canonical_guard=require_actual_cli_authorities,
    _canonical_append=append_record,
    _canonical_before=validate_canonical_ledger_before_append,
    _canonical_after=validate_canonical_ledger_after_append,
    _canonical_runner=run_canonical_validator,
) -> int:
    if require_actual_cli_authorities is not _canonical_guard:
        raise EvidenceValidationError("migration operation CLI guard authority substitution rejected")
    if append_record is not _canonical_append:
        raise EvidenceValidationError("migration operation CLI append authority substitution rejected")
    if validate_canonical_ledger_before_append is not _canonical_before:
        raise EvidenceValidationError("migration operation pre-append validator authority substitution rejected")
    if validate_canonical_ledger_after_append is not _canonical_after:
        raise EvidenceValidationError("migration operation post-append validator authority substitution rejected")
    if run_canonical_validator is not _canonical_runner:
        raise EvidenceValidationError("migration operation canonical runner authority substitution rejected")
    _canonical_guard()

    parser = argparse.ArgumentParser()
    parser.add_argument("record", help="path to the JSON record to append")
    parser.add_argument("--ledger-dir", default=str(_CANONICAL_DEFAULT_LEDGER))
    args = parser.parse_args()

    record_path = Path(args.record)
    if not record_path.is_absolute():
        record_path = Path.cwd() / record_path
    ledger = Path(args.ledger_dir)
    if not ledger.is_absolute():
        ledger = Path.cwd() / ledger

    target = _canonical_append(
        record_path,
        ledger,
        before_validator=_canonical_before,
        after_validator=_canonical_after,
        record_loader=load_json,
        record_validator=validate_record,
        filename_builder=expected_filename,
    )
    print(f"Created append-only migration operation evidence: {target}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except EvidenceValidationError as exc:
        print(f"MIGRATION OPERATION EVIDENCE CREATE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
