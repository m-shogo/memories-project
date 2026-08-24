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
    fail_validator = tmp_path / "ledger-fail.py"
    fail_validator.write_text("raise SystemExit(1)\n", encoding="utf-8")
    creator.VALIDATOR = fail_validator

    rejected = False
    try:
        creator.validate_canonical_ledger_before_append(creator.DEFAULT_LEDGER)
    except creator.EvidenceValidationError as exc:
        require("failed validation before append" in str(exc),
                f"unexpected canonical ledger rejection: {exc}")
        rejected = True
    require(rejected, "canonical append did not require current ledger validation")

    custom_ledger = tmp_path / "isolated-ledger"
    creator.validate_canonical_ledger_before_append(custom_ledger)


def prove_postappend_failure_removes_new_record(tmp_path: Path) -> None:
    creator = load_module(CREATOR, "migration_operation_creator_postappend_negative")
    ledger = tmp_path / "canonical-ledger"
    counter = tmp_path / "validator-count.txt"
    validator = tmp_path / "ledger-pass-then-fail.py"
    validator.write_text(
        "from pathlib import Path\n"
        f"counter = Path({str(counter)!r})\n"
        "count = int(counter.read_text() or '0') if counter.exists() else 0\n"
        "counter.write_text(str(count + 1))\n"
        "raise SystemExit(0 if count == 0 else 1)\n",
        encoding="utf-8",
    )
    creator.DEFAULT_LEDGER = ledger
    creator.VALIDATOR = validator

    record_path = tmp_path / "record.json"
    record = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    record["migrationRunId"] = "mgr_postappend_rollback_negative"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    target = ledger / creator.expected_filename(record)

    argv = sys.argv
    sys.argv = [str(CREATOR), str(record_path), "--ledger-dir", str(ledger)]
    try:
        rejected = False
        try:
            creator.main()
        except creator.EvidenceValidationError as exc:
            require("failed validation after append" in str(exc),
                    f"unexpected post-append rejection: {exc}")
            rejected = True
        require(rejected, "post-append canonical validation failure was not rejected")
    finally:
        sys.argv = argv

    require(not target.exists(),
            "new migration operation evidence remained after post-append validation failure")
    require(counter.read_text(encoding="utf-8") == "2",
            "controlled validator did not run once before and once after append")


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

    with tempfile.TemporaryDirectory(prefix="migration-operation-reconcile-negative-") as tmp:
        tmp_path = Path(tmp)
        prove_canonical_ledger_preappend_guard(tmp_path)
        prove_postappend_failure_removes_new_record(tmp_path)

    prove_atomic_replace_failure_rolls_back(module, originals)
    prove_post_write_failure_rolls_back(module, originals)
    print("PASS: migration operation append and reconcile are fail-closed, atomic, and rollback-safe")
    print("migration operation validator-chain substitution accepted: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
