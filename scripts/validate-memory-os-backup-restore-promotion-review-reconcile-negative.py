#!/usr/bin/env python3
"""Prove promotion-review reconcile pins canonical authorities and rolls back aggregate rejection."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-promotion-review.py"
CANONICAL_CONTRACT = ROOT / "contracts/operations/backup-restore-promotion-review.v1.json"
CANONICAL_REGISTRY = ROOT / "contracts/operations/backup-restore-promotion-review-registry.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(reconciler: Any, name: str, expected: str) -> None:
    try:
        reconciler.main()
    except reconciler.Fail as exc:
        require(expected in str(exc), f"{name} rejected at wrong boundary: {exc}")
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"{name} unexpectedly accepted")


def assert_canonical_unchanged(original_contract: bytes, original_registry: bytes, name: str) -> None:
    require(CANONICAL_CONTRACT.read_bytes() == original_contract, f"{name} changed promotion review contract")
    require(CANONICAL_REGISTRY.read_bytes() == original_registry, f"{name} changed promotion review registry")


def expect_authority_substitution_rejected(
    reconciler: Any,
    attribute: str,
    substitute: Path,
    name: str,
    expected: str,
    original_contract: bytes,
    original_registry: bytes,
) -> None:
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, substitute)
    try:
        expect_rejected(reconciler, name, expected)
        assert_canonical_unchanged(original_contract, original_registry, name)
    finally:
        setattr(reconciler, attribute, original)


def main() -> int:
    reconciler = load_module(RECONCILER, "memory_os_promotion_review_reconcile_negative")
    original_contract = CANONICAL_CONTRACT.read_bytes()
    original_registry = CANONICAL_REGISTRY.read_bytes()

    expect_authority_substitution_rejected(
        reconciler,
        "CONTRACT",
        reconciler.REGISTRY,
        "promotion review contract substitution",
        "promotion review contract authority drift",
        original_contract,
        original_registry,
    )
    expect_authority_substitution_rejected(
        reconciler,
        "REGISTRY",
        reconciler.GEN_REGISTRY,
        "promotion review registry substitution",
        "promotion review registry authority drift",
        original_contract,
        original_registry,
    )
    expect_authority_substitution_rejected(
        reconciler,
        "GEN_REGISTRY",
        reconciler.REGISTRY,
        "generation evidence registry substitution",
        "generation evidence registry authority drift",
        original_contract,
        original_registry,
    )
    expect_authority_substitution_rejected(
        reconciler,
        "WRITER",
        reconciler.VALIDATOR,
        "promotion review writer executable substitution",
        "promotion review writer authority drift",
        original_contract,
        original_registry,
    )
    expect_authority_substitution_rejected(
        reconciler,
        "VALIDATOR",
        reconciler.OPERABILITY_VALIDATOR,
        "promotion review validator executable substitution",
        "promotion review validator authority drift",
        original_contract,
        original_registry,
    )
    expect_authority_substitution_rejected(
        reconciler,
        "OPERABILITY_VALIDATOR",
        reconciler.VALIDATOR,
        "operability validator executable substitution",
        "operability validator authority drift",
        original_contract,
        original_registry,
    )
    expect_authority_substitution_rejected(
        reconciler,
        "STATUS",
        reconciler.CONTRACT,
        "production operability status substitution",
        "production operability status authority drift",
        original_contract,
        original_registry,
    )

    original_run_validator = reconciler.run_validator
    original_write_text = reconciler.write_text
    labels: list[str] = []
    injected_contract_write = False

    def fake_run_validator(path: Path, label: str) -> None:
        labels.append(label)
        if path == reconciler.OPERABILITY_VALIDATOR:
            raise reconciler.Fail("synthetic aggregate operability rejection")
        require(path == reconciler.VALIDATOR, f"unexpected validator path: {path}")

    def tracked_write_text(path: Path, text: str) -> None:
        nonlocal injected_contract_write
        if path == reconciler.CONTRACT and not injected_contract_write:
            injected_contract_write = True
            original_write_text(path, text + "\n")
            return
        original_write_text(path, text)

    reconciler.run_validator = fake_run_validator
    reconciler.write_text = tracked_write_text
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("synthetic aggregate operability rejection" in str(exc), f"unexpected reconcile rejection: {exc}")
        else:
            raise Fail("aggregate operability rejection unexpectedly accepted")

        require(injected_contract_write, "transaction did not reach contract write before aggregate rejection")
        require(
            labels == ["promotion review validator", "aggregate operability validator"],
            f"unexpected validator order: {labels}",
        )
        assert_canonical_unchanged(original_contract, original_registry, "aggregate operability rejection")
    finally:
        reconciler.run_validator = original_run_validator
        reconciler.write_text = original_write_text
        CANONICAL_CONTRACT.write_bytes(original_contract)
        CANONICAL_REGISTRY.write_bytes(original_registry)

    print("Memory OS backup/restore promotion review reconcile negative PASS")
    print("promotion contract substitution accepted: false")
    print("promotion registry substitution accepted: false")
    print("generation evidence registry substitution accepted: false")
    print("promotion writer executable substitution accepted: false")
    print("promotion validator executable substitution accepted: false")
    print("operability validator executable substitution accepted: false")
    print("production operability status substitution accepted: false")
    print("promotion validator ran before aggregate operability validator: true")
    print("aggregate operability rejection rolled back promotion registry/contract: true")
    print("production evidence created: false")
    print("production traffic changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE PROMOTION REVIEW RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
