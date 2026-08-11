#!/usr/bin/env python3
"""Prove environment-generation reconciliation load boundaries and transactional rollback."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-production-equivalent-generation-status.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-generation-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load environment generation reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_domain_fail(name: str, action: Callable[[], object], fail_type: type[BaseException]) -> None:
    try:
        action()
    except fail_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    require(RECONCILER.is_file(), "environment generation reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    with tempfile.TemporaryDirectory(prefix=".tmp-environment-generation-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 generation authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("unreadable generation authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-environment-generation-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("generation authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

        absolute_ref = str((ROOT / "README.md").resolve())
        expect_domain_fail("absolute current environment ref", lambda: reconciler.canonical_repo_ref(absolute_ref, "invalid ref"), reconciler.Fail)
        expect_domain_fail("parent traversal current environment ref", lambda: reconciler.canonical_repo_ref("scripts/../README.md", "invalid ref"), reconciler.Fail)

        contract_copy = tmp / CONTRACT.name
        status_copy = tmp / STATUS.name
        shutil.copyfile(CONTRACT, contract_copy)
        shutil.copyfile(STATUS, status_copy)
        reconciler.CONTRACT = contract_copy
        reconciler.STATUS = status_copy
        original_contract = contract_copy.read_bytes()
        original_status = status_copy.read_bytes()

        failing_validator = tmp / "forced-validator-failure.py"
        failing_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(31)\n", encoding="utf-8")
        reconciler.VALIDATOR = failing_validator

        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("generation validator failed" in str(exc), f"unexpected reconcile failure: {exc}")
        else:
            raise Fail("forced generation post-validation failure unexpectedly accepted")

        require(contract_copy.read_bytes() == original_contract, "generation contract rollback drift")
        require(status_copy.read_bytes() == original_status, "operability status rollback drift")

    print("PASS rollback: environment generation contract/status restored byte-for-byte")
    print("Environment generation reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
