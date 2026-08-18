#!/usr/bin/env python3
"""Focused fail-closed proof for rollback rehearsal transactional append."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/request-memory-os-rollback-rehearsal.py"
CONTRACT_PATH = ROOT / "contracts/operations/rollback-rehearsal-gate-contract.v1.json"
RELEASE_REGISTRY_PATH = ROOT / "contracts/operations/release-baseline-registry.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/rollback-rehearsal-registry.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location("rollback_rehearsal_append_negative", WRITER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load rollback rehearsal writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(action: Any, label: str) -> None:
    try:
        action()
    except Exception:
        return
    raise Fail(f"rollback rehearsal transactional authority accepted invalid case: {label}")


def main() -> int:
    writer = load_writer()
    contract = load(CONTRACT_PATH)
    release_registry = load(RELEASE_REGISTRY_PATH)
    registry = load(REGISTRY_PATH)

    writer.validate_registry_for_append(
        copy.deepcopy(registry), copy.deepcopy(contract), copy.deepcopy(release_registry)
    )

    weakened = copy.deepcopy(contract)
    weakened["admissionGuards"] = [
        item for item in weakened["admissionGuards"]
        if item != writer.TRANSACTIONAL_APPEND_GUARD
    ]
    expect_rejected(
        lambda: writer.validate_registry_for_append(
            copy.deepcopy(registry), weakened, copy.deepcopy(release_registry)
        ),
        "missing transactional append guard",
    )

    original_bytes = REGISTRY_PATH.read_bytes()
    original_atomic_write = writer.atomic_write
    original_validator = writer.validate_registry_for_append
    observed_write = {"changed": False}
    candidate = copy.deepcopy(registry)
    candidate["limitations"] = list(registry.get("limitations", [])) + [
        "synthetic rollback sentinel"
    ]

    def observing_write(value: dict[str, Any]) -> None:
        original_atomic_write(value)
        observed_write["changed"] = REGISTRY_PATH.read_bytes() != original_bytes

    def fail_after_write(*_args: Any, **_kwargs: Any) -> None:
        raise writer.RequestFailure("synthetic post-append canonical validation failure")

    try:
        writer.atomic_write = observing_write
        writer.validate_registry_for_append = fail_after_write
        expect_rejected(
            lambda: writer.write_registry_transactionally(
                candidate, copy.deepcopy(contract), copy.deepcopy(release_registry)
            ),
            "post-append canonical validation failure",
        )
        require(observed_write["changed"], "transactional negative did not exercise registry write")
        require(
            REGISTRY_PATH.read_bytes() == original_bytes,
            "rollback rehearsal registry was not restored after post-append validation failure",
        )
    finally:
        writer.atomic_write = original_atomic_write
        writer.validate_registry_for_append = original_validator
        if REGISTRY_PATH.read_bytes() != original_bytes:
            writer.atomic_restore(original_bytes)

    print("PASS: rollback rehearsal append revalidates canonical authority and restores original registry bytes on failure")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ROLLBACK REHEARSAL APPEND ROLLBACK NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
