#!/usr/bin/env python3
"""Prove promotion-review reconcile rolls back when aggregate operability rejects."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-promotion-review.py"


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


def main() -> int:
    reconciler = load_module(RECONCILER, "memory_os_promotion_review_reconcile_negative")
    original_contract = reconciler.CONTRACT.read_bytes()
    original_registry = reconciler.REGISTRY.read_bytes()
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
        require(reconciler.CONTRACT.read_bytes() == original_contract, "promotion review contract changed after aggregate rejection")
        require(reconciler.REGISTRY.read_bytes() == original_registry, "promotion review registry changed after aggregate rejection")
    finally:
        reconciler.run_validator = original_run_validator
        reconciler.write_text = original_write_text
        reconciler.CONTRACT.write_bytes(original_contract)
        reconciler.REGISTRY.write_bytes(original_registry)

    print("Memory OS backup/restore promotion review reconcile negative PASS")
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
