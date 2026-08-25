#!/usr/bin/env python3
"""Prove container-kill authority identity, atomic publication, mode preservation and rollback remain fail-closed."""

from __future__ import annotations

import importlib.util
import stat
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-container-kill-authority.py"
LOAD_CONTRACT = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


def load_module():
    spec = importlib.util.spec_from_file_location("container_kill_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise SystemExit("unable to load container-kill reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(fn, needle: str) -> None:
    try:
        fn()
    except BaseException as exc:
        if needle not in str(exc):
            raise SystemExit(f"unexpected rejection: {exc}") from exc
        return
    raise SystemExit(f"expected rejection containing: {needle}")


def expect_authority_substitution(module, attr: str, replacement: Path, needle: str) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        expect_rejection(module.require_canonical_authorities, needle)
    finally:
        setattr(module, attr, original)


def expect_atomic_replace_failure(module) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-container-kill-atomic-") as tmp:
        root = Path(tmp)
        authority = root / "authority.json"
        authority.write_bytes(b"before\n")
        authority.chmod(0o640)
        original_mode = stat.S_IMODE(authority.stat().st_mode)
        original_replace = module.os.replace

        def reject_replace(_source, _target):
            raise OSError("synthetic container-kill atomic replacement failure")

        module.os.replace = reject_replace
        try:
            try:
                module.CANONICAL_ATOMIC_WRITE_BYTES(authority, b"after\n")
            except OSError as exc:
                if "synthetic container-kill atomic replacement failure" not in str(exc):
                    raise
            else:
                raise SystemExit("atomic replacement failure was accepted")
        finally:
            module.os.replace = original_replace

        if authority.read_bytes() != b"before\n":
            raise SystemExit("atomic replacement failure mutated target bytes")
        if stat.S_IMODE(authority.stat().st_mode) != original_mode:
            raise SystemExit("atomic replacement failure changed target mode")
        if list(root.glob(f".{authority.name}.*.tmp")):
            raise SystemExit("atomic replacement failure left temp residue")

        module.CANONICAL_ATOMIC_WRITE_BYTES(authority, b"after\n")
        if authority.read_bytes() != b"after\n":
            raise SystemExit("successful atomic replacement did not update target")
        if stat.S_IMODE(authority.stat().st_mode) != original_mode:
            raise SystemExit("successful atomic replacement changed target mode")


def main() -> int:
    original_load = LOAD_CONTRACT.read_bytes()
    original_status = STATUS.read_bytes()
    original_load_mode = stat.S_IMODE(LOAD_CONTRACT.stat().st_mode)
    original_status_mode = stat.S_IMODE(STATUS.stat().st_mode)
    module = load_module()

    source = RECONCILER.read_text(encoding="utf-8")
    for forbidden in ("LOAD_CONTRACT.write_text(", "STATUS.write_text(", "LOAD_CONTRACT.write_bytes(", "STATUS.write_bytes("):
        if forbidden in source:
            raise SystemExit(f"container-kill authority regressed to direct publication/rollback: {forbidden}")

    substitutions = {
        "PROOF_CONTRACT": (module.LOAD_CONTRACT, "proof contract authority substitution"),
        "PROOF_RESULT": (module.PROOF_CONTRACT, "proof result authority substitution"),
        "PROOF_VALIDATOR": (module.LOAD_VALIDATOR, "proof validator authority substitution"),
        "LOAD_CONTRACT": (module.PROOF_CONTRACT, "load contract authority substitution"),
        "STATUS": (module.LOAD_CONTRACT, "production status authority substitution"),
        "READINESS_NORMALIZER": (module.LOAD_VALIDATOR, "readiness normalizer authority substitution"),
        "MISSING_EVIDENCE_NORMALIZER": (module.LOAD_VALIDATOR, "missing-evidence normalizer authority substitution"),
        "LOAD_VALIDATOR": (module.PROOF_VALIDATOR, "load validator authority substitution"),
        "OPERABILITY_VALIDATOR": (module.LOAD_VALIDATOR, "operability validator authority substitution"),
    }
    for attr, (replacement, needle) in substitutions.items():
        expect_authority_substitution(module, attr, replacement, needle)
        if LOAD_CONTRACT.read_bytes() != original_load or STATUS.read_bytes() != original_status:
            raise SystemExit(f"authority substitution mutated canonical data: {attr}")

    original_run = module.subprocess.run
    module.subprocess.run = lambda *args, **kwargs: None
    try:
        expect_rejection(module.require_canonical_authorities, "container-kill subprocess transport is not canonical")
    finally:
        module.subprocess.run = original_run

    original_writer = module.atomic_write_bytes
    module.atomic_write_bytes = lambda _path, _data: None
    try:
        expect_rejection(module.require_canonical_authorities, "container-kill atomic writer authority is not canonical")
    finally:
        module.atomic_write_bytes = original_writer

    expect_atomic_replace_failure(module)
    module.require_canonical_authorities()

    original_operability = module.OPERABILITY_VALIDATOR.read_bytes()
    original_operability_mode = stat.S_IMODE(module.OPERABILITY_VALIDATOR.stat().st_mode)
    try:
        module.CANONICAL_ATOMIC_WRITE_BYTES(
            module.OPERABILITY_VALIDATOR,
            b"raise SystemExit('synthetic post-write aggregate failure')\n",
        )
        expect_rejection(module.main, "synthetic post-write aggregate failure")
        if LOAD_CONTRACT.read_bytes() != original_load:
            raise SystemExit("container-kill reconcile failed to roll back load authority")
        if STATUS.read_bytes() != original_status:
            raise SystemExit("container-kill reconcile failed to roll back production status")
        if stat.S_IMODE(LOAD_CONTRACT.stat().st_mode) != original_load_mode:
            raise SystemExit("container-kill reconcile changed load authority mode")
        if stat.S_IMODE(STATUS.stat().st_mode) != original_status_mode:
            raise SystemExit("container-kill reconcile changed production status mode")
    finally:
        module.CANONICAL_ATOMIC_WRITE_BYTES(module.OPERABILITY_VALIDATOR, original_operability)
        module.OPERABILITY_VALIDATOR.chmod(original_operability_mode)
        module.CANONICAL_ATOMIC_WRITE_BYTES(LOAD_CONTRACT, original_load)
        module.CANONICAL_ATOMIC_WRITE_BYTES(STATUS, original_status)

    residue = list(LOAD_CONTRACT.parent.glob(f".{LOAD_CONTRACT.name}.*.tmp"))
    residue += list(STATUS.parent.glob(f".{STATUS.name}.*.tmp"))
    if residue:
        raise SystemExit(f"container-kill rollback left temp residue: {residue!r}")

    print("PASS: container-kill authority identity, execution transport, atomic mode and post-write rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
