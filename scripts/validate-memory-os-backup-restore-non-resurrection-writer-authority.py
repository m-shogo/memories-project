#!/usr/bin/env python3
"""Prove the typed non-resurrection writer CLI cannot substitute production authorities."""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_typed_non_resurrection_writer_authority", WRITER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load typed non-resurrection writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(writer: Any, field: str, substitute: Path) -> None:
    original = getattr(writer, field)
    try:
        setattr(writer, field, substitute)
        try:
            writer.require_cli_authorities()
        except writer.Fail:
            return
        raise NegativeFailure(f"typed non-resurrection writer accepted {field} CLI authority substitution")
    finally:
        setattr(writer, field, original)


def main() -> int:
    writer = load_writer()
    guard = getattr(writer, "require_cli_authorities", None)
    require(callable(guard), "typed non-resurrection writer CLI authority guard missing")

    main_source = inspect.getsource(writer.main)
    guard_offset = main_source.find("require_cli_authorities()")
    parser_offset = main_source.find("argparse.ArgumentParser")
    require(guard_offset >= 0, "typed non-resurrection writer main does not invoke CLI authority guard")
    require(parser_offset >= 0 and guard_offset < parser_offset,
            "typed non-resurrection writer must validate CLI authority before parsing input")

    writer.require_cli_authorities()
    contract_before = writer.CANONICAL_CONTRACT.read_bytes()
    registry_before = writer.CANONICAL_REGISTRY.read_bytes()
    generation_before = writer.CANONICAL_GEN_EVIDENCE_REGISTRY.read_bytes()

    substitutions = (
        ("CONTRACT", writer.CANONICAL_REGISTRY),
        ("REGISTRY", writer.CANONICAL_CONTRACT),
        ("GEN_EVIDENCE_REGISTRY", writer.CANONICAL_REGISTRY),
        ("GEN_WRITER", ROOT / "scripts/request-memory-os-backup-restore-drill.py"),
        ("LOCK", ROOT / "contracts/operations/.backup-restore-non-resurrection-admission-alternate.lock"),
    )
    for field, substitute in substitutions:
        expect_rejected(writer, field, substitute)

    writer.require_cli_authorities()
    require(writer.CANONICAL_CONTRACT.read_bytes() == contract_before,
            "typed writer CLI authority rejection mutated canonical contract")
    require(writer.CANONICAL_REGISTRY.read_bytes() == registry_before,
            "typed writer CLI authority rejection mutated canonical registry")
    require(writer.CANONICAL_GEN_EVIDENCE_REGISTRY.read_bytes() == generation_before,
            "typed writer CLI authority rejection mutated generation evidence registry")

    print("Memory OS typed non-resurrection writer CLI authority negative PASS")
    print("canonical typed evidence authorities substitution-rejected: true")
    print("CLI authority guard executes before input parsing: true")
    print("canonical registries mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"TYPED NON-RESURRECTION WRITER AUTHORITY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
