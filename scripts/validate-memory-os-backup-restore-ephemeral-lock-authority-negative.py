#!/usr/bin/env python3
"""Prove canonical OPS-P0-007 validators reject ephemeral append-lock authority substitution."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    (
        "recovery objectives",
        ROOT / "scripts/validate-memory-os-recovery-objectives.py",
        ROOT / "contracts/operations/.production-equivalent-environment-generation.lock",
    ),
    (
        "environment generation",
        ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py",
        ROOT / "contracts/operations/.recovery-objectives.lock",
    ),
    (
        "restore drill request",
        ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py",
        ROOT / "contracts/operations/.backup-restore-generation-evidence.lock",
    ),
    (
        "generation recovery evidence",
        ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py",
        ROOT / "contracts/operations/.backup-restore-drill-request.lock",
    ),
    (
        "human promotion review",
        ROOT / "scripts/validate-memory-os-backup-restore-promotion-review.py",
        ROOT / "contracts/operations/.backup-restore-generation-evidence.lock",
    ),
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str) -> Any:
    require(path.is_file(), f"validator missing: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load validator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    for index, (label, path, alternate_lock) in enumerate(TARGETS):
        module = load_module(path, f"memory_os_lock_authority_negative_{index}")
        canonical = getattr(module, "EXPECTED_LOCK", None)
        require(isinstance(canonical, Path), f"{label} validator missing EXPECTED_LOCK authority")
        require(callable(getattr(module, "enforce_runtime_authorities", None)), f"{label} validator missing runtime authority guard")

        module.enforce_runtime_authorities()
        require(canonical != alternate_lock, f"{label} alternate lock unexpectedly equals canonical authority")
        module.EXPECTED_LOCK = alternate_lock
        try:
            try:
                module.enforce_runtime_authorities()
            except module.Fail:
                print(f"PASS reject: {label} append-lock substitution")
            else:
                raise Fail(f"{label} validator accepted substituted append-lock authority")
        finally:
            module.EXPECTED_LOCK = canonical
        module.enforce_runtime_authorities()

    print("Memory OS backup/restore ephemeral lock authority negative suite PASS")
    print(f"validators covered: {len(TARGETS)}")
    print("ephemeral lock absence accepted: true")
    print("lock path substitution accepted: false")
    print("lock symlink accepted by canonical guard: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE EPHEMERAL LOCK AUTHORITY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
