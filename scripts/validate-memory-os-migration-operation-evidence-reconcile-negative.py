#!/usr/bin/env python3
"""Prove migration operation authority rollback and monotonic composition."""

from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATOR = ROOT / "scripts/create-memory-os-migration-operation-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-migration-operation-evidence.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-operation-evidence.py"
CONTRACT = ROOT / "contracts/operations/migration-operation-evidence-contract.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
TEMPLATE = ROOT / "docs/fixtures/memory-os-operability/migration-operation-record.template.v1.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(call, error_type, expected: str) -> None:
    rejected = False
    try:
        call()
    except error_type as exc:
        require(expected in str(exc), f"unexpected authority rejection: {exc}")
        rejected = True
    require(rejected, f"expected rejection containing: {expected}")


def prove_stronger_authority_is_preserved(module, lifecycle_payload: bytes) -> None:
    lifecycle = json.loads(lifecycle_payload.decode("utf-8"))
    readiness = lifecycle["readiness"]
    for field in module.STRONGER_LIFECYCLE_FIELDS:
        readiness[field] = True
    normalized = module.normalize_lifecycle(lifecycle)
    normalized_readiness = normalized["readiness"]
    for field in module.STRONGER_LIFECYCLE_FIELDS:
        require(normalized_readiness.get(field) is True,
                f"weaker operation evidence rolled back stronger lifecycle authority: {field}")


def prove_canonical_ledger_preappend_guard(tmp_path: Path) -> None:
    creator = load_module(CREATOR, "migration_operation_creator_negative")

    def fail_runner() -> None:
        raise creator.EvidenceValidationError(
            "canonical migration operation ledger failed validation: synthetic failure"
        )

    expect_rejection(
        lambda: creator.validate_canonical_ledger_before_append(
            creator.DEFAULT_LEDGER,
            _canonical_runner=fail_runner,
        ),
        creator.EvidenceValidationError,
        "failed validation before append",
    )

    custom_ledger = tmp_path / "isolated-ledger"
    creator.validate_canonical_ledger_before_append(
        custom_ledger,
        _canonical_runner=fail_runner,
    )


def prove_postappend_failure_removes_new_record(tmp_path: Path) -> None:
    creator = load_module(CREATOR, "migration_operation_creator_postappend_negative")
    ledger = tmp_path / "isolated-ledger"
    record_path = tmp_path / "record.json"
    record = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    record["migrationRunId"] = "mgr_postappend_rollback_negative"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    target = ledger / creator.expected_filename(record)

    def accept_before(_: Path) -> None:
        return None

    def fail_after_append(_: Path) -> None:
        raise creator.EvidenceValidationError(
            "canonical migration operation ledger failed validation after append: synthetic failure"
        )

    expect_rejection(
        lambda: creator.append_record(
            record_path,
            ledger,
            before_validator=accept_before,
            after_validator=fail_after_append,
        ),
        creator.EvidenceValidationError,
        "failed validation after append",
    )
    require(not target.exists(),
            "new migration operation evidence remained after post-append validation failure")


def prove_postappend_rollback_failure_preserves_diagnostics(tmp_path: Path) -> None:
    creator = load_module(CREATOR, "migration_operation_creator_rollback_diagnostic_negative")
    ledger = tmp_path / "rollback-failure-ledger"
    record_path = tmp_path / "rollback-failure-record.json"
    record = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    record["migrationRunId"] = "mgr_postappend_rollback_failure_negative"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    target = ledger / creator.expected_filename(record)

    def accept_before(_: Path) -> None:
        return None

    def fail_after_append(_: Path) -> None:
        raise creator.EvidenceValidationError("synthetic migration operation post-append rejection")

    original_unlink = creator.Path.unlink

    def fail_target_unlink(self: Path, *args, **kwargs):
        if self == target:
            raise OSError("synthetic migration operation append rollback rejection")
        return original_unlink(self, *args, **kwargs)

    creator.Path.unlink = fail_target_unlink
    try:
        rejected = False
        try:
            creator.append_record(
                record_path,
                ledger,
                before_validator=accept_before,
                after_validator=fail_after_append,
            )
        except creator.EvidenceValidationError as exc:
            text = str(exc)
            require("synthetic migration operation post-append rejection" in text,
                    f"primary post-append rejection was lost: {exc}")
            require("rollback incomplete" in text,
                    f"append rollback incompleteness was not reported: {exc}")
            require("synthetic migration operation append rollback rejection" in text,
                    f"append rollback failure was lost: {exc}")
            rejected = True
        require(rejected, "migration operation append accepted validator plus rollback failure")
        require(target.exists(), "append rollback failure fixture did not preserve failed target")
    finally:
        creator.Path.unlink = original_unlink
        target.unlink(missing_ok=True)


