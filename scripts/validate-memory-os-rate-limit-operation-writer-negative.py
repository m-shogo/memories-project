#!/usr/bin/env python3
"""Focused negatives for the rate-limit operation evidence writer guard."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/create-memory-os-rate-limit-operation-evidence.py"


def load_writer():
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operation_writer", WRITER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load rate-limit operation evidence writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    writer = load_writer()

    class FakeValidationFailure(RuntimeError):
        pass

    class RejectingValidator:
        ValidationFailure = FakeValidationFailure

        @staticmethod
        def main() -> int:
            raise FakeValidationFailure("synthetic canonical ledger corruption")

    try:
        writer.validate_existing_canonical_authority(
            RejectingValidator(), writer.DEFAULT_LEDGER.resolve()
        )
    except writer.WriterFailure as exc:
        if "existing canonical ledger authority is invalid" not in str(exc):
            raise AssertionError(f"unexpected canonical rejection: {exc}") from exc
    else:
        raise AssertionError("canonical ledger corruption was incorrectly accepted")

    class NonZeroValidator:
        ValidationFailure = FakeValidationFailure

        @staticmethod
        def main() -> int:
            return 7

    try:
        writer.validate_existing_canonical_authority(
            NonZeroValidator(), writer.DEFAULT_LEDGER.resolve()
        )
    except writer.WriterFailure as exc:
        if "validation returned non-zero: 7" not in str(exc):
            raise AssertionError(f"unexpected non-zero rejection: {exc}") from exc
    else:
        raise AssertionError("non-zero canonical validation was incorrectly accepted")

    class AlternateLedgerValidator:
        ValidationFailure = FakeValidationFailure
        calls = 0

        @classmethod
        def main(cls) -> int:
            cls.calls += 1
            raise AssertionError("alternate CI ledger must not validate canonical authority")

    with tempfile.TemporaryDirectory() as tmpdir:
        writer.validate_existing_canonical_authority(
            AlternateLedgerValidator(), Path(tmpdir).resolve()
        )
    if AlternateLedgerValidator.calls != 0:
        raise AssertionError("alternate ledger unexpectedly invoked canonical validation")

    print("PASS: canonical rate-limit operation ledger is validated before append")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
