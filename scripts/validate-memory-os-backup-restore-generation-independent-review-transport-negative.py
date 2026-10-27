#!/usr/bin/env python3
"""Focused negative for independent-review execution transport authority."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import Any, Callable

from ops_independent_review_fixture_loader import FixtureImportFail, load_pinned_module, read_pinned_source

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
    return load_pinned_module(ROOT, VALIDATOR, "memory_os_generation_independent_review_transport_negative")


SOURCE_ORDER_EXECUTION_NEGATIVE = (
    ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review-execution-negative.py"
)


def require_source_order_pinned_import(source: str) -> None:
    tree = ast.parse(source)
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == "prove_source_order_json_reader"]
    require(len(functions) == 1, "source-order negative import function drift")
    fn = functions[0]
    pinned = [node for node in ast.walk(fn)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
              and node.func.id == "load_checked_module"]
    unsafe = [node for node in ast.walk(fn)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr == "spec_from_file_location"]
    require(len(pinned) == 1 and not unsafe, "source-order negative import must be descriptor-pinned")


def prove_source_order_import_guard() -> None:
    try:
        raw = read_pinned_source(ROOT, SOURCE_ORDER_EXECUTION_NEGATIVE)
        source = raw.decode("utf-8")
    except (FixtureImportFail, UnicodeDecodeError):
        raise Fail("source-order negative source rejected") from None
    require_source_order_pinned_import(source)
    old = 'module = load_checked_module(path_to_validator, "memory_os_source_order_json_negative")'
    require(source.count(old) == 1, "source-order pinned negative mutation anchor drift")
    for label, replacement in (
        ("delete import", "module = None"),
        ("restore unsafe default loader", 'module = importlib.util.spec_from_file_location("unsafe", path_to_validator)'),
    ):
        mutant = source.replace(old, replacement, 1)
        try:
            require_source_order_pinned_import(mutant)
        except Fail:
            continue
        raise Fail("source-order pinned import weakening accepted: " + label)
    print("PASS: independent source-order negative importer rejects 2 source mutations")


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
    prove_source_order_import_guard()
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