def prove_actual_cli_authority_substitution_rejected() -> None:
    creator = load_module(CREATOR, "migration_operation_creator_cli_authority_negative")
    canonical_root = creator.ROOT
    canonical_ledger = creator.DEFAULT_LEDGER
    canonical_validator = creator.VALIDATOR

    mutations = (
        ("ROOT", ROOT / "docs", "repository authority substitution rejected"),
        ("CANONICAL_DEFAULT_LEDGER", ROOT / "docs/evidence", "canonical ledger authority substitution rejected"),
        ("CANONICAL_VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py", "canonical validator authority substitution rejected"),
        ("DEFAULT_LEDGER", ROOT / "docs/evidence", "default ledger authority substitution rejected"),
        ("VALIDATOR", ROOT / "scripts/validate-memory-os-operability.py", "validator authority substitution rejected"),
        ("load_json", lambda path: {}, "JSON loader authority substitution rejected"),
        ("validate_record", lambda record: None, "record validator authority substitution rejected"),
        ("expected_filename", lambda record: "fake.json", "filename authority substitution rejected"),
    )
    for field, replacement, expected in mutations:
        original = getattr(creator, field)
        setattr(creator, field, replacement)
        try:
            expect_rejection(
                creator.require_actual_cli_authorities,
                creator.EvidenceValidationError,
                expected,
            )
        finally:
            setattr(creator, field, original)

    original_run = creator.subprocess.run
    creator.subprocess.run = lambda *args, **kwargs: None
    try:
        expect_rejection(
            creator.require_actual_cli_authorities,
            creator.EvidenceValidationError,
            "subprocess transport substitution rejected",
        )
    finally:
        creator.subprocess.run = original_run

    main_mutations = (
        ("require_actual_cli_authorities", lambda: None, "CLI guard authority substitution rejected"),
        ("append_record", lambda *args, **kwargs: None, "CLI append authority substitution rejected"),
        ("validate_canonical_ledger_before_append", lambda ledger: None, "pre-append validator authority substitution rejected"),
        ("validate_canonical_ledger_after_append", lambda ledger: None, "post-append validator authority substitution rejected"),
        ("run_canonical_validator", lambda: None, "canonical runner authority substitution rejected"),
    )
    for field, replacement, expected in main_mutations:
        original = getattr(creator, field)
        setattr(creator, field, replacement)
        argv = sys.argv
        sys.argv = [str(CREATOR)]
        try:
            expect_rejection(creator.main, creator.EvidenceValidationError, expected)
        finally:
            sys.argv = argv
            setattr(creator, field, original)

    require(creator.ROOT == canonical_root, "migration operation ROOT authority was not restored")
    require(creator.DEFAULT_LEDGER == canonical_ledger, "migration operation ledger authority was not restored")
    require(creator.VALIDATOR == canonical_validator, "migration operation validator authority was not restored")


def prove_contract_guards_are_required(contract_payload: bytes) -> None:
    for guard, message in (
        ("canonicalLedgerMustValidateBeforeAppend", "canonical pre-append guard"),
        ("canonicalLedgerMustValidateAfterAppend", "canonical post-append guard"),
        ("postAppendValidationFailureMustRemoveNewRecord", "post-append rollback guard"),
    ):
        candidate = json.loads(contract_payload.decode("utf-8"))
        candidate["appendOnlyGuards"][guard] = False
        CONTRACT.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, str(VALIDATOR)],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            require(completed.returncode != 0,
                    f"standalone validator accepted disabled {message}")
        finally:
            CONTRACT.write_bytes(contract_payload)


