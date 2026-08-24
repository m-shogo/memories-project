#!/usr/bin/env python3
"""Fail closed if generation-evidence validation transport is substituted."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator() -> Any:
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical generation-evidence validator missing or symlinked")
    require(
        VALIDATOR.resolve(strict=True) == VALIDATOR,
        "canonical generation-evidence validator resolved path drift",
    )
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_transport_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load generation-evidence validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(module: Any, label: str, mutate: Callable[[], None], restore: Callable[[], None], expected: str) -> None:
    mutate()
    try:
        try:
            module.main()
        except module.Fail as exc:
            require(expected in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"generation-evidence transport substitution unexpectedly passed: {label}")
    finally:
        restore()


def main() -> int:
    module = load_validator()

    original_run = module.subprocess.run
    expect_rejected(
        module,
        "subprocess.run",
        lambda: setattr(module.subprocess, "run", lambda *_args, **_kwargs: None),
        lambda: setattr(module.subprocess, "run", original_run),
        "subprocess execution transport drift",
    )

    original_spec = module.importlib.util.spec_from_file_location
    expect_rejected(
        module,
        "importlib spec loader",
        lambda: setattr(module.importlib.util, "spec_from_file_location", lambda *_args, **_kwargs: None),
        lambda: setattr(module.importlib.util, "spec_from_file_location", original_spec),
        "import spec transport drift",
    )

    original_module_from_spec = module.importlib.util.module_from_spec
    expect_rejected(
        module,
        "importlib module loader",
        lambda: setattr(module.importlib.util, "module_from_spec", lambda *_args, **_kwargs: None),
        lambda: setattr(module.importlib.util, "module_from_spec", original_module_from_spec),
        "module loader transport drift",
    )

    print("Memory OS generation-evidence execution transport negative PASS")
    print("subprocess validation transport substitution accepted: false")
    print("import spec transport substitution accepted: false")
    print("module loader transport substitution accepted: false")
    print("generation evidence created: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE TRANSPORT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
