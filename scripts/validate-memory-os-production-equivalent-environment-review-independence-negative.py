#!/usr/bin/env python3
"""Prove independent-review evidence refs and helper authority remain canonical and repository-contained."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-review-independence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_environment_review_independence_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load environment review-independence validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(validator: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except validator.Fail:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name}: leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"{name}: invalid review authority unexpectedly accepted")


def main() -> int:
    require(VALIDATOR.is_file(), "environment review-independence validator missing")
    validator = load_validator()
    real_root = validator.ROOT
    real_helper = validator.HELPER

    with tempfile.TemporaryDirectory(prefix="memory-os-review-ref-root-") as root_tmp, tempfile.TemporaryDirectory(prefix="memory-os-review-ref-external-") as external_tmp:
        root = Path(root_tmp)
        canonical = root / "review.json"
        canonical.write_text("{}\n", encoding="utf-8")
        external = Path(external_tmp) / "external-review.json"
        external.write_text("{}\n", encoding="utf-8")

        validator.ROOT = root
        try:
            require(validator.repo_ref("review.json", "review") == "review.json", "canonical review ref rejected")
            expect_rejected(validator, "absolute review ref", lambda: validator.repo_ref(str(canonical.resolve()), "review"))
            expect_rejected(validator, "parent traversal review ref", lambda: validator.repo_ref("nested/../review.json", "review"))

            escaped = root / "escaped-review.json"
            escaped.symlink_to(external)
            expect_rejected(validator, "review ref symlink escape", lambda: validator.repo_ref("escaped-review.json", "review"))

            loop = root / "loop-review.json"
            loop.symlink_to(loop.name)
            expect_rejected(validator, "review ref symlink loop", lambda: validator.repo_ref("loop-review.json", "review"))
        finally:
            validator.ROOT = real_root

    with tempfile.TemporaryDirectory(prefix="memory-os-review-helper-root-") as root_tmp, tempfile.TemporaryDirectory(prefix="memory-os-review-helper-external-") as external_tmp:
        root = Path(root_tmp)
        scripts = root / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        external_helper = Path(external_tmp) / "memory_os_environment_generation_eligibility.py"
        external_helper.write_text("def derive(*args, **kwargs):\n    return {}\n", encoding="utf-8")
        helper_link = scripts / "memory_os_environment_generation_eligibility.py"
        helper_link.symlink_to(external_helper)

        validator.ROOT = root
        validator.HELPER = helper_link
        try:
            expect_rejected(validator, "generation eligibility helper symlink escape", validator.load_helper)
        finally:
            validator.ROOT = real_root
            validator.HELPER = real_helper

    validator.HELPER = ROOT / "scripts/validate-memory-os-production-equivalent-environment-review-independence.py"
    try:
        expect_rejected(validator, "generation eligibility helper executable substitution", validator.load_helper)
    finally:
        validator.HELPER = real_helper

    print("Environment review-independence authority negative suite PASS")
    print("review ref symlink escape accepted: false")
    print("review ref symlink loop accepted: false")
    print("eligibility helper symlink escape accepted: false")
    print("eligibility helper executable substitution accepted: false")
    print("review evidence created: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT REVIEW INDEPENDENCE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
