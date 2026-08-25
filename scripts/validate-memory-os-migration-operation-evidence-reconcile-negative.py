#!/usr/bin/env python3
"""Prove migration operation authority rollback and monotonic composition."""

from __future__ import annotations

import importlib.util
import json
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


def prove_atomic_replace_failure_rolls_back(module, originals: dict[Path, bytes]) -> None:
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
        leftovers = list(path.parent.glob(f".{path.name}.*.tmp"))
        require(not leftovers, f"temporary migration operation authority remained after replace failure: {leftovers}")


def prove_post_write_failure_rolls_back(module, originals: dict[Path, bytes]) -> None:
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


def main() -> int:
    originals = {
        CONTRACT: CONTRACT.read_bytes(),
        LIFECYCLE: LIFECYCLE.read_bytes(),
        STATUS: STATUS.read_bytes(),
    }
    module = load_module(RECONCILER, "migration_operation_reconciler")
    prove_stronger_authority_is_preserved(module, originals[LIFECYCLE])
    prove_contract_guards_are_required(originals[CONTRACT])
    prove_validator_chain_substitution_rejected(module, originals)
    prove_actual_cli_authority_substitution_rejected()

    with tempfile.TemporaryDirectory(prefix="migration-operation-reconcile-negative-") as tmp:
        tmp_path = Path(tmp)
        prove_canonical_ledger_preappend_guard(tmp_path)
        prove_postappend_failure_removes_new_record(tmp_path)

    prove_atomic_replace_failure_rolls_back(module, originals)
    prove_post_write_failure_rolls_back(module, originals)
    print("PASS: migration operation append and reconcile are fail-closed, atomic, and rollback-safe")
    print("migration operation validator-chain substitution accepted: false")
    print("migration operation actual CLI authority substitution accepted: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
