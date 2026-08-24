#!/usr/bin/env python3
"""Focused negative for independent-review execution transport authority."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-independent-review.py")
VALIDATOR = ROOT / VALIDATOR_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator() -> Any:
    require(VALIDATOR.is_file() and not VALIDATOR.is_symlink(), "canonical independent-review validator missing or symlinked")
    require(VALIDATOR.resolve(strict=True).relative_to(ROOT.resolve()) == VALIDATOR_REL, "canonical independent-review validator path drift")
    spec = importlib.util.spec_from_file_location("memory_os_generation_independent_review_transport_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load independent-review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_transport_rejected(module: Any, mutate: Callable[[], None], restore: Callable[[], None], label: str) -> None:
    mutate()
    try:
        try:
            module.candidate_reviews_approved({})
        except module.Fail as exc:
            require("execution transport drift" in str(exc), f"{label} rejected at wrong boundary: {exc}")
            return
        raise Fail(f"transport substitution unexpectedly passed: {label}")
    finally:
        restore()


def main() -> int:
    module = load_validator()
    canonical_contract = module.CONTRACT.read_bytes()
    canonical_registry = module.REGISTRY.read_bytes()

    original_run = module.subprocess.run
    expect_transport_rejected(
        module,
        lambda: setattr(module.subprocess, "run", lambda *_args, **_kwargs: None),
        lambda: setattr(module.subprocess, "run", original_run),
        "subprocess.run substitution",
    )

    original_spec = module.importlib.util.spec_from_file_location
    expect_transport_rejected(
        module,
        lambda: setattr(module.importlib.util, "spec_from_file_location", lambda *_args, **_kwargs: None),
        lambda: setattr(module.importlib.util, "spec_from_file_location", original_spec),
        "spec_from_file_location substitution",
    )

    original_module_from_spec = module.importlib.util.module_from_spec
    expect_transport_rejected(
        module,
        lambda: setattr(module.importlib.util, "module_from_spec", lambda *_args, **_kwargs: object()),
        lambda: setattr(module.importlib.util, "module_from_spec", original_module_from_spec),
        "module_from_spec substitution",
    )

    require(module.CONTRACT.read_bytes() == canonical_contract, "transport substitution mutated canonical generation evidence contract")
    require(module.REGISTRY.read_bytes() == canonical_registry, "transport substitution mutated canonical generation evidence registry")
    print("Memory OS generation independent-review transport negative PASS")
    print("subprocess transport substitution accepted: false")
    print("module loader transport substitution accepted: false")
    print("canonical authority mutation: false")
    print("human production promotion remains separate: true")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION INDEPENDENT REVIEW TRANSPORT NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
