#!/usr/bin/env python3
"""Prove deletion-worker saturation reconcile rolls back post-write validator failures."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts" / "reconcile-memory-os-deletion-worker-saturation.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    reconciler = load_module(RECONCILER_PATH, "memory_os_deletion_worker_saturation_reconciler_negative")
    real_validator = reconciler.load_validator()
    original_contract = reconciler.CONTRACT_PATH.read_bytes()
    result = json.loads(reconciler.RESULT_PATH.read_text(encoding="utf-8"))
    expected = result.get("commitSha")
    if not isinstance(expected, str) or len(expected) != 40:
        raise AssertionError("canonical saturation result must expose a full commitSha")

    class Fail(RuntimeError):
        pass

    class FailingValidator:
        def __init__(self) -> None:
            self.contract_calls = 0

        def validate_contract(self, contract) -> None:
            self.contract_calls += 1
            real_validator.validate_contract(contract)
            if self.contract_calls == 2:
                raise Fail("synthetic post-write validation failure")

        def validate_result(self, contract, expected_sha) -> None:
            real_validator.validate_result(contract, expected_sha)

    old_expected = os.environ.get("EXPECTED_COMMIT_SHA")
    reconciler.load_validator = lambda: FailingValidator()
    os.environ["EXPECTED_COMMIT_SHA"] = expected
    try:
        try:
            reconciler.main()
        except RuntimeError as exc:
            if "synthetic post-write validation failure" not in str(exc):
                raise AssertionError(f"unexpected reconcile rejection: {exc}") from exc
        else:
            raise AssertionError("reconciler accepted synthetic post-write validator failure")

        if reconciler.CONTRACT_PATH.read_bytes() != original_contract:
            raise AssertionError("reconciler failed to restore contract bytes after post-write validation failure")
    finally:
        reconciler.CONTRACT_PATH.write_bytes(original_contract)
        if old_expected is None:
            os.environ.pop("EXPECTED_COMMIT_SHA", None)
        else:
            os.environ["EXPECTED_COMMIT_SHA"] = old_expected

    print("PASS: deletion-worker saturation reconcile rollback is fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
