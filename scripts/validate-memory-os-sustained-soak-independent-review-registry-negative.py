#!/usr/bin/env python3
"""Verify the sustained-soak writer rejects corrupt canonical authority before append."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/sustained-soak-independent-review-registry.v1.json"
WRITER_PATH = ROOT / "scripts/register-memory-os-sustained-soak-independent-review.py"


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location("memory_os_sustained_soak_review_writer_negative", WRITER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to import sustained-soak independent review writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(value: dict[str, Any]) -> None:
    REGISTRY.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expect_rejected(writer: Any, name: str, mutate: Callable[[dict[str, Any]], None], original: bytes) -> None:
    value = json.loads(original.decode("utf-8"))
    mutate(value)
    write_json(value)
    corrupted = REGISTRY.read_bytes()
    try:
        try:
            writer.validate_existing_registry()
        except writer.Fail:
            pass
        else:
            raise AssertionError(f"{name}: corrupt registry was accepted")
        if REGISTRY.read_bytes() != corrupted:
            raise AssertionError(f"{name}: rejected validation mutated registry")
    finally:
        REGISTRY.write_bytes(original)


def main() -> int:
    writer = load_writer()
    original = REGISTRY.read_bytes()
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda value: value.__setitem__("schemaVersion", "broken")),
        ("append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        ("boolean criteria count", lambda value: value.__setitem__("registeredCriteriaCount", False)),
        ("criteria count drift", lambda value: value.__setitem__("registeredCriteriaCount", 1)),
        ("boolean review count", lambda value: value.__setitem__("registeredReviewCount", False)),
        ("review count drift", lambda value: value.__setitem__("registeredReviewCount", 1)),
        ("approved criteria count drift", lambda value: value.__setitem__("approvedLeakStabilityCriteriaCount", 1)),
        ("passing review count drift", lambda value: value.__setitem__("passingIndependentReviewCount", 1)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("production readiness promotion", lambda value: value.__setitem__("productionReady", True)),
        ("leak proof promotion", lambda value: value.__setitem__("leakProof", True)),
    ]
    try:
        for name, mutate in cases:
            expect_rejected(writer, name, mutate, original)
    finally:
        REGISTRY.write_bytes(original)

    print("PASS: sustained-soak independent review registry corruption is rejected before append")
    print(f"cases: {len(cases)}")
    print("canonical registry mutated by rejected cases: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