def prove_validator_chain_substitution_rejected(module, originals: dict[Path, bytes]) -> None:
    original_chain = module.POST_WRITE_VALIDATORS
    module.POST_WRITE_VALIDATORS = ()
    argv = sys.argv
    sys.argv = [str(RECONCILER), "--check"]
    try:
        rejected = False
        try:
            module.main()
        except module.ReconcileFailure as exc:
            require("validator chain authority drift" in str(exc),
                    f"unexpected validator-chain rejection: {exc}")
            rejected = True
        require(rejected, "migration operation validator chain substitution was accepted")
    finally:
        sys.argv = argv
        module.POST_WRITE_VALIDATORS = original_chain

    for path, payload in originals.items():
        require(path.read_bytes() == payload,
                f"{path.name} changed after rejected validator-chain substitution")


def prove_atomic_replace_preserves_mode(module) -> None:
    with tempfile.TemporaryDirectory(prefix="migration-operation-mode-negative-") as temp_dir:
        fixture = Path(temp_dir) / "authority.json"
        fixture.write_bytes(b"before\n")
        fixture.chmod(0o640)
        module.atomic_replace_bytes(fixture, b"after\n")
        require(fixture.read_bytes() == b"after\n",
                "migration operation atomic replacement did not publish fixture payload")
        require(stat.S_IMODE(fixture.stat().st_mode) == 0o640,
                "migration operation atomic replacement changed existing authority mode")


def prove_atomic_replace_failure_rolls_back(
    module,
    originals: dict[Path, bytes],
    original_modes: dict[Path, int],
) -> None:
    candidates = [json.loads(payload.decode("utf-8")) for payload in originals.values()]
    for candidate in candidates:
        candidate["atomicRollbackProbe"] = "must-not-persist"

    original_replace = module.os.replace
    calls = 0

    def fail_second_replace(source, destination) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic atomic replace failure")
        original_replace(source, destination)

    module.os.replace = fail_second_replace
    try:
        rejected = False
        try:
            module.commit_validated_triple(*candidates)
        except OSError as exc:
            require("synthetic atomic replace failure" in str(exc), f"unexpected atomic replacement rejection: {exc}")
            rejected = True
        require(rejected, "migration operation authority accepted synthetic atomic replace failure")
    finally:
        module.os.replace = original_replace

    require(calls >= 5, "migration operation rollback did not atomically restore all canonical authorities")
    for path, payload in originals.items():
        require(path.read_bytes() == payload,
                f"{path.name} changed after synthetic atomic replace failure")
        require(stat.S_IMODE(path.stat().st_mode) == original_modes[path],
                f"{path.name} mode changed after synthetic atomic replace failure")
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, f"temporary migration operation authority remained after replace failure: {leftovers}")


def prove_post_write_failure_rolls_back(
    module,
    originals: dict[Path, bytes],
    original_modes: dict[Path, int],
) -> None:
    candidates = [json.loads(payload.decode("utf-8")) for payload in originals.values()]
    for candidate in candidates:
        candidate["rollbackProbe"] = "must-not-persist"

    original_run_validator = module.run_validator
    calls: list[Path] = []

    def controlled_run_validator(path: Path, *, phase: str) -> None:
        calls.append(path)
        if len(calls) == 3:
            raise module.ReconcileFailure(
                f"{phase} migration operation authority failed validation: {path.name}"
            )

    module.run_validator = controlled_run_validator
    try:
        rejected = False
        try:
            module.commit_validated_triple(*candidates)
        except module.ReconcileFailure as exc:
            require("failed validation" in str(exc), f"unexpected rejection: {exc}")
            rejected = True
        require(rejected, "post-write validation failure was not rejected")
    finally:
        module.run_validator = original_run_validator

    require(calls == list(module.EXPECTED_POST_WRITE_VALIDATORS),
            "controlled post-write validator order drifted")
    for path, payload in originals.items():
        require(path.read_bytes() == payload,
                f"{path.name} changed after rejected migration operation reconcile")
        require(stat.S_IMODE(path.stat().st_mode) == original_modes[path],
                f"{path.name} mode changed after rejected migration operation reconcile")


