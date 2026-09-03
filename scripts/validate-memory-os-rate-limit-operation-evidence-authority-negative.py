#!/usr/bin/env python3
"""Prove rate-limit operation evidence validator authorities cannot be substituted."""

from __future__ import annotations

import importlib.util
import re
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-operation-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_operation_evidence_authority_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load operation evidence validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(label: str, action: Callable[[], object], failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {label}")
        return
    except Exception as exc:
        raise Fail(f"{label} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {label}")


def main() -> int:
    validator = load_validator()
    validator.require_runtime_authorities()
    contract_before = validator.CONTRACT_PATH.read_bytes()
    status_before = validator.STATUS_PATH.read_bytes()
    ledger_before = sorted(path.name for path in validator.LEDGER_PATH.glob("*.json"))

    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-operation-validator-") as temp_dir:
        outside_root = Path(temp_dir)
        outside_file = outside_root / "outside.json"
        outside_file.write_text("{}\n", encoding="utf-8")
        outside_dir = outside_root / "ledger"
        outside_dir.mkdir()

        original_root = validator.ROOT
        try:
            validator.ROOT = outside_root
            expect_rejected(
                "operation evidence validator ROOT substitution",
                validator.require_runtime_authorities,
                validator.ValidationFailure,
            )
        finally:
            validator.ROOT = original_root

        for attribute in (
            "CONTRACT_PATH", "OPERATIONS_PATH", "POLICY_PATH", "STATUS_PATH", "TEMPLATE_PATH",
        ):
            original = getattr(validator, attribute)
            try:
                setattr(validator, attribute, outside_file)
                expect_rejected(
                    f"operation evidence validator {attribute} substitution",
                    validator.require_runtime_authorities,
                    validator.ValidationFailure,
                )
            finally:
                setattr(validator, attribute, original)

        original_ledger = validator.LEDGER_PATH
        try:
            validator.LEDGER_PATH = outside_dir
            expect_rejected(
                "operation evidence validator LEDGER_PATH substitution",
                validator.require_runtime_authorities,
                validator.ValidationFailure,
            )
        finally:
            validator.LEDGER_PATH = original_ledger

        helper_attributes = (
            "require",
            "require_source_ancestor",
            "git_bytes",
            "canonical_evidence_path",
            "load_json",
            "parse_rfc3339",
            "validate_repo_refs",
            "all_evidence_refs",
            "expected_evidence_digests",
            "iter_string_values",
            "load_contract_context",
            "validate_record",
        )
        for attribute in helper_attributes:
            original = getattr(validator, attribute)
            try:
                setattr(validator, attribute, lambda *args, **kwargs: True)
                expect_rejected(
                    f"operation evidence validator {attribute} execution substitution",
                    validator.require_runtime_authorities,
                    validator.ValidationFailure,
                )
            finally:
                setattr(validator, attribute, original)

        original_fields = validator.REQUIRED_RECORD_FIELDS
        try:
            validator.REQUIRED_RECORD_FIELDS = set(original_fields) - {"evidenceDigestsByRef"}
            expect_rejected(
                "operation evidence required-field semantic substitution",
                validator.require_runtime_authorities,
                validator.ValidationFailure,
            )
        finally:
            validator.REQUIRED_RECORD_FIELDS = original_fields

        original_secret_re = validator.SECRET_WORD_RE
        try:
            validator.SECRET_WORD_RE = re.compile(r"never-match-this-secret-pattern")
            expect_rejected(
                "operation evidence privacy regex semantic substitution",
                validator.require_runtime_authorities,
                validator.ValidationFailure,
            )
        finally:
            validator.SECRET_WORD_RE = original_secret_re

        expect_rejected(
            "operation evidence validator main guard substitution",
            lambda: validator.main(lambda: None),
            validator.ValidationFailure,
        )

        original_run = validator.subprocess.run
        try:
            validator.subprocess.run = lambda *args, **kwargs: object()
            expect_rejected(
                "operation evidence source ancestry transport substitution",
                lambda: validator.require_source_ancestor("0" * 40),
                validator.ValidationFailure,
            )
            expect_rejected(
                "operation evidence git evidence transport substitution",
                lambda: validator.git_bytes("status"),
                validator.ValidationFailure,
            )
        finally:
            validator.subprocess.run = original_run

    validator.require_runtime_authorities()
    require(validator.CONTRACT_PATH.read_bytes() == contract_before,
            "operation evidence authority negative mutated contract")
    require(validator.STATUS_PATH.read_bytes() == status_before,
            "operation evidence authority negative mutated production status")
    require(sorted(path.name for path in validator.LEDGER_PATH.glob("*.json")) == ledger_before,
            "operation evidence authority negative mutated append-only ledger")
    print("Memory OS rate-limit operation evidence authority negative suite PASS")
    print("validator path/helper/privacy semantic substitution accepted: false")
    print("append-only evidence mutated: false")
    print("production evidence generated: false")
    print("production readiness changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE-LIMIT OPERATION EVIDENCE AUTHORITY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
