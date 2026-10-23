#!/usr/bin/env python3
"""Prove the strict OPS-P0-007 snapshot generator cannot bypass canonical execution helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    require(GENERATOR.is_file() and not GENERATOR.is_symlink(), "canonical strict snapshot generator missing or symlinked")
    require(GENERATOR.resolve(strict=True).relative_to(ROOT.resolve()) == GENERATOR.relative_to(ROOT), "strict snapshot generator path drift")
    spec = importlib.util.spec_from_file_location("memory_os_ops_p0_007_snapshot_generator_execution_authority_negative", GENERATOR)
    require(spec is not None and spec.loader is not None, "cannot load strict snapshot generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def protected_state(path: Path) -> tuple[Any, ...]:
    """Capture bytes plus file and parent identity; following a symlink is not enough."""
    entry = path.lstat()
    parent = path.parent.lstat()
    return (
        path.read_bytes(),
        (entry.st_mode, entry.st_dev, entry.st_ino),
        (parent.st_mode, parent.st_dev, parent.st_ino),
        path.resolve(strict=True),
    )


def prove_symlink_identity_rejected() -> None:
    # Only mutate a temporary authority fixture, never the canonical checkout.
    with tempfile.TemporaryDirectory(prefix="ops-p0-007-generator-identity-") as tmp:
        root = Path(tmp)
        parent = root / "authority"
        parent.mkdir()
        path = parent / "snapshot.json"
        path.write_text('{"productionDecision":"NO_GO"}\n', encoding="utf-8")
        original_state = protected_state(path)
        original = parent / "original.json"
        path.rename(original)
        path.symlink_to(original.name)
        require(path.read_bytes() == original.read_bytes(), "symlink fixture content drift")
        require(
            protected_state(path) != original_state,
            "symlink alias with identical bytes bypassed protected identity",
        )
        path.unlink()
        original.rename(path)
        require(protected_state(path) == original_state, "identity fixture restoration drift")

        actual_parent = root / "actual"
        parent.rename(actual_parent)
        parent.symlink_to(actual_parent.name, target_is_directory=True)
        require(path.read_bytes() == original_state[0], "parent symlink fixture content drift")
        require(
            protected_state(path) != original_state,
            "parent symlink alias with identical bytes bypassed protected identity",
        )


def expect_rejected(module: Any, field: str, replacement: Any) -> None:
    expected = (
        "strict snapshot generator execution guard drift"
        if field == "enforce_execution_authority"
        else "strict snapshot generator runtime authority guard drift"
        if field == "enforce_runtime_authorities"
        else "strict snapshot generator execution helper drift"
    )
    original = getattr(module, field)
    protected_before = {path: protected_state(path) for path in (SNAPSHOT, STATUS, GENERATOR)}
    setattr(module, field, replacement)
    rejected = False
    try:
        module.main()
    except SystemExit as exc:
        require(
            isinstance(exc.code, str) and exc.code == expected,
            f"{field} rejected outside intended strict snapshot guard: {exc}",
        )
        rejected = True
    finally:
        setattr(module, field, original)
    require(rejected, f"strict snapshot generator accepted substituted execution authority: {field}")
    for path, state in protected_before.items():
        require(protected_state(path) == state, f"{field} rejection changed protected authority identity: {path.relative_to(ROOT)}")


def main() -> int:
    module = load_module()
    prove_symlink_identity_rejected()
    baseline_state = {path: protected_state(path) for path in (SNAPSHOT, STATUS, GENERATOR)}

    substitutions = (
        ("enforce_execution_authority", lambda: None),
        ("require_exact_repo_file", lambda *_args: None),
        ("enforce_runtime_authorities", lambda: None),
        ("atomic_write_text", lambda *_args: None),
        ("load", lambda _path: {}),
        ("load_module", lambda *_args: object()),
        ("validate_registry", lambda *_args: []),
        ("run_canonical_validator", lambda *_args: None),
        ("run_full_admission_validators", lambda: None),
        ("validate_generated_snapshot", lambda: None),
        ("load_helper", lambda: object()),
    )
    # Canonical guard must pass before any substitution can count as a rejection.
    module.enforce_execution_authority()
    for field, replacement in substitutions:
        expect_rejected(module, field, replacement)

    module.enforce_execution_authority()
    for path, state in baseline_state.items():
        require(protected_state(path) == state, f"generator execution authority probes changed protected identity: {path.relative_to(ROOT)}")
    json.loads(baseline_state[SNAPSHOT][0].decode("utf-8"))
    json.loads(baseline_state[STATUS][0].decode("utf-8"))

    print("Memory OS OPS-P0-007 strict snapshot generator execution authority negative PASS")
    print(f"execution helper substitutions rejected: {len(substitutions)}")
    print("full admission validator no-op substitution accepted: false")
    print("post-write validator no-op substitution accepted: false")
    print("atomic publication helper substitution accepted: false")
    print("rejected probes changed canonical snapshot/status/generator identity: false")
    print("isolated file and parent symlink identity bypass accepted: false")
    print("production evidence created: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError, json.JSONDecodeError) as exc:
        print(f"OPS-P0-007 SNAPSHOT GENERATOR EXECUTION AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
