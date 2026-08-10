#!/usr/bin/env python3
"""Prove generation-validator authority refs cannot escape the repository."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-generation.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_generation_validator_authority_path_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load generation validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], object], failure_type: type[Exception]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    validator = load_validator()
    original_root = validator.ROOT
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-validator-root-") as root_tmp, tempfile.TemporaryDirectory(prefix="memory-os-generation-validator-external-") as external_tmp:
        root = Path(root_tmp)
        external = Path(external_tmp) / "external.yml"
        local = root / "workflow.yml"
        local.write_text("name: local\n", encoding="utf-8")
        external.write_text("name: external\n", encoding="utf-8")
        escape = root / "escaped.yml"
        escape.symlink_to(external)
        validator.ROOT = root
        try:
            resolved = validator.repo_file("workflow.yml", "workflow")
            require(resolved == local.resolve(), "canonical repository authority ref rejected")
            expect_rejected(
                "absolute generation validator authority ref",
                lambda: validator.repo_file(str(local.resolve()), "workflow"),
                validator.Fail,
            )
            expect_rejected(
                "parent-traversal generation validator authority ref",
                lambda: validator.repo_file("nested/../workflow.yml", "workflow"),
                validator.Fail,
            )
            expect_rejected(
                "generation validator authority symlink escapes repository",
                lambda: validator.repo_file("escaped.yml", "workflow"),
                validator.Fail,
            )
        finally:
            validator.ROOT = original_root

    print("Memory OS production-equivalent generation validator authority-path negative suite PASS")
    print("absolute authority refs accepted: false")
    print("parent-traversal authority refs accepted: false")
    print("repo-local symlink to external authority accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION AUTHORITY-PATH NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
