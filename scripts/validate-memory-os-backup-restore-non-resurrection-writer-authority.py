#!/usr/bin/env python3
"""Prove the typed non-resurrection writer CLI cannot substitute production authorities."""
from __future__ import annotations

import importlib.util
import inspect
import tempfile
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


def prove_materialized_lock_symlink_fails_closed(writer: Any) -> None:
    lock = writer.LOCK
    require(lock == ROOT / "contracts/operations/.backup-restore-non-resurrection-admission.lock",
            "typed non-resurrection canonical lock path drift")
    require(not lock.exists() and not lock.is_symlink(),
            "typed non-resurrection canonical lock must be absent before symlink negative")
    with tempfile.TemporaryDirectory(prefix="memory-os-typed-lock-negative-") as temp_dir:
        target = Path(temp_dir) / "outside.lock"
        target.write_bytes(b"outside-lock-target\n")
        before = target.read_bytes()
        lock.symlink_to(target)
        try:
            try:
                writer.os.open(lock, writer.os.O_WRONLY | writer.os.O_CREAT | writer.os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                raise NegativeFailure("typed non-resurrection writer lock flags followed a materialized symlink")
            require(lock.is_symlink(), "typed non-resurrection lock symlink unexpectedly replaced")
            require(target.read_bytes() == before,
                    "typed non-resurrection lock symlink rejection mutated external target")
        finally:
            try:
                lock.unlink()
            except FileNotFoundError:
                pass
    require(not lock.exists() and not lock.is_symlink(),
            "typed non-resurrection lock symlink negative left canonical lock materialized")


def main() -> int:
    writer = load_writer()
    guard = getattr(writer, "require_cli_authorities", None)
    require(callable(guard), "typed non-resurrection writer CLI authority guard missing")

    main_source = inspect.getsource(writer.main)
    guard_offset = main_source.find("require_cli_authorities()")
    parser_offset = main_source.find("argparse.ArgumentParser")
    lock_open_offset = main_source.find("os.O_CREAT | os.O_EXCL")
    require(guard_offset >= 0, "typed non-resurrection writer main does not invoke CLI authority guard")
    require(parser_offset >= 0 and guard_offset < parser_offset,
            "typed non-resurrection writer must validate CLI authority before parsing input")
    require(lock_open_offset >= 0 and parser_offset < lock_open_offset,
            "typed non-resurrection writer must retain exclusive-create lock semantics")

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

    prove_materialized_lock_symlink_fails_closed(writer)
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
    print("materialized lock symlink rejected by exclusive-create semantics: true")
    print("external lock target mutated: false")
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
