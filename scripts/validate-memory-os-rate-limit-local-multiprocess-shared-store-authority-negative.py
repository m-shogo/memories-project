#!/usr/bin/env python3
"""Prove local shared-store validator authorities cannot be substituted."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-rate-limit-local-multiprocess-shared-store.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_shared_store_validator_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load local shared-store validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(label: str, action: Callable[[], object], failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {label}")
        return
    except Exception as exc:
        raise Fail(f"{label} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {label}")


def main() -> int:
    validator = load_validator()
    validator.require_runtime_authorities()
    result_before = validator.RESULT.read_bytes() if validator.RESULT.exists() else None

    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-shared-store-validator-") as temp_dir:
        outside = Path(temp_dir) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        for attribute in ("ROOT", "CONTRACT", "RESULT"):
            original = getattr(validator, attribute)
            try:
                setattr(validator, attribute, outside if attribute != "ROOT" else outside.parent)
                expect_rejected(
                    f"local shared-store validator {attribute} substitution",
                    validator.require_runtime_authorities,
                    validator.Fail,
                )
            finally:
                setattr(validator, attribute, original)

        original_refs = validator.EXPECTED_REFS
        try:
            validator.EXPECTED_REFS = dict(original_refs)
            validator.EXPECTED_REFS["runner"] = "README.md"
            expect_rejected(
                "local shared-store validator EXPECTED_REFS semantic substitution",
                validator.require_runtime_authorities,
                validator.Fail,
            )
        finally:
            validator.EXPECTED_REFS = original_refs

        for attribute in ("require", "load", "require_canonical_ref", "source_is_ancestor"):
            original = getattr(validator, attribute)
            try:
                setattr(validator, attribute, lambda *args, **kwargs: True)
                expect_rejected(
                    f"local shared-store validator {attribute} execution substitution",
                    validator.require_runtime_authorities,
                    validator.Fail,
                )
            finally:
                setattr(validator, attribute, original)

        expect_rejected(
            "local shared-store validator main guard substitution",
            lambda: validator.main(lambda: None, validator.source_is_ancestor),
            validator.Fail,
        )
        expect_rejected(
            "local shared-store validator ancestry helper substitution",
            lambda: validator.main(validator.require_runtime_authorities, lambda source: True),
            validator.Fail,
        )

    validator.require_runtime_authorities()
    if result_before is None:
        require(not validator.RESULT.exists(), "shared-store authority negative created result evidence")
    else:
        require(validator.RESULT.read_bytes() == result_before, "shared-store authority negative mutated result evidence")
    print("Memory OS local shared-store validator authority negative suite PASS")
    print("validator data/helper/semantic substitution accepted: false")
    print("production-equivalent evidence generated: false")
    print("production evidence generated: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RATE LIMIT LOCAL SHARED STORE VALIDATOR AUTHORITY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
