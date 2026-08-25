#!/usr/bin/env python3
"""Negative proof for canonical load-readiness note reconciliation."""

from __future__ import annotations

import importlib.util
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-load-readiness-note.py"
CANONICAL_LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_load_readiness_note_reconciler", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load load-readiness note reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def authority_substitution_rejected(module) -> None:
    original = CANONICAL_LOAD.read_bytes()
    substitutions = (
        ("LOAD_PATH", RECONCILER, "load contract authority drift"),
        ("LOAD_VALIDATOR", RECONCILER, "load validator authority drift"),
        ("OPERABILITY_VALIDATOR", RECONCILER, "operability validator authority drift"),
    )
    for attr, substitute, expected in substitutions:
        current = getattr(module, attr)
        try:
            setattr(module, attr, substitute)
            try:
                module.validate_authorities()
            except RuntimeError as exc:
                if expected not in str(exc):
                    raise RuntimeError(f"unexpected {attr} authority rejection: {exc}") from exc
            else:
                raise RuntimeError(f"reconciler accepted substituted authority: {attr}")
            if CANONICAL_LOAD.read_bytes() != original:
                raise RuntimeError(f"canonical load authority changed after rejected substitution: {attr}")
        finally:
            setattr(module, attr, current)


def atomic_replacement_is_fail_closed(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-load-readiness-atomic-") as temp_dir:
        root = Path(temp_dir)
        authority = root / "authority.json"
        authority.write_bytes(b"before\n")
        authority.chmod(0o640)
        original_mode = stat.S_IMODE(authority.stat().st_mode)
        original_replace = module.os.replace

        def reject_replace(_source, _target):
            raise OSError("synthetic readiness atomic replacement failure")

        module.os.replace = reject_replace
        try:
            try:
                module.atomic_write_bytes(authority, b"after\n")
            except OSError as exc:
                if "synthetic readiness atomic replacement failure" not in str(exc):
                    raise
            else:
                raise RuntimeError("readiness atomic replacement failure was accepted")
        finally:
            module.os.replace = original_replace

        if authority.read_bytes() != b"before\n":
            raise RuntimeError("failed readiness atomic replacement changed authority bytes")
        if stat.S_IMODE(authority.stat().st_mode) != original_mode:
            raise RuntimeError("failed readiness atomic replacement changed authority mode")
        residue = list(root.glob(f".{authority.name}.*.tmp"))
        if residue:
            raise RuntimeError(f"failed readiness atomic replacement left temp residue: {residue!r}")

        module.atomic_write_bytes(authority, b"after\n")
        if authority.read_bytes() != b"after\n":
            raise RuntimeError("successful readiness atomic replacement did not update authority")
        if stat.S_IMODE(authority.stat().st_mode) != original_mode:
            raise RuntimeError("successful readiness atomic replacement changed authority mode")


def rejected_load_validator_rolls_back(module, original: bytes) -> None:
    calls = 0
    original_validate = module.validate_canonical_load

    def controlled_validator() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            return
        raise SystemExit("synthetic post-write load authority rejection")

    module.validate_canonical_load = controlled_validator
    try:
        try:
            module.main()
        except SystemExit as exc:
            if "synthetic post-write load authority rejection" not in str(exc):
                raise RuntimeError(f"unexpected rejection: {exc}") from exc
        else:
            raise RuntimeError("reconciler accepted synthetic post-write load validator failure")
        if calls != 2:
            raise RuntimeError(f"canonical load validator call count drift: {calls}")
        if CANONICAL_LOAD.read_bytes() != original:
            raise RuntimeError("load authority was not restored after post-write load rejection")
    finally:
        module.validate_canonical_load = original_validate
        module.atomic_write_bytes(CANONICAL_LOAD, original)


def rejected_operability_validator_rolls_back(module, original: bytes) -> None:
    load_calls = 0
    operability_calls = 0
    original_load_validate = module.validate_canonical_load
    original_operability_validate = module.validate_canonical_operability

    def controlled_load_validator() -> None:
        nonlocal load_calls
        load_calls += 1

    def controlled_operability_validator() -> None:
        nonlocal operability_calls
        operability_calls += 1
        raise SystemExit("synthetic post-write aggregate operability rejection")

    module.validate_canonical_load = controlled_load_validator
    module.validate_canonical_operability = controlled_operability_validator
    try:
        try:
            module.main()
        except SystemExit as exc:
            if "synthetic post-write aggregate operability rejection" not in str(exc):
                raise RuntimeError(f"unexpected aggregate rejection: {exc}") from exc
        else:
            raise RuntimeError("reconciler accepted synthetic post-write aggregate operability failure")
        if load_calls != 2:
            raise RuntimeError(f"canonical load validator call count drift during aggregate rejection: {load_calls}")
        if operability_calls != 1:
            raise RuntimeError(f"canonical operability validator call count drift: {operability_calls}")
        if CANONICAL_LOAD.read_bytes() != original:
            raise RuntimeError("load authority was not restored after aggregate operability rejection")
    finally:
        module.validate_canonical_load = original_load_validate
        module.validate_canonical_operability = original_operability_validate
        module.atomic_write_bytes(CANONICAL_LOAD, original)


def main() -> int:
    module = load_module()
    original = CANONICAL_LOAD.read_bytes()
    original_mode = stat.S_IMODE(CANONICAL_LOAD.stat().st_mode)
    authority_substitution_rejected(module)
    atomic_replacement_is_fail_closed(module)
    rejected_load_validator_rolls_back(module, original)
    rejected_operability_validator_rolls_back(module, original)

    if CANONICAL_LOAD.read_bytes() != original:
        raise RuntimeError("canonical load authority was not restored")
    if stat.S_IMODE(CANONICAL_LOAD.stat().st_mode) != original_mode:
        raise RuntimeError("canonical load authority mode drifted")
    residue = list(CANONICAL_LOAD.parent.glob(f".{CANONICAL_LOAD.name}.*.tmp"))
    if residue:
        raise RuntimeError(f"load readiness-note reconcile left temp residue: {residue!r}")
    print("PASS: load readiness-note reconcile pins authority identity, publishes atomically, preserves mode, and rolls back rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
