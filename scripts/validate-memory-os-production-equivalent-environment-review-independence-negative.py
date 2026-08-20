#!/usr/bin/env python3
"""Prove independent-review evidence refs, counts, contract shape and helper authority remain fail-closed."""

from __future__ import annotations

import copy
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

    require(validator.exact_int(0, "zero") == 0, "canonical zero count rejected")
    require(validator.exact_int(3, "positive") == 3, "canonical positive count rejected")
    for name, value in (
        ("boolean false count", False),
        ("boolean true count", True),
        ("negative count", -1),
        ("string count", "0"),
        ("null count", None),
    ):
        expect_rejected(validator, name, lambda value=value: validator.exact_int(value, name))

    canonical_contract = validator.load(validator.CONTRACT)
    validator.validate_contract_shape(canonical_contract)
    contract_mutations: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
        ("unknown root field", lambda value: value.__setitem__("automaticPromotionAuthorized", True)),
        ("missing root field", lambda value: value.pop("workflow")),
        ("unknown rule field", lambda value: value["rules"].__setitem__("automaticPromotionAllowed", True)),
        ("missing rule field", lambda value: value["rules"].pop("productionReadyForbidden")),
        ("unknown boundary field", lambda value: value["currentBoundary"].__setitem__("productionAuthorization", "APPROVED")),
        ("missing boundary field", lambda value: value["currentBoundary"].pop("productionReady")),
    )
    for name, mutate in contract_mutations:
        candidate = copy.deepcopy(canonical_contract)
        mutate(candidate)
        expect_rejected(validator, name, lambda candidate=candidate: validator.validate_contract_shape(candidate))

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
    print("boolean or invalid review-independence count accepted: false")
    print("unknown or missing review-independence contract fields accepted: false")
    print("unknown or missing review-independence rules accepted: false")
    print("unknown or missing review-independence boundary fields accepted: false")
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
