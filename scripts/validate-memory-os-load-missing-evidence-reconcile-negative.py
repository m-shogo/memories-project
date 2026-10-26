#!/usr/bin/env python3
"""Prove load missing-evidence reconciliation is atomic, mode-preserving and fail-closed."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import json
import stat
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-load-missing-evidence.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
LOAD_VALIDATOR = ROOT / "scripts/validate-memory-os-load.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("load_missing_evidence_reconciler", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load load missing-evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"expected object: {path.relative_to(ROOT)}")
    return value


def authority_substitution_rejected(module: ModuleType) -> None:
    canonical_status = STATUS.read_bytes()
    substitutions = (
        ("LOAD", STATUS, "load contract authority drift"),
        ("STATUS", LOAD, "production status authority drift"),
        ("LOAD_VALIDATOR", OPERABILITY_VALIDATOR, "load validator authority drift"),
        ("OPERABILITY_VALIDATOR", LOAD_VALIDATOR, "operability validator authority drift"),
    )
    for attr, substitute, expected in substitutions:
        original = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            try:
                module.validate_authorities()
            except RuntimeError as exc:
                require(expected in str(exc), f"unexpected {attr} substitution rejection: {exc}")
            else:
                raise NegativeFailure(f"load missing-evidence reconciler accepted substituted authority: {attr}")
            require(STATUS.read_bytes() == canonical_status, f"{attr}: production status changed after rejected authority substitution")
        finally:
            setattr(module, attr, original)


def atomic_replacement_is_fail_closed(module: ModuleType) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-load-missing-atomic-") as temp_dir:
        root = Path(temp_dir)
        authority = root / "authority.json"
        authority.write_bytes(b"before\n")
        authority.chmod(0o640)
        original_mode = stat.S_IMODE(authority.stat().st_mode)
        original_replace = module.os.replace

        def reject_replace(_source, _target):
            raise OSError("synthetic missing-evidence atomic replacement failure")

        module.os.replace = reject_replace
        try:
            try:
                module.atomic_write_bytes(authority, b"after\n")
            except OSError as exc:
                require("synthetic missing-evidence atomic replacement failure" in str(exc), f"unexpected atomic failure: {exc}")
            else:
                raise NegativeFailure("missing-evidence atomic replacement failure was accepted")
        finally:
            module.os.replace = original_replace

        require(authority.read_bytes() == b"before\n", "failed atomic replacement changed authority bytes")
        require(stat.S_IMODE(authority.stat().st_mode) == original_mode, "failed atomic replacement changed authority mode")
        require(not list(root.glob(f".{authority.name}.*.tmp")), "failed atomic replacement left temp residue")

        module.atomic_write_bytes(authority, b"after\n")
        require(authority.read_bytes() == b"after\n", "successful atomic replacement did not update authority")
        require(stat.S_IMODE(authority.stat().st_mode) == original_mode, "successful atomic replacement changed authority mode")


def substituted_atomic_targets_are_rejected(module: ModuleType) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-load-missing-symlink-") as temp_dir:
        root = Path(temp_dir)
        outside = root / "outside"
        outside.mkdir()
        canary = outside / "authority.json"
        canary.write_bytes(b"SYNTHETIC_MISSING_EVIDENCE_CANARY")
        direct = root / "direct.json"
        direct.symlink_to(canary)
        ancestor = root / "linked"
        ancestor.symlink_to(outside, target_is_directory=True)
        directory = root / "directory.json"
        directory.mkdir()
        for target, expected in (
            (direct, "load missing-evidence atomic symlink target/ancestor refused"),
            (ancestor / "authority.json", "load missing-evidence atomic symlink target/ancestor refused"),
            (directory, "load missing-evidence atomic target must be a regular file"),
        ):
            try:
                module.atomic_write_bytes(target, b"synthetic overwrite")
            except RuntimeError as exc:
                require(expected in str(exc), f"unexpected missing-evidence target rejection: {exc}")
            else:
                raise NegativeFailure(f"missing-evidence atomic writer accepted substituted target: {target}")
            require(canary.read_bytes() == b"SYNTHETIC_MISSING_EVIDENCE_CANARY",
                    "missing-evidence atomic writer escaped to external canary")
        require(direct.is_symlink() and ancestor.is_symlink() and directory.is_dir(),
                "missing-evidence atomic writer replaced substituted target")
        require(not list(root.rglob(".*.tmp")), "missing-evidence rejected target left temp residue")


def rollback_failure_is_explicit(module: ModuleType, original_status: bytes) -> None:
    original_validate = module.validate
    original_writer = module.atomic_write_bytes
    calls: list[Path] = []

    def fail_after_write(path: Path) -> None:
        if path == module.OPERABILITY_VALIDATOR:
            raise RuntimeError("synthetic missing-evidence post-write rejection")

    def reject_rollback(path: Path, data: bytes) -> None:
        calls.append(path)
        if len(calls) == 2:
            raise OSError("synthetic missing-evidence rollback denied")
        original_writer(path, data)

    module.validate = fail_after_write
    module.atomic_write_bytes = reject_rollback
    try:
        try:
            module.main()
        except RuntimeError as exc:
            require("rollback incomplete: OSError" in str(exc),
                    f"missing-evidence rollback failure was not explicit: {exc}")
            require(isinstance(exc.__cause__, RuntimeError) and
                    "synthetic missing-evidence post-write rejection" in str(exc.__cause__),
                    "missing-evidence rollback failure masked primary cause")
        else:
            raise NegativeFailure("missing-evidence incomplete rollback was accepted")
        require(calls == [module.STATUS, module.STATUS],
                f"missing-evidence writer/rollback order drift: {calls}")
    finally:
        module.validate = original_validate
        module.atomic_write_bytes = original_writer
        original_writer(STATUS, original_status)
    require(STATUS.read_bytes() == original_status,
            "missing-evidence synthetic rollback failure left canonical status mutated")
    require(not list(STATUS.parent.glob(f".{STATUS.name}.*.tmp")),
            "missing-evidence synthetic rollback failure left temporary files")


def main() -> int:
    module = load_module()
    canonical_bytes = STATUS.read_bytes()
    canonical_mode = stat.S_IMODE(STATUS.stat().st_mode)
    authority_substitution_rejected(module)
    atomic_replacement_is_fail_closed(module)
    substituted_atomic_targets_are_rejected(module)
    rollback_failure_is_explicit(module, canonical_bytes)
    status = load_json(STATUS)
    area = next(
        (row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-006"),
        None,
    )
    require(isinstance(area, dict), "OPS-P0-006 missing")
    missing = area.get("missingEvidence")
    require(isinstance(missing, list), "OPS-P0-006 missingEvidence missing")
    if module.PREFENCE_STALE_BLOCKER not in missing:
        missing.append(module.PREFENCE_STALE_BLOCKER)
    input_bytes = (json.dumps(status, indent=2) + "\n").encode("utf-8")

    calls: list[Path] = []
    original_validate = module.validate

    def controlled_validate(path: Path) -> None:
        calls.append(path)
        if path == module.OPERABILITY_VALIDATOR:
            raise RuntimeError("controlled post-write operability failure")

    module.validate = controlled_validate
    try:
        module.atomic_write_bytes(STATUS, input_bytes)
        try:
            module.main()
        except RuntimeError as exc:
            require("controlled post-write operability failure" in str(exc), f"unexpected failure: {exc}")
        else:
            raise NegativeFailure("controlled post-write operability failure was accepted")
        require(
            calls == [module.LOAD_VALIDATOR, module.LOAD_VALIDATOR, module.OPERABILITY_VALIDATOR],
            f"validator ordering drift: {calls}",
        )
        require(STATUS.read_bytes() == input_bytes, "status was not rolled back after post-write validation failure")
        require(stat.S_IMODE(STATUS.stat().st_mode) == canonical_mode, "status mode drifted during rollback")
        require(not list(STATUS.parent.glob(f".{STATUS.name}.*.tmp")), "status rollback left temp residue")
    finally:
        module.validate = original_validate
        module.atomic_write_bytes(STATUS, canonical_bytes)

    require(STATUS.read_bytes() == canonical_bytes, "canonical production status was not restored")
    require(stat.S_IMODE(STATUS.stat().st_mode) == canonical_mode, "canonical production status mode was not restored")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate-memory-os-load-missing-source-negative.py")],
        cwd=ROOT, check=True,
    )
    print("PASS: load missing-evidence reconcile pins authorities, publishes atomically, preserves mode, and rolls back fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
