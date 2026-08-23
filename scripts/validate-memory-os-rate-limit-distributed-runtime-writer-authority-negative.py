#!/usr/bin/env python3
"""Prove the real distributed rate-limit runtime writer cannot substitute canonical authorities."""

from __future__ import annotations

import importlib.util
import inspect
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-rate-limit-distributed-runtime.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_rate_limit_runtime_writer_authority_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load distributed runtime writer")
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
    require(WRITER.is_file(), "distributed runtime writer missing")
    writer = load_writer()
    require(callable(getattr(writer, "require_actual_cli_authorities", None)),
            "distributed runtime writer CLI authority guard missing")
    require("require_actual_cli_authorities()" in inspect.getsource(writer.main),
            "distributed runtime writer main does not enforce CLI authority guard")
    writer.require_actual_cli_authorities()

    canonical_registry_before = writer.CANONICAL_REGISTRY.read_bytes()
    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-runtime-authority-") as temp_dir:
        outside = Path(temp_dir) / "outside-authority.json"
        outside.write_text("{}\n", encoding="utf-8")
        substitutions = (
            ("CONTRACT", writer.CANONICAL_CONTRACT),
            ("REGISTRY", writer.CANONICAL_REGISTRY),
            ("POLICY", writer.CANONICAL_POLICY),
            ("GEN_REGISTRY", writer.CANONICAL_GEN_REGISTRY),
            ("GEN_WRITER", writer.CANONICAL_GEN_WRITER),
            ("VALIDATOR", writer.CANONICAL_VALIDATOR),
            ("LOCK", writer.CANONICAL_LOCK),
        )
        for attribute, canonical in substitutions:
            original = getattr(writer, attribute)
            try:
                setattr(writer, attribute, outside)
                expect_rejected(
                    f"distributed runtime writer CLI {attribute} substitution",
                    writer.require_actual_cli_authorities,
                    writer.Fail,
                )
            finally:
                setattr(writer, attribute, original)
            require(getattr(writer, attribute) == canonical,
                    f"distributed runtime writer CLI {attribute} canonical authority not restored")

        original_review_root = writer.REVIEW_ROOT
        try:
            writer.REVIEW_ROOT = Path("docs/evidence/elsewhere")
            expect_rejected(
                "distributed runtime writer CLI REVIEW_ROOT substitution",
                writer.require_actual_cli_authorities,
                writer.Fail,
            )
        finally:
            writer.REVIEW_ROOT = original_review_root
        require(writer.REVIEW_ROOT == writer.CANONICAL_REVIEW_ROOT,
                "distributed runtime writer CLI review namespace not restored")

    writer.require_actual_cli_authorities()
    require(writer.CANONICAL_REGISTRY.read_bytes() == canonical_registry_before,
            "distributed runtime writer authority negative mutated canonical registry")
    print("Memory OS distributed rate-limit runtime writer authority negative suite PASS")
    print("writer CLI data/executable/review/lock substitution accepted: false")
    print("distributed runtime evidence generated: false")
    print("production evidence generated: false")
    print("production readiness changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DISTRIBUTED RATE LIMIT RUNTIME WRITER AUTHORITY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
