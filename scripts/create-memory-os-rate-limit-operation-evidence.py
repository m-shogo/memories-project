#!/usr/bin/env python3
"""Exclusively create one validated rate-limit operation evidence record."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

_CANONICAL_ROOT = Path(__file__).resolve().parents[1]
_CANONICAL_VALIDATOR_PATH = _CANONICAL_ROOT / "scripts/validate-memory-os-rate-limit-operation-evidence.py"
_CANONICAL_DEFAULT_LEDGER = _CANONICAL_ROOT / "docs/evidence/rate-limit-operations"

ROOT = _CANONICAL_ROOT
VALIDATOR_PATH = _CANONICAL_VALIDATOR_PATH
DEFAULT_LEDGER = _CANONICAL_DEFAULT_LEDGER
REQUIRED_APPEND_GUARDS = {
    "canonicalLedgerMustValidateBeforeAppend",
    "canonicalLedgerMustValidateAfterAppend",
    "postAppendValidationFailureMustRemoveNewRecord",
}


class WriterFailure(RuntimeError):
    pass


def require_cli_authorities(
    _canonical_root: Path = _CANONICAL_ROOT,
    _canonical_validator_path: Path = _CANONICAL_VALIDATOR_PATH,
    _canonical_default_ledger: Path = _CANONICAL_DEFAULT_LEDGER,
) -> None:
    expected = (
        ("ROOT", ROOT, _canonical_root),
        ("VALIDATOR_PATH", VALIDATOR_PATH, _canonical_validator_path),
        ("DEFAULT_LEDGER", DEFAULT_LEDGER, _canonical_default_ledger),
    )
    for label, actual, canonical in expected:
        if actual != canonical:
            raise WriterFailure(f"{label} authority must remain canonical")
        if actual.is_symlink():
            raise WriterFailure(f"{label} authority cannot be a symlink")
        try:
            resolved = actual.resolve(strict=True)
        except FileNotFoundError:
            if label == "DEFAULT_LEDGER":
                parent = actual.parent.resolve(strict=True)
                resolved = parent / actual.name
            else:
                raise WriterFailure(f"{label} authority does not exist")
        canonical_resolved = canonical.resolve(strict=label != "DEFAULT_LEDGER")
        if resolved != canonical_resolved:
            raise WriterFailure(f"{label} authority resolved path drift")


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operation_validator", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise WriterFailure("unable to load operation evidence validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_cli_execution_authority(_canonical_loader=load_validator) -> None:
    require_cli_authorities()
    if load_validator is not _canonical_loader:
        raise WriterFailure("operation evidence validator loader authority drift")


def load_input(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WriterFailure(f"input file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WriterFailure(f"input is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise WriterFailure("input JSON root must be an object")
    return value


def validate_contract_append_guards(contract: dict[str, Any]) -> None:
    guards = contract.get("appendOnlyGuards")
    if not isinstance(guards, dict) or set(guards) != REQUIRED_APPEND_GUARDS:
        raise WriterFailure("appendOnlyGuards authority field set drift")
    for guard in sorted(REQUIRED_APPEND_GUARDS):
        if guards.get(guard) is not True:
            raise WriterFailure(f"appendOnlyGuards.{guard} must be true")


def validate_canonical_authority(
    validator: ModuleType,
    ledger: Path,
    *,
    phase: str,
    _canonical_default_ledger: Path = _CANONICAL_DEFAULT_LEDGER,
) -> None:
    if ledger != _canonical_default_ledger.resolve():
        return
    try:
        result = validator.main()
    except validator.ValidationFailure as exc:
        raise WriterFailure(
            f"canonical ledger authority failed validation {phase}: {exc}"
        ) from exc
    if result != 0:
        raise WriterFailure(
            f"canonical ledger authority validation returned non-zero {phase}: {result}"
        )


def validate_existing_canonical_authority(validator: ModuleType, ledger: Path) -> None:
    validate_canonical_authority(validator, ledger, phase="before append")


def append_record(
    input_path: Path,
    ledger_dir: Path,
    validator: ModuleType,
    _canonical_root: Path = _CANONICAL_ROOT,
    _canonical_default_ledger: Path = _CANONICAL_DEFAULT_LEDGER,
) -> Path:
    record = load_input(input_path)
    contract, policy_ids = validator.load_contract_context()
    validate_contract_append_guards(contract)
    try:
        validator.validate_record(record, contract, policy_ids, writer_input=True)
        record["evidenceDigestsByRef"] = validator.expected_evidence_digests(record)
        validator.validate_record(record, contract, policy_ids)
    except validator.ValidationFailure as exc:
        raise WriterFailure(str(exc)) from exc

    ledger = ledger_dir.resolve()
    allowed_root = _canonical_root.resolve()
    if ledger != _canonical_default_ledger.resolve():
        temp_root = Path(os.environ.get("TMPDIR", "/tmp")).resolve()
        if not (ledger.is_relative_to(allowed_root) or ledger.is_relative_to(temp_root)):
            raise WriterFailure("ledger directory is outside approved roots")
    validate_existing_canonical_authority(validator, ledger)
    ledger.mkdir(parents=True, exist_ok=True)

    operation_id = record["operationId"]
    target = ledger / f"{operation_id}.json"
    payload = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(target, flags, 0o644)
    except FileExistsError as exc:
        raise WriterFailure(f"operationId already exists and cannot be overwritten: {operation_id}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        validate_canonical_authority(validator, ledger, phase="after append")
    except Exception:
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        raise
    return target


def main(_canonical_guard=require_cli_execution_authority) -> int:
    if require_cli_execution_authority is not _canonical_guard:
        raise WriterFailure("operation evidence CLI guard authority drift")
    _canonical_guard()
    parser = argparse.ArgumentParser(
        description="Validate and exclusively append one rate-limit operation record"
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--ledger-dir", type=Path, default=_CANONICAL_DEFAULT_LEDGER)
    args = parser.parse_args()

    target = append_record(args.input, args.ledger_dir, load_validator())
    print(f"Created append-only rate-limit operation evidence: {target}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WriterFailure as exc:
        print(f"RATE-LIMIT OPERATION EVIDENCE WRITE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
