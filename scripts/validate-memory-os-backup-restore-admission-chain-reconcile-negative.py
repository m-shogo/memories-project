#!/usr/bin/env python3
"""Prove admission-chain reconciliation load boundaries and contract rollback."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-admission-chain.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/backup-restore-admission-chain-contract.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_admission_chain_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load admission-chain reconciler")
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
    require(RECONCILER.is_file(), "admission-chain reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    with tempfile.TemporaryDirectory(prefix=".tmp-admission-chain-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("admission-chain invalid UTF-8 authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("admission-chain unreadable authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-chain-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("admission-chain authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

        contract_copy = tmp / CONTRACT.name
        shutil.copyfile(CONTRACT, contract_copy)
        reconciler.CONTRACT = contract_copy
        original_contract = contract_copy.read_bytes()

        failing_validator = tmp / "forced-validator-failure.py"
        failing_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(41)\n", encoding="utf-8")
        reconciler.VALIDATOR = failing_validator

        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("post-reconcile admission-chain validator failed" in str(exc), f"unexpected reconcile failure: {exc}")
        else:
            raise Fail("forced admission-chain post-validation failure unexpectedly accepted")

        require(contract_copy.read_bytes() == original_contract, "admission-chain contract rollback drift")

    print("PASS rollback: admission-chain contract restored byte-for-byte")
    print("Admission-chain reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ADMISSION CHAIN RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
