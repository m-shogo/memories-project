#!/usr/bin/env python3
"""Prove restore drill preflight reconciliation rolls back partial publication."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-backup-restore-drill-preflight.py"


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


def assert_authorities_restored(
    module,
    contract_before: bytes,
    status_before: bytes,
    contract_mode_before: int,
    status_mode_before: int,
    boundary: str,
) -> None:
    require(module.CONTRACT.read_bytes() == contract_before, f"preflight contract was not restored byte-for-byte after {boundary}")
    require(module.STATUS.read_bytes() == status_before, f"production status was not restored byte-for-byte after {boundary}")
    require(mode(module.CONTRACT) == contract_mode_before, f"preflight contract mode changed after {boundary}")
    require(mode(module.STATUS) == status_mode_before, f"production status mode changed after {boundary}")
    require(
        not list(module.CONTRACT.parent.glob(f".{module.CONTRACT.name}.*.tmp")),
        f"preflight contract left a temporary authority file after {boundary}",
    )
    require(
        not list(module.STATUS.parent.glob(f".{module.STATUS.name}.*.tmp")),
        f"production status left a temporary authority file after {boundary}",
    )


def prove_second_replace_rollback(module) -> None:
    contract_before = module.CONTRACT.read_bytes()
    status_before = module.STATUS.read_bytes()
    contract_mode_before = mode(module.CONTRACT)
    status_mode_before = mode(module.STATUS)
    real_replace = module.os.replace
    replace_calls = 0

    def fail_second_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("synthetic preflight second atomic replacement failure")
        real_replace(source, destination)

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

    require(replace_calls == 4, f"unexpected preflight replace/rollback call count: {replace_calls}")
    assert_authorities_restored(
        module,
        contract_before,
        status_before,
        contract_mode_before,
        status_mode_before,
        "partial publication rollback",
    )
    print("PASS rollback: preflight second replace failure restores contract/status bytes and modes")
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
                "rollback could not restore all canonical authorities" in str(exc)
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


def prove_post_validator_rollback(module) -> None:
    contract_before = module.CONTRACT.read_bytes()
    status_before = module.STATUS.read_bytes()
    contract_mode_before = mode(module.CONTRACT)
    status_mode_before = mode(module.STATUS)
    real_validator = module.run_post_reconcile_validator
    real_replace = module.os.replace
    validator_calls: list[str] = []
    publication_destinations: list[Path] = []

    def record_replace(source: str | Path, destination: str | Path) -> None:
        publication_destinations.append(Path(destination))
        real_replace(source, destination)

    def fail_after_preflight_validator(path: Path, label: str) -> None:
        validator_calls.append(label)
        if label == "preflight":
            real_validator(path, label)
            return
        require(label == "operability", f"unexpected post-reconcile validator label: {label}")
        raise module.Fail("synthetic post-publication operability validator failure")

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

    require(validator_calls == ["preflight", "operability"], f"unexpected post-reconcile validator sequence: {validator_calls}")
    require(len(publication_destinations) == 4, f"unexpected publish/rollback replacement count after validator failure: {len(publication_destinations)}")
    require(
        publication_destinations[:2] == [module.CONTRACT, module.STATUS],
        f"validators ran before both canonical authorities were published: {publication_destinations}",
    )
    require(
        publication_destinations[2:] == [module.CONTRACT, module.STATUS],
        f"post-validator rollback did not restore both canonical authorities: {publication_destinations}",
    )
    assert_authorities_restored(
        module,
        contract_before,
        status_before,
        contract_mode_before,
        status_mode_before,
        "post-publication validator rollback",
    )
    print("PASS rollback: failed aggregate validator restores both published authorities byte-for-byte with original modes")
    print("PASS boundary: preflight validator succeeds before synthetic aggregate failure; rollback leaves no temporary files")


def main() -> int:
    require(RECONCILER.is_file(), "restore drill preflight reconciler missing")
    module = load_module()
    module.enforce_execution_identity()
    module.enforce_runtime_authorities()
    prove_second_replace_rollback(module)
    prove_rollback_attempts_all_authorities(module)
    prove_post_validator_rollback(module)
    print("Restore drill preflight reconcile negative suite PASS")
    print("partial preflight/status publication accepted: false")
    print("rollback skips later authority after earlier restore failure: false")
    print("failed post-publication validation retained authority mutation: false")
    print("production evidence created: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL PREFLIGHT RECONCILE NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
