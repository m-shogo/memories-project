#!/usr/bin/env python3
"""Prove environment review-independence reconciliation pins authorities, rejects helper substitution and rolls back failed validation."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-equivalent-environment-review-independence.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-review-independence-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_environment_review_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load environment review reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(reconciler, name: str, expected: str) -> None:
    try:
        reconciler.main()
    except reconciler.Fail as exc:
        require(expected in str(exc), f"{name} rejected at wrong boundary: {exc}")
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"{name} unexpectedly accepted")


def main() -> int:
    require(RECONCILER.is_file(), "environment review reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()
    canonical_contract = reconciler.CONTRACT.read_bytes()

    original_validator = reconciler.VALIDATOR
    reconciler.VALIDATOR = reconciler.HELPER
    try:
        expect_rejected(reconciler, "review independence validator executable substitution", "review independence validator authority drift")
        require(reconciler.CONTRACT.read_bytes() == canonical_contract, "validator substitution changed review-independence contract")
    finally:
        reconciler.VALIDATOR = original_validator

    original_generation_registry = reconciler.GEN_REGISTRY
    reconciler.GEN_REGISTRY = reconciler.CONTRACT
    try:
        expect_rejected(reconciler, "review independence generation registry substitution", "generation registry authority drift")
        require(reconciler.CONTRACT.read_bytes() == canonical_contract, "registry substitution changed review-independence contract")
    finally:
        reconciler.GEN_REGISTRY = original_generation_registry

    with tempfile.TemporaryDirectory(prefix=".tmp-environment-review-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        contract_copy = tmp / CONTRACT.name
        shutil.copyfile(CONTRACT, contract_copy)
        original_contract = contract_copy.read_bytes()
        failing_validator = tmp / "forced-validator-failure.py"
        failing_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(41)\n", encoding="utf-8")

        reconciler.CONTRACT = contract_copy
        reconciler.GEN_REGISTRY = GEN_REGISTRY
        real_helper = reconciler.HELPER
        reconciler.HELPER = RECONCILER
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("generation eligibility helper executable authority drift" in str(exc), f"helper substitution rejected at wrong boundary: {exc}")
        except Exception as exc:
            raise Fail(f"helper substitution leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
        else:
            raise Fail("generation eligibility helper substitution unexpectedly accepted")
        finally:
            reconciler.HELPER = real_helper
        require(contract_copy.read_bytes() == original_contract, "helper substitution changed review-independence contract")

        reconciler.VALIDATOR = failing_validator
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("post-reconcile review independence validator failed" in str(exc), f"post-validation failure rejected at wrong boundary: {exc}")
        except Exception as exc:
            raise Fail(f"post-validation failure leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
        else:
            raise Fail("forced review-independence post-validation failure unexpectedly accepted")
        require(contract_copy.read_bytes() == original_contract, "failed review-independence validation left contract mutation")

    print("Environment review-independence reconcile negative suite PASS")
    print("review validator executable substitution accepted: false")
    print("generation registry substitution accepted: false")
    print("eligibility helper substitution accepted: false")
    print("failed post-validation leaves authority mutation behind: false")
    print("review evidence created: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT REVIEW RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
