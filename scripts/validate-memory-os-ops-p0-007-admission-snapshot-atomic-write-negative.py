#!/usr/bin/env python3
"""Negative proof for OPS-P0-007 strict snapshot atomic replacement."""

from __future__ import annotations

import importlib.util
import os
import stat
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


def protected_identity(path: Path) -> tuple[object, ...]:
    """Identity of both the authority and its parent, without following links for stat."""
    entry = path.lstat()
    parent = path.parent.lstat()
    return (
        (entry.st_mode, entry.st_dev, entry.st_ino),
        (parent.st_mode, parent.st_dev, parent.st_ino),
        path.resolve(strict=True),
    )


def prove_identity_classifier() -> None:
    # The only symlink mutations occur outside the canonical checkout.
    with tempfile.TemporaryDirectory(prefix="ops-p0-007-atomic-identity-") as tmp:
        root = Path(tmp)
        parent = root / "authority"
        parent.mkdir()
        path = parent / "snapshot.json"
        path.write_text('{"productionDecision":"NO_GO"}\n', encoding="utf-8")
        baseline = protected_identity(path)
        baseline_bytes = path.read_bytes()
        original = parent / "original.json"
        path.rename(original)
        path.symlink_to(original.name)
        if path.read_bytes() != baseline_bytes or protected_identity(path) == baseline:
            raise SystemExit("atomic identity classifier accepted equal-content file symlink")
        path.unlink()
        original.rename(path)
        if protected_identity(path) != baseline:
            raise SystemExit("atomic identity classifier failed original inode restoration")
        actual_parent = root / "actual"
        parent.rename(actual_parent)
        parent.symlink_to(actual_parent.name, target_is_directory=True)
        if path.read_bytes() != baseline_bytes or protected_identity(path) == baseline:
            raise SystemExit("atomic identity classifier accepted equal-content parent symlink")


EXPECTED_ATOMIC_FAILURE = (
    "cannot atomically write contracts/operations/ops-p0-007-admission-snapshot.v1.json: "
    "injected atomic replacement failure"
)


def require_exact_atomic_failure(observed: str) -> None:
    if observed != EXPECTED_ATOMIC_FAILURE:
        raise SystemExit(f"unexpected atomic-write failure: {observed}")


def prove_exact_failure_classifier() -> None:
    require_exact_atomic_failure(EXPECTED_ATOMIC_FAILURE)
    for observed in (
        "unrelated failure: " + EXPECTED_ATOMIC_FAILURE,
        EXPECTED_ATOMIC_FAILURE + " unrelated failure",
        "cannot atomically write another-authority.json: injected atomic replacement failure",
        "injected atomic replacement failure",
    ):
        try:
            require_exact_atomic_failure(observed)
        except SystemExit as exc:
            if str(exc) != f"unexpected atomic-write failure: {observed}":
                raise SystemExit(f"atomic failure classifier rejected outside intended guard: {exc}") from exc
        else:
            raise SystemExit("atomic failure classifier accepted unrelated replacement diagnostic")


def load_generator():
    spec = importlib.util.spec_from_file_location("ops_p0_007_snapshot_atomic_negative", GENERATOR)
    if spec is None or spec.loader is None:
        raise SystemExit("cannot load strict snapshot generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    prove_identity_classifier()
    prove_exact_failure_classifier()
    if not GENERATOR.is_file() or GENERATOR.is_symlink() or GENERATOR.resolve(strict=True).relative_to(ROOT) != GENERATOR.relative_to(ROOT):
        raise SystemExit("strict snapshot atomic negative generator source path drift")
    module = load_generator()
    atomic_write = getattr(module, "atomic_write_text", None)
    if not callable(atomic_write):
        raise SystemExit("strict snapshot atomic writer missing")

    target = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
    before = target.read_bytes()
    before_mode = stat.S_IMODE(target.stat().st_mode)
    status_before = STATUS.read_bytes()
    status_mode = stat.S_IMODE(STATUS.stat().st_mode)
    protected_before = {path: protected_identity(path) for path in (target, STATUS, GENERATOR)}
    temp_prefix = f".{target.name}."
    before_temps = {p.name for p in target.parent.glob(f"{temp_prefix}*.tmp")}

    real_replace = os.replace
    target_replace_attempts = 0

    def reject_replace(src, dst):
        nonlocal target_replace_attempts
        if Path(dst) == target:
            target_replace_attempts += 1
            raise OSError("injected atomic replacement failure")
        return real_replace(src, dst)

    try:
        with mock.patch.object(module.os, "replace", side_effect=reject_replace):
            atomic_write(target, before.decode("utf-8") + "\n")
    except SystemExit as exc:
        require_exact_atomic_failure(str(exc))
    else:
        raise SystemExit("injected atomic replacement failure was accepted")

    if target_replace_attempts != 1:
        raise SystemExit(f"expected exactly one injected canonical replacement attempt, got {target_replace_attempts}")
    if target.read_bytes() != before:
        raise SystemExit("failed atomic replacement mutated canonical snapshot bytes")
    if stat.S_IMODE(target.stat().st_mode) != before_mode:
        raise SystemExit("failed atomic replacement mutated canonical snapshot mode")
    if STATUS.read_bytes() != status_before or stat.S_IMODE(STATUS.stat().st_mode) != status_mode:
        raise SystemExit("failed atomic replacement mutated canonical production status bytes/mode")
    for path, original_identity in protected_before.items():
        if protected_identity(path) != original_identity:
            raise SystemExit(f"failed atomic replacement changed protected path identity: {path.relative_to(ROOT)}")
    after_temps = {p.name for p in target.parent.glob(f"{temp_prefix}*.tmp")}
    if after_temps != before_temps:
        raise SystemExit("failed atomic replacement left temporary residue")

    print("OPS-P0-007 strict snapshot atomic replacement negative proof: PASS")
    print("exact injected replacement failure and one canonical target attempt verified: true")
    print("canonical production status bytes/mode unchanged: true")
    print("snapshot/status/generator source and parent identity unchanged: true")
    print("isolated file/parent symlink identity bypass accepted: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