def prove_rollback_failure_is_exhaustive_and_preserves_diagnostics(
    module,
    originals: dict[Path, bytes],
    original_modes: dict[Path, int],
) -> None:
    candidates = [json.loads(payload.decode("utf-8")) for payload in originals.values()]
    for candidate in candidates:
        candidate["rollbackDiagnosticProbe"] = "must-not-persist"

    original_run_validator = module.run_validator
    real_atomic_replace = module.atomic_replace_bytes
    post_write_failure_seen = False
    rollback_attempts: list[Path] = []
    rollback_failure_injected = False

    def fail_post_write_validator(path: Path, *, phase: str) -> None:
        nonlocal post_write_failure_seen
        post_write_failure_seen = True
        raise module.ReconcileFailure("synthetic migration operation post-write validator rejection")

    def fail_first_restore_after_restoring(path: Path, payload: bytes) -> None:
        nonlocal rollback_failure_injected
        if post_write_failure_seen and path in originals and payload == originals[path]:
            rollback_attempts.append(path)
            real_atomic_replace(path, payload)
            if not rollback_failure_injected:
                rollback_failure_injected = True
                raise OSError("synthetic migration operation rollback restore rejection")
            return
        real_atomic_replace(path, payload)

    module.run_validator = fail_post_write_validator
    module.atomic_replace_bytes = fail_first_restore_after_restoring
    try:
        rejected = False
        try:
            module.commit_validated_triple(*candidates)
        except module.ReconcileFailure as exc:
            text = str(exc)
            require("synthetic migration operation post-write validator rejection" in text,
                    f"primary migration operation failure was lost: {exc}")
            require("rollback incomplete" in text,
                    f"migration operation rollback incompleteness was not reported: {exc}")
            require("synthetic migration operation rollback restore rejection" in text,
                    f"migration operation rollback failure was lost: {exc}")
            rejected = True
        require(rejected, "migration operation reconciler accepted validator plus rollback failure")
    finally:
        module.run_validator = original_run_validator
        module.atomic_replace_bytes = real_atomic_replace

    require(rollback_failure_injected, "migration operation rollback failure injection did not execute")
    require(rollback_attempts == list(originals),
            "migration operation rollback stopped before attempting every canonical authority")
    for path, payload in originals.items():
        require(path.read_bytes() == payload,
                f"{path.name} changed after rollback failure diagnostic case")
        require(stat.S_IMODE(path.stat().st_mode) == original_modes[path],
                f"{path.name} mode changed after rollback failure diagnostic case")


def main() -> int:
    originals = {
        CONTRACT: CONTRACT.read_bytes(),
        LIFECYCLE: LIFECYCLE.read_bytes(),
        STATUS: STATUS.read_bytes(),
    }
    original_modes = {path: stat.S_IMODE(path.stat().st_mode) for path in originals}
    module = load_module(RECONCILER, "migration_operation_reconciler")
    prove_stronger_authority_is_preserved(module, originals[LIFECYCLE])
    prove_contract_guards_are_required(originals[CONTRACT])
    prove_validator_chain_substitution_rejected(module, originals)
    prove_actual_cli_authority_substitution_rejected()

    with tempfile.TemporaryDirectory(prefix="migration-operation-reconcile-negative-") as tmp:
        tmp_path = Path(tmp)
        prove_canonical_ledger_preappend_guard(tmp_path)
        prove_postappend_failure_removes_new_record(tmp_path)
        prove_postappend_rollback_failure_preserves_diagnostics(tmp_path)

    prove_atomic_replace_preserves_mode(module)
    prove_atomic_replace_failure_rolls_back(module, originals, original_modes)
    prove_post_write_failure_rolls_back(module, originals, original_modes)
    prove_rollback_failure_is_exhaustive_and_preserves_diagnostics(module, originals, original_modes)
    print("PASS: migration operation append and reconcile are fail-closed, atomic, mode-preserving, and rollback-safe")
    print("migration operation append rollback diagnostics: enforced")
    print("migration operation rollback exhaustiveness: enforced")
    print("migration operation primary plus rollback diagnostics: enforced")
    print("migration operation validator-chain substitution accepted: false")
    print("migration operation actual CLI authority substitution accepted: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
