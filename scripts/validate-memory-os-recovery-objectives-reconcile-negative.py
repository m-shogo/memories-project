#!/usr/bin/env python3
"""Prove recovery-objective reconciliation load boundaries and transactional rollback."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-recovery-objectives.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"
CONTRACT = ROOT / "contracts/operations/recovery-objectives-admission-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_reconciler():
    spec = importlib.util.spec_from_file_location("memory_os_recovery_objectives_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load recovery objective reconciler")
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
    require(RECONCILER.is_file(), "recovery objective reconciler missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    reconciler = load_reconciler()

    with tempfile.TemporaryDirectory(prefix=".tmp-recovery-objective-reconcile-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 objective authority", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("unreadable objective authority directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        with tempfile.TemporaryDirectory(prefix="memory-os-objective-outside-") as outside_dir:
            outside = Path(outside_dir) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            expect_domain_fail("objective authority escapes repository", lambda: reconciler.load(outside), reconciler.Fail)

        contract_copy = tmp / CONTRACT.name
        status_copy = tmp / STATUS.name
        shutil.copyfile(CONTRACT, contract_copy)
        shutil.copyfile(STATUS, status_copy)
        reconciler.CONTRACT = contract_copy
        reconciler.STATUS = status_copy
        original_contract = contract_copy.read_bytes()
        original_status = status_copy.read_bytes()

        passing_validator = tmp / "passing-objective-validator.py"
        passing_validator.write_text("#!/usr/bin/env python3\nraise SystemExit(0)\n", encoding="utf-8")
        failing_operability = tmp / "forced-operability-failure.py"
        failing_operability.write_text("#!/usr/bin/env python3\nraise SystemExit(37)\n", encoding="utf-8")
        reconciler.VALIDATOR = passing_validator
        reconciler.OPERABILITY_VALIDATOR = failing_operability

        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require("aggregate operability validator failed" in str(exc), f"unexpected reconcile failure: {exc}")
        else:
            raise Fail("forced aggregate operability failure unexpectedly accepted")

        require(contract_copy.read_bytes() == original_contract, "objective contract rollback drift")
        require(status_copy.read_bytes() == original_status, "objective operability status rollback drift")

    print("PASS rollback: aggregate operability rejection restores recovery objective contract/status byte-for-byte")
    print("Recovery objective reconcile negative suite PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RECOVERY OBJECTIVE RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
