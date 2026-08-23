#!/usr/bin/env python3
"""Prove restore-drill preflight authority loading and reconcile rollback fail closed."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-preflight.py"
CANONICAL_CONTRACT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
CANONICAL_STATUS = ROOT / "contracts/operations/production-operability-status.json"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
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


def expect_direct_authority_rejected(
    reconciler: object,
    name: str,
    field: str,
    attribute: str,
    replacement: Path,
    contract_before: bytes,
    status_before: bytes,
) -> None:
    original = getattr(reconciler, attribute)
    setattr(reconciler, attribute, replacement)
    try:
        try:
            reconciler.main()
        except reconciler.Fail as exc:
            require(f"{field} authority drift" in str(exc), f"{name} rejected at wrong boundary: {exc}")
        else:
            raise Fail(f"direct reconciler unexpectedly accepted: {name}")
        require(CANONICAL_CONTRACT.read_bytes() == contract_before, f"canonical contract mutated while rejecting {name}")
        require(CANONICAL_STATUS.read_bytes() == status_before, f"canonical status mutated while rejecting {name}")
    finally:
        setattr(reconciler, attribute, original)


def prove_data_and_executable_authority_rejection(reconciler: object) -> None:
    contract_before = CANONICAL_CONTRACT.read_bytes()
    status_before = CANONICAL_STATUS.read_bytes()
    cases = (
        (
            "preflight contract substitution",
            "preflight contract",
            "CONTRACT",
            reconciler.STATUS,
        ),
        (
            "environment generation registry substitution",
            "environment generation registry",
            "GEN_REGISTRY",
            reconciler.OBJECTIVES,
        ),
        (
            "recovery objectives registry substitution",
            "recovery objectives registry",
            "OBJECTIVES",
            reconciler.DRILL_REGISTRY,
        ),
        (
            "drill request registry substitution",
            "drill request registry",
            "DRILL_REGISTRY",
            reconciler.GEN_REGISTRY,
        ),
        (
            "preflight validator substitution",
            "preflight validator",
            "VALIDATOR_MODULE",
            reconciler.OPERABILITY_VALIDATOR,
        ),
        (
            "operability validator substitution",
            "operability validator",
            "OPERABILITY_VALIDATOR",
            reconciler.VALIDATOR_MODULE,
        ),
        (
            "production operability status substitution",
            "production operability status",
            "STATUS",
            reconciler.CONTRACT,
        ),
    )
    for name, field, attribute, replacement in cases:
        expect_direct_authority_rejected(
            reconciler,
            name,
            field,
            attribute,
            replacement,
            contract_before,
            status_before,
        )
    print(f"PASS boundary: direct preflight data/executable substitutions rejected: {len(cases)}")


def prove_transactional_rollback(reconciler: object, tmp: Path) -> None:
    contract = tmp / "preflight-contract.json"
    status = tmp / "production-operability-status.json"
    shutil.copyfile(CANONICAL_CONTRACT, contract)
    shutil.copyfile(CANONICAL_STATUS, status)
    before_contract = contract.read_bytes()
    before_status = status.read_bytes()

    original_contract = reconciler.CONTRACT
    original_status = reconciler.STATUS
    original_run = reconciler.subprocess.run
    original_enforcer = reconciler.enforce_runtime_authorities
    observed_commands: list[list[str]] = []

    expected_paths = [
        str(reconciler.load_validator_module().GEN_VALIDATOR),
        str(reconciler.load_validator_module().OBJECTIVE_VALIDATOR),
        str(reconciler.load_validator_module().DRILL_VALIDATOR),
        str(reconciler.VALIDATOR_MODULE),
        str(reconciler.OPERABILITY_VALIDATOR),
    ]

    def fail_only_aggregate_post_reconcile(*args, **kwargs):
        command = [str(item) for item in (args[0] if args else [])]
        observed_commands.append(command)
        call_index = len(observed_commands) - 1
        require(call_index < len(expected_paths), "unexpected extra preflight validator invocation")
        require(command[-1] == expected_paths[call_index], f"preflight validator order drift at call {call_index + 1}: {command}")
        if call_index < 4:
            return SimpleNamespace(returncode=0, stdout="upstream/preflight authority validator pass", stderr="")
        return SimpleNamespace(returncode=1, stdout="forced post-reconcile operability validator failure", stderr="")

    # Direct invocation is canonical-only. The negative suite bypasses only that
    # production identity guard around internal repo-contained fixture copies so
    # it can prove the write/validation rollback transaction independently.
    reconciler.enforce_runtime_authorities = lambda: None
    reconciler.CONTRACT = contract
    reconciler.STATUS = status
    reconciler.subprocess.run = fail_only_aggregate_post_reconcile
    try:
        expect_domain_fail("forced aggregate operability validation failure", reconciler.main, reconciler.Fail)
    finally:
        reconciler.enforce_runtime_authorities = original_enforcer
        reconciler.CONTRACT = original_contract
        reconciler.STATUS = original_status
        reconciler.subprocess.run = original_run

    require(len(observed_commands) == 5, "expected exact five-stage preflight validation chain")
    require(contract.read_bytes() == before_contract, "preflight contract was not rolled back byte-for-byte")
    require(status.read_bytes() == before_status, "production status was not rolled back byte-for-byte")
    print("PASS boundary: validator order is environment generation -> recovery objectives -> drill request -> preflight -> aggregate Operability")
    print("PASS boundary: preflight validator passed before aggregate operability rejection")
    print("PASS rollback: preflight contract restored byte-for-byte after aggregate rejection")
    print("PASS rollback: production status restored byte-for-byte after aggregate rejection")


def main() -> int:
    require(VALIDATOR.is_file(), "preflight validator missing")
    require(RECONCILER.is_file(), "preflight reconciler missing")
    require(CANONICAL_CONTRACT.is_file(), "preflight contract missing")
    require(CANONICAL_STATUS.is_file(), "production status missing")
    require(TMP_PARENT.is_dir(), "temporary fixture parent missing")
    validator = load_module(VALIDATOR, "memory_os_restore_drill_preflight_load_negative")
    reconciler = load_module(RECONCILER, "memory_os_restore_drill_preflight_reconcile_load_negative")

    prove_data_and_executable_authority_rejection(reconciler)

    with tempfile.TemporaryDirectory(prefix=".tmp-preflight-load-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)

        invalid_utf8 = tmp / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}")
        expect_domain_fail("invalid UTF-8 preflight authority JSON", lambda: validator.load(invalid_utf8), validator.Fail)
        expect_domain_fail("invalid UTF-8 preflight reconcile authority JSON", lambda: reconciler.load(invalid_utf8), reconciler.Fail)

        directory_authority = tmp / "directory-authority.json"
        directory_authority.mkdir()
        expect_domain_fail("preflight authority path is unreadable directory", lambda: validator.load(directory_authority), validator.Fail)
        expect_domain_fail("preflight reconcile authority path is unreadable directory", lambda: reconciler.load(directory_authority), reconciler.Fail)

        prove_transactional_rollback(reconciler, tmp)

    escaped = Path("/tmp/memory-os-preflight-reconcile-escaped.json")
    expect_domain_fail("preflight reconcile authority path escapes repository", lambda: reconciler.load(escaped), reconciler.Fail)

    print("Preflight unreadable-authority and reconcile rollback negative suite PASS")
    print("direct reconciler data/executable authority substitutions accepted: false")
    print("reconciler invalid UTF-8 authority leaked raw exception: false")
    print("reconciler unreadable directory authority leaked raw exception: false")
    print("reconciler escaped authority accepted: false")
    print("upstream append-only authorities validated before derived mutation: true")
    print("preflight and operability validators execute inside reconcile transaction: true")
    print("failed aggregate post-validation leaves derived authority mutation behind: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PREFLIGHT LOAD NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
