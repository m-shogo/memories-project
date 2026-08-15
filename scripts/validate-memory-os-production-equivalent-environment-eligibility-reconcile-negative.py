#!/usr/bin/env python3
"""Prove environment-generation eligibility reconciliation is transactional and fail-closed."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-equivalent-environment-eligibility.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json"
GEN_CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
HELPER_SUBSTITUTE = ROOT / "scripts/validate-memory-os-operability.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_eligibility_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load generation eligibility reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    require(RECONCILER.is_file(), "generation eligibility reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    require(HELPER_SUBSTITUTE.is_file(), "repo-contained helper substitute missing")
    reconciler = load_reconciler()

    original_helper = reconciler.HELPER
    reconciler.HELPER = HELPER_SUBSTITUTE
    try:
        try:
            reconciler.load_helper()
        except reconciler.Fail:
            print("PASS reject before write: eligibility reconciler helper substitution")
        except Exception as exc:
            raise Fail(f"helper substitution leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
        else:
            raise Fail("eligibility reconciler helper substitution unexpectedly accepted")
    finally:
        reconciler.HELPER = original_helper

    with tempfile.TemporaryDirectory(prefix=".tmp-environment-eligibility-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        contract_copy = tmp / CONTRACT.name
        generation_contract_copy = tmp / GEN_CONTRACT.name
        shutil.copyfile(CONTRACT, contract_copy)
        shutil.copyfile(GEN_CONTRACT, generation_contract_copy)
        original_contract = contract_copy.read_bytes()

        reconciler.CONTRACT = contract_copy
        reconciler.GEN_CONTRACT = generation_contract_copy
        reconciler.GEN_REGISTRY = GEN_REGISTRY

        drifted_generation_contract = json.loads(generation_contract_copy.read_text(encoding="utf-8"))
        generation_boundary = drifted_generation_contract.get("currentBoundary")
        require(isinstance(generation_boundary, dict), "generation fixture boundary missing")
        generation_boundary["registeredGenerationCount"] = 1
        generation_contract_copy.write_text(json.dumps(drifted_generation_contract, indent=2) + "\n", encoding="utf-8")
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("generation registered count drift" in str(exc), f"generation count drift rejected at wrong boundary: {exc}")
        except Exception as exc:
            raise Fail(f"generation count drift leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
        else:
            raise Fail("generation contract count drift unexpectedly reconciled")
        require(contract_copy.read_bytes() == original_contract, "generation count drift mutated eligibility contract")
        print("PASS reject before write: generation contract count drift")

        shutil.copyfile(GEN_CONTRACT, generation_contract_copy)
        failing_validator = tmp / "forced-validator-failure.py"
        failing_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(37)\n", encoding="utf-8")
        reconciler.VALIDATOR = failing_validator
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("post-reconcile eligibility validator failed" in str(exc), f"post-validation failure rejected at wrong boundary: {exc}")
        except Exception as exc:
            raise Fail(f"post-validation failure leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
        else:
            raise Fail("forced eligibility post-validation failure unexpectedly accepted")
        require(contract_copy.read_bytes() == original_contract, "post-validation failure left eligibility contract mutation")
        print("PASS rollback: eligibility contract restored byte-for-byte after post-validation failure")

    print("Environment generation eligibility reconcile negative suite PASS")
    print("reconciler helper substitution accepted: false")
    print("generation contract drift can mutate eligibility authority: false")
    print("failed post-validation leaves eligibility authority mutation behind: false")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION ELIGIBILITY RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
