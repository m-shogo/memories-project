#!/usr/bin/env python3
"""Prove load missing-evidence reconciliation is atomic, mode-preserving and fail-closed."""

from __future__ import annotations

import importlib.util
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


def main() -> int:
    module = load_module()
    canonical_bytes = STATUS.read_bytes()
    canonical_mode = stat.S_IMODE(STATUS.stat().st_mode)
    authority_substitution_rejected(module)
    atomic_replacement_is_fail_closed(module)
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
    print("PASS: load missing-evidence reconcile pins authorities, publishes atomically, preserves mode, and rolls back fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
