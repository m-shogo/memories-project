#!/usr/bin/env python3
"""Prove typed non-resurrection execution and registry transport fail closed."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
TEMP_PARENT = ROOT / "contracts/operations"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_validator():
    return load_module(VALIDATOR, "memory_os_typed_transport_negative")


def expect_rejected(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def assert_no_registry_temp_residue(parent: Path) -> None:
    residue = [
        path.name
        for path in parent.iterdir()
        if path.name.startswith(".backup-restore-non-resurrection.")
        or path.name.startswith(".backup-restore-non-resurrection-rollback.")
    ]
    require(not residue, f"typed registry temp residue remained: {residue}")


def exercise_registry_transaction_transport() -> None:
    require(WRITER.is_file() and not WRITER.is_symlink(), "canonical typed writer missing or symlinked")
    require(TEMP_PARENT.is_dir(), "repo-local typed transport temp parent missing")
    writer = load_module(WRITER, "memory_os_typed_writer_transport_negative")
    base = {
        "schemaVersion": "memory-os-backup-restore-non-resurrection-admission-registry.v1",
        "appendOnly": True,
        "registeredRecordCount": 0,
        "completeRecordCount": 0,
        "candidateCoveredCount": 0,
        "records": [],
        "productionEvidence": False,
        "productionReady": False,
    }

    with tempfile.TemporaryDirectory(prefix=".memory-os-nonres-transport-negative-", dir=TEMP_PARENT) as tmp:
        parent = Path(tmp)
        registry = parent / "typed-registry.json"
        registry.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8")
        registry.chmod(0o640)
        writer.REGISTRY = registry
        original_bytes = registry.read_bytes()
        original_mode = stat.S_IMODE(registry.stat().st_mode)
        require(original_mode == 0o640, "typed registry negative fixture mode setup failed")

        writer.atomic_write(copy.deepcopy(base), original_mode)
        require(stat.S_IMODE(registry.stat().st_mode) == original_mode, "successful typed registry replace changed mode")
        assert_no_registry_temp_residue(parent)

        before_reject = registry.read_bytes()
        original_replace = writer.os.replace

        def reject_replace(*_args: object, **_kwargs: object) -> None:
            raise OSError("controlled typed registry replace rejection")

        writer.os.replace = reject_replace
        try:
            expect_rejected(
                "typed registry atomic replace rejection",
                lambda: writer.atomic_write(copy.deepcopy(base), original_mode),
                OSError,
            )
        finally:
            writer.os.replace = original_replace
        require(registry.read_bytes() == before_reject, "replace rejection mutated typed registry bytes")
        require(stat.S_IMODE(registry.stat().st_mode) == original_mode, "replace rejection mutated typed registry mode")
        assert_no_registry_temp_residue(parent)

        candidate = copy.deepcopy(base)
        candidate["registeredRecordCount"] = 1
        original_guard = writer.validate_registry_for_append

        def reject_post_write(_value: dict[str, object]) -> list[dict[str, object]]:
            raise writer.Fail("controlled typed registry post-write validation failure")

        writer.validate_registry_for_append = reject_post_write
        try:
            expect_rejected(
                "typed registry post-write validation rollback",
                lambda: writer.write_registry_transactionally(candidate),
                writer.Fail,
            )
        finally:
            writer.validate_registry_for_append = original_guard
        require(registry.read_bytes() == original_bytes, "post-write failure did not restore exact typed registry bytes")
        require(stat.S_IMODE(registry.stat().st_mode) == original_mode, "post-write failure did not restore typed registry mode")
        assert_no_registry_temp_residue(parent)


def main() -> int:
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical typed validator missing or symlinked")
    validator = load_validator()

    original_subprocess_run = validator.subprocess.run
    original_spec_from_file_location = validator.importlib.util.spec_from_file_location
    original_module_from_spec = validator.importlib.util.module_from_spec
    original_guard = validator.enforce_execution_transport

    try:
        validator.subprocess.run = lambda *args, **kwargs: None
        expect_rejected("typed subprocess transport substitution", validator.main, validator.Fail)
    finally:
        validator.subprocess.run = original_subprocess_run

    try:
        validator.importlib.util.spec_from_file_location = lambda *args, **kwargs: None
        expect_rejected("typed import spec transport substitution", validator.main, validator.Fail)
    finally:
        validator.importlib.util.spec_from_file_location = original_spec_from_file_location

    try:
        validator.importlib.util.module_from_spec = lambda *args, **kwargs: None
        expect_rejected("typed module loader transport substitution", validator.main, validator.Fail)
    finally:
        validator.importlib.util.module_from_spec = original_module_from_spec

    try:
        validator.enforce_execution_transport = lambda: None
        expect_rejected("typed execution guard substitution", validator.main, validator.Fail)
    finally:
        validator.enforce_execution_transport = original_guard

    exercise_registry_transaction_transport()

    print("Typed non-resurrection execution/registry transport negative suite PASS")
    print("subprocess/import loader/guard substitution accepted: false")
    print("registry mode preserved across atomic replacement: true")
    print("replace rejection mutates canonical bytes or mode: false")
    print("post-write validation failure restores exact bytes and mode: true")
    print("registry temp residue remains: false")
    print("typed evidence created: false")
    print("production evidence: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"TYPED TRANSPORT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
