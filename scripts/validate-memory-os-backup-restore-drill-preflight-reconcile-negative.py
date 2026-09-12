#!/usr/bin/env python3
"""Prove restore drill preflight reconciliation rolls back partial publication."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-preflight.py"
TMP_PARENT = ROOT / "docs/fixtures/memory-os-operability"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_backup_restore_drill_preflight_reconcile_negative",
        RECONCILER,
    )
    require(spec is not None and spec.loader is not None, "cannot load restore drill preflight reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture_authorities(module, tmp: Path, label: str) -> tuple[Path, Path]:
    contract = tmp / f"{label}-{module.CONTRACT.name}"
    status = tmp / f"{label}-{module.STATUS.name}"
    shutil.copy2(module.CONTRACT, contract)
    shutil.copy2(module.STATUS, status)
    return contract, status


def assert_authorities_restored(
    contract: Path,
    status: Path,
    contract_before: bytes,
    status_before: bytes,
    contract_mode_before: int,
    status_mode_before: int,
    boundary: str,
) -> None:
    require(contract.read_bytes() == contract_before, f"preflight contract was not restored byte-for-byte after {boundary}")
    require(status.read_bytes() == status_before, f"production status was not restored byte-for-byte after {boundary}")
    require(mode(contract) == contract_mode_before, f"preflight contract mode changed after {boundary}")
    require(mode(status) == status_mode_before, f"production status mode changed after {boundary}")
    require(
        not list(contract.parent.glob(f".{contract.name}.*.tmp")),
        f"preflight contract left a temporary authority file after {boundary}",
    )
    require(
        not list(status.parent.glob(f".{status.name}.*.tmp")),
        f"production status left a temporary authority file after {boundary}",
    )


def prove_second_replace_rollback(module, tmp: Path) -> None:
    contract, status = fixture_authorities(module, tmp, "second-replace")
    contract_before = contract.read_bytes()
    status_before = status.read_bytes()
    contract_mode_before = mode(contract)
    status_mode_before = mode(status)
    original_contract = module.CONTRACT
    original_status = module.STATUS
    real_replace = module.os.replace
    replace_calls = 0

    def fail_second_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("synthetic preflight second atomic replacement failure")
        real_replace(source, destination)

    module.CONTRACT = contract
    module.STATUS = status
    module.os.replace = fail_second_replace
    try:
        try:
            module._reconcile()
        except module.Fail as exc:
            require(
                "cannot atomically write" in str(exc),
                f"preflight second replace rejected at wrong boundary: {exc}",
            )
        else:
            raise Fail("preflight second atomic replacement failure unexpectedly accepted")
    finally:
        module.os.replace = real_replace
        module.CONTRACT = original_contract
        module.STATUS = original_status

    require(replace_calls == 4, f"unexpected preflight replace/rollback call count: {replace_calls}")
    assert_authorities_restored(
        contract,
        status,
        contract_before,
        status_before,
        contract_mode_before,
        status_mode_before,
        "partial publication rollback",
    )
    print("PASS rollback: preflight second replace failure restores fixture contract/status bytes and modes")
    print("PASS boundary: preflight second replace failure leaves no temporary authority files")


def prove_rollback_attempts_all_authorities(module) -> None:
    real_write_text = module.write_text
    real_repo_relative = module.repo_relative
    first = Path("/synthetic/preflight-contract.json")
    second = Path("/synthetic/production-status.json")
    attempts: list[Path] = []

    def fail_first_restore(path: Path, _text: str) -> None:
        attempts.append(path)
        if path == first:
            raise module.Fail("synthetic first preflight rollback restore rejection")

    module.write_text = fail_first_restore
    module.repo_relative = lambda path: Path(path.name)
    try:
        try:
            module.restore_authorities(
                ((first, "contract-original"), (second, "status-original")),
                module.Fail("synthetic forward preflight rejection"),
            )
        except module.Fail as exc:
            require(
                "rollback incomplete" in str(exc)
                and "preflight-contract.json" in str(exc),
                f"preflight rollback aggregation rejected at wrong boundary: {exc}",
            )
        else:
            raise Fail("synthetic first preflight rollback restore failure unexpectedly accepted")
        require(attempts == [first, second], f"preflight rollback did not attempt every authority: {attempts}")
    finally:
        module.write_text = real_write_text
        module.repo_relative = real_repo_relative
    print("PASS rollback: failure restoring first preflight authority does not skip later authority restore attempts")


def prove_post_validator_rollback(module, tmp: Path) -> None:
    contract, status = fixture_authorities(module, tmp, "post-validator")
    contract_before = contract.read_bytes()
    status_before = status.read_bytes()
    contract_mode_before = mode(contract)
    status_mode_before = mode(status)
    original_contract = module.CONTRACT
    original_status = module.STATUS
    real_validator = module.run_post_reconcile_validator
    real_replace = module.os.replace
    validator_calls: list[str] = []
    publication_destinations: list[Path] = []

    def record_replace(source: str | Path, destination: str | Path) -> None:
        publication_destinations.append(Path(destination))
        real_replace(source, destination)

    def fail_after_preflight_validator(_path: Path, label: str) -> None:
        validator_calls.append(label)
        if label == "preflight":
            return
        require(label == "operability", f"unexpected post-reconcile validator label: {label}")
        raise module.Fail("synthetic post-publication operability validator failure")

    module.CONTRACT = contract
    module.STATUS = status
    module.os.replace = record_replace
    module.run_post_reconcile_validator = fail_after_preflight_validator
    try:
        try:
            module._reconcile()
        except module.Fail as exc:
            require(
                "synthetic post-publication operability validator failure" in str(exc),
                f"post-publication validator failure rejected at wrong boundary: {exc}",
            )
        else:
            raise Fail("post-publication validator failure unexpectedly accepted")
    finally:
        module.run_post_reconcile_validator = real_validator
        module.os.replace = real_replace
        module.CONTRACT = original_contract
        module.STATUS = original_status

    require(validator_calls == ["preflight", "operability"], f"unexpected post-reconcile validator sequence: {validator_calls}")
    require(len(publication_destinations) == 4, f"unexpected publish/rollback replacement count after validator failure: {len(publication_destinations)}")
    require(
        publication_destinations[:2] == [contract, status],
        f"validators ran before both fixture authorities were published: {publication_destinations}",
    )
    require(
        publication_destinations[2:] == [contract, status],
        f"post-validator rollback did not restore both fixture authorities: {publication_destinations}",
    )
    assert_authorities_restored(
        contract,
        status,
        contract_before,
        status_before,
        contract_mode_before,
        status_mode_before,
        "post-publication validator rollback",
    )
    print("PASS rollback: failed aggregate validator restores both fixture authorities byte-for-byte with original modes")
    print("PASS boundary: synthetic post-validation rollback leaves canonical authorities untouched")


def main() -> int:
    require(RECONCILER.is_file(), "restore drill preflight reconciler missing")
    require(TMP_PARENT.is_dir(), "preflight negative fixture parent missing")
    module = load_module()
    module.enforce_execution_identity()
    module.enforce_runtime_authorities()
    canonical_before = {
        module.CONTRACT: module.CONTRACT.read_bytes(),
        module.STATUS: module.STATUS.read_bytes(),
    }
    with tempfile.TemporaryDirectory(prefix=".tmp-preflight-reconcile-negative-", dir=TMP_PARENT) as tmpdir:
        tmp = Path(tmpdir)
        prove_second_replace_rollback(module, tmp)
        prove_rollback_attempts_all_authorities(module)
        prove_post_validator_rollback(module, tmp)
    for path, payload in canonical_before.items():
        require(path.read_bytes() == payload, f"canonical authority mutated by rollback negative: {path.name}")
    print("Restore drill preflight reconcile negative suite PASS")
    print("partial preflight/status publication accepted: false")
    print("rollback skips later authority after earlier restore failure: false")
    print("failed post-publication validation retained authority mutation: false")
    print("canonical preflight/status mutation during negative proof: false")
    print("production evidence created: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL PREFLIGHT RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
