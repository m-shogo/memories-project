#!/usr/bin/env python3
"""Prove parser artifact reconcile rejects executable/path authority substitution."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-parser-artifact-registry.py"
CONTRACT_PATH = ROOT / "contracts/operations/parser-artifact-registry-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_reconciler() -> Any:
    spec = importlib.util.spec_from_file_location(
        "parser_artifact_reconciler_authority_negative", RECONCILER_PATH
    )
    require(spec is not None and spec.loader is not None, "cannot load parser reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_substitution_rejection(
    reconciler: Any, attribute: str, substitute: Path, label: str
) -> None:
    original_attribute = getattr(reconciler, attribute)
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    setattr(reconciler, attribute, substitute)
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            message = str(exc)
            require(
                "authority drift" in message or "missing or escapes repository" in message,
                f"{label} rejected for unrelated reason: {message}",
            )
        else:
            raise NegativeFailure(f"parser reconciler accepted authority substitution: {label}")
        require(
            CONTRACT_PATH.read_bytes() == original_contract,
            f"parser contract mutated after authority substitution: {label}",
        )
        require(
            STATUS_PATH.read_bytes() == original_status,
            f"production status mutated after authority substitution: {label}",
        )
    finally:
        setattr(reconciler, attribute, original_attribute)
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)


def main() -> int:
    reconciler = load_reconciler()
    reconciler.enforce_runtime_authorities()
    cases = (
        ("WRITER_PATH", reconciler.VALIDATOR_PATH, "writer executable"),
        ("VALIDATOR_PATH", reconciler.VERSION_VALIDATOR_PATH, "parser validator executable"),
        ("VERSION_VALIDATOR_PATH", reconciler.OPERABILITY_VALIDATOR_PATH, "version validator executable"),
        ("OPERABILITY_VALIDATOR_PATH", reconciler.VERSION_VALIDATOR_PATH, "operability validator executable"),
        ("CONTRACT_PATH", reconciler.STATUS_PATH, "parser contract path"),
        ("STATUS_PATH", reconciler.CONTRACT_PATH, "production status path"),
    )
    for attribute, substitute, label in cases:
        expect_substitution_rejection(reconciler, attribute, substitute, label)
    print("PASS: parser reconcile rejects executable and canonical path authority substitutions")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"PARSER RECONCILE AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
