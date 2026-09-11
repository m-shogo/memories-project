#!/usr/bin/env python3
"""Prove rate-limit operation-ledger reconcile authority and rollback boundaries fail closed."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-operation-evidence.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_rate_limit_operation_evidence_reconcile_negative", RECONCILER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load rate-limit operation evidence reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def expect_authority_identity(reconciler) -> None:
    reconciler.enforce_runtime_authorities()
    original_operations = reconciler.OPERATIONS_PATH.read_bytes()
    original_status = reconciler.STATUS_PATH.read_bytes()
    substitutions = (
        ("EVIDENCE_PATH", reconciler.OPERATIONS_PATH, "operation evidence contract"),
        ("OPERATIONS_PATH", reconciler.EVIDENCE_PATH, "operations contract"),
        ("STATUS_PATH", reconciler.OPERATIONS_PATH, "production operability status"),
        ("WRITER_PATH", reconciler.EVIDENCE_VALIDATOR, "operation writer"),
        ("EVIDENCE_VALIDATOR", reconciler.OPERATIONS_VALIDATOR, "operation evidence validator"),
        ("OPERATIONS_VALIDATOR", reconciler.RATE_LIMIT_VALIDATOR, "operations validator"),
        ("RATE_LIMIT_VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "rate-limit validator"),
        ("OPERABILITY_VALIDATOR", reconciler.ENTRY_DOCS_VALIDATOR, "operability validator"),
        ("ENTRY_DOCS_VALIDATOR", reconciler.OPERABILITY_VALIDATOR, "entry docs validator"),
        (
            "WORKFLOW_PATH",
            ROOT / ".github/workflows/reconcile-rate-limit-operations.yml",
            "operation workflow",
        ),
    )
    for attribute, substitute, label in substitutions:
        original = getattr(reconciler, attribute)
        try:
            setattr(reconciler, attribute, substitute)
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.ReconcileFailure as exc:
                message = str(exc)
                if "authority drift" not in message and "missing or escapes repository" not in message:
                    raise RuntimeError(f"{label} rejected for unrelated reason: {message}") from exc
            else:
                raise RuntimeError(f"reconciler accepted authority substitution: {label}")
        finally:
            setattr(reconciler, attribute, original)
    if reconciler.OPERATIONS_PATH.read_bytes() != original_operations:
        raise RuntimeError("operations contract changed after authority substitution rejection")
    if reconciler.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("production status changed after authority substitution rejection")
    reconciler.enforce_runtime_authorities()


def expect_execution_rejection(reconciler, attribute: str, substitute, expected: str) -> None:
    original = getattr(reconciler, attribute)
    operations_before = reconciler.OPERATIONS_PATH.read_bytes()
    status_before = reconciler.STATUS_PATH.read_bytes()
    setattr(reconciler, attribute, substitute)
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            if expected not in str(exc):
                raise RuntimeError(f"{attribute} rejected for unrelated reason: {exc}") from exc
        else:
            raise RuntimeError(f"reconciler accepted execution substitution: {attribute}")
        if reconciler.OPERATIONS_PATH.read_bytes() != operations_before:
            raise RuntimeError(f"operations contract changed after execution substitution: {attribute}")
        if reconciler.STATUS_PATH.read_bytes() != status_before:
            raise RuntimeError(f"production status changed after execution substitution: {attribute}")
    finally:
        setattr(reconciler, attribute, original)


def prove_execution_authority_identity(reconciler) -> None:
    cases = (
        ("require", lambda *_args, **_kwargs: None, "require execution authority drift"),
        ("require_exact_repo_file", lambda path, *_args: path, "path checker execution authority drift"),
        ("enforce_runtime_authorities", lambda: None, "runtime guard execution authority drift"),
        ("load", lambda _path: {}, "loader execution authority drift"),
        ("load_writer", lambda: object(), "writer loader execution authority drift"),
        ("append_once", lambda *_args: False, "append helper execution authority drift"),
        ("run_validator", lambda *_args: None, "validator runner execution authority drift"),
        ("atomic_write_bytes", lambda *_args: None, "atomic byte writer execution authority drift"),
        ("atomic_write_json", lambda *_args: None, "atomic JSON writer execution authority drift"),
        ("validate_evidence_authority", lambda *_args: None, "evidence validator execution authority drift"),
        ("validate_written_authority", lambda: None, "post-write validator execution authority drift"),
        ("transactional_write", lambda *_args: None, "transaction writer execution authority drift"),
        ("enforce_execution_authorities", lambda: None, "execution guard authority drift"),
    )
    for attribute, substitute, expected in cases:
        expect_execution_rejection(reconciler, attribute, substitute, expected)

    original_run = reconciler.subprocess.run
    reconciler.subprocess.run = lambda *_args, **_kwargs: None
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            if "subprocess transport execution authority drift" not in str(exc):
                raise RuntimeError(f"subprocess transport rejected for unrelated reason: {exc}") from exc
        else:
            raise RuntimeError("reconciler accepted subprocess transport substitution")
    finally:
        reconciler.subprocess.run = original_run

    original_spec = reconciler.importlib.util.spec_from_file_location
    reconciler.importlib.util.spec_from_file_location = lambda *_args, **_kwargs: None
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            if "module spec loader execution authority drift" not in str(exc):
                raise RuntimeError(f"module spec loader rejected for unrelated reason: {exc}") from exc
        else:
            raise RuntimeError("reconciler accepted module spec loader substitution")
    finally:
        reconciler.importlib.util.spec_from_file_location = original_spec

    original_constructor = reconciler.importlib.util.module_from_spec
    reconciler.importlib.util.module_from_spec = lambda *_args, **_kwargs: object()
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            if "module constructor execution authority drift" not in str(exc):
                raise RuntimeError(f"module constructor rejected for unrelated reason: {exc}") from exc
        else:
            raise RuntimeError("reconciler accepted module constructor substitution")
    finally:
        reconciler.importlib.util.module_from_spec = original_constructor


def prove_validator_chain(reconciler) -> None:
    observed: list[Path] = []
    original_run_validator = reconciler.run_validator
    original_validate_evidence = reconciler.validate_evidence_authority
    original_canonical_run_validator = reconciler._CANONICAL_RUN_VALIDATOR
    original_canonical_validate_evidence = reconciler._CANONICAL_VALIDATE_EVIDENCE_AUTHORITY

    def capture(path: Path, _label: str) -> None:
        observed.append(path.resolve())

    def skip_evidence(_evidence) -> None:
        return None

    try:
        reconciler.run_validator = capture
        reconciler._CANONICAL_RUN_VALIDATOR = capture
        reconciler.validate_evidence_authority = skip_evidence
        reconciler._CANONICAL_VALIDATE_EVIDENCE_AUTHORITY = skip_evidence
        reconciler.validate_written_authority()
    finally:
        reconciler.run_validator = original_run_validator
        reconciler._CANONICAL_RUN_VALIDATOR = original_canonical_run_validator
        reconciler.validate_evidence_authority = original_validate_evidence
        reconciler._CANONICAL_VALIDATE_EVIDENCE_AUTHORITY = original_canonical_validate_evidence

    expected = [
        reconciler.OPERATIONS_VALIDATOR.resolve(),
        reconciler.RATE_LIMIT_VALIDATOR.resolve(),
        reconciler.OPERABILITY_VALIDATOR.resolve(),
        reconciler.ENTRY_DOCS_VALIDATOR.resolve(),
    ]
    if observed != expected:
        raise RuntimeError(f"post-write validator chain drift: {observed!r} != {expected!r}")


def prove_atomic_replace_failure(reconciler) -> None:
    path = reconciler.OPERATIONS_PATH
    original = path.read_bytes()
    original_mode = path.stat().st_mode & 0o777
    pattern = f".{path.name}.*.tmp"
    before = {item.name for item in path.parent.glob(pattern)}
    original_replace = reconciler.os.replace

    def reject_replace(_source, _destination) -> None:
        raise OSError("synthetic atomic replace rejection")

    test_writer = reconciler._build_atomic_write_bytes(reject_replace)
    reconciler.os.replace = reject_replace
    try:
        try:
            test_writer(path, b"synthetic operation authority\n")
        except OSError as exc:
            if "synthetic atomic replace rejection" not in str(exc):
                raise RuntimeError(f"atomic replacement failed for unrelated reason: {exc}") from exc
        else:
            raise RuntimeError("atomic writer accepted synthetic replacement failure")
        if path.read_bytes() != original:
            raise RuntimeError("operations contract changed after failed atomic replacement")
        if (path.stat().st_mode & 0o777) != original_mode:
            raise RuntimeError("operations contract mode changed after failed atomic replacement")
        after = {item.name for item in path.parent.glob(pattern)}
        if after != before:
            raise RuntimeError(f"atomic replacement left temporary residue: {sorted(after - before)}")
    finally:
        reconciler.os.replace = original_replace
        if path.read_bytes() != original:
            path.write_bytes(original)
        path.chmod(original_mode)


def prove_transaction_rollback(reconciler) -> None:
    originals = {
        reconciler.OPERATIONS_PATH: reconciler.OPERATIONS_PATH.read_bytes(),
        reconciler.STATUS_PATH: reconciler.STATUS_PATH.read_bytes(),
    }
    modes = {
        reconciler.OPERATIONS_PATH: reconciler.OPERATIONS_PATH.stat().st_mode & 0o777,
        reconciler.STATUS_PATH: reconciler.STATUS_PATH.stat().st_mode & 0o777,
    }
    operations = copy.deepcopy(load_json(reconciler.OPERATIONS_PATH))
    status = copy.deepcopy(load_json(reconciler.STATUS_PATH))
    operations["readiness"]["evidenceLedgerImplemented"] = True
    status["asOf"] = "2099-01-01"

    original_validator = reconciler.validate_written_authority
    original_canonical_validator = reconciler._CANONICAL_VALIDATE_WRITTEN_AUTHORITY

    def fail_validation() -> None:
        raise reconciler.ReconcileFailure("synthetic post-write validation failure")

    reconciler.validate_written_authority = fail_validation
    reconciler._CANONICAL_VALIDATE_WRITTEN_AUTHORITY = fail_validation
    try:
        try:
            reconciler.transactional_write(operations, status)
        except reconciler.ReconcileFailure as exc:
            if "synthetic post-write validation failure" not in str(exc):
                raise RuntimeError(f"transaction rollback failed for unrelated reason: {exc}") from exc
        else:
            raise RuntimeError("transactional write accepted synthetic post-write validation failure")

        for path, original in originals.items():
            if path.read_bytes() != original:
                raise RuntimeError(f"rollback failed for {path.relative_to(ROOT)}")
            if (path.stat().st_mode & 0o777) != modes[path]:
                raise RuntimeError(f"rollback changed mode for {path.relative_to(ROOT)}")
    finally:
        reconciler.validate_written_authority = original_validator
        reconciler._CANONICAL_VALIDATE_WRITTEN_AUTHORITY = original_canonical_validator
        for path, original in originals.items():
            path.write_bytes(original)
            path.chmod(modes[path])


def prove_transaction_rollback_failure_is_exhaustive(reconciler) -> None:
    originals = {
        reconciler.OPERATIONS_PATH: reconciler.OPERATIONS_PATH.read_bytes(),
        reconciler.STATUS_PATH: reconciler.STATUS_PATH.read_bytes(),
    }
    modes = {
        reconciler.OPERATIONS_PATH: reconciler.OPERATIONS_PATH.stat().st_mode & 0o777,
        reconciler.STATUS_PATH: reconciler.STATUS_PATH.stat().st_mode & 0o777,
    }
    operations = copy.deepcopy(load_json(reconciler.OPERATIONS_PATH))
    status = copy.deepcopy(load_json(reconciler.STATUS_PATH))
    operations["readiness"]["evidenceLedgerImplemented"] = True
    status["asOf"] = "2099-01-01"

    original_validator = reconciler.validate_written_authority
    original_canonical_validator = reconciler._CANONICAL_VALIDATE_WRITTEN_AUTHORITY
    original_writer = reconciler.atomic_write_bytes
    original_canonical_writer = reconciler._CANONICAL_ATOMIC_WRITE_BYTES
    calls: list[Path] = []

    def fail_validation() -> None:
        raise reconciler.ReconcileFailure("synthetic operation evidence primary validation failure")

    def fail_first_rollback(path: Path, payload: bytes) -> None:
        calls.append(path)
        if len(calls) == 3:
            raise OSError("synthetic operation evidence rollback failure")
        original_writer(path, payload)

    reconciler.validate_written_authority = fail_validation
    reconciler._CANONICAL_VALIDATE_WRITTEN_AUTHORITY = fail_validation
    reconciler.atomic_write_bytes = fail_first_rollback
    reconciler._CANONICAL_ATOMIC_WRITE_BYTES = fail_first_rollback
    caught: BaseException | None = None
    try:
        try:
            reconciler.transactional_write(operations, status)
        except BaseException as exc:
            caught = exc
        if caught is None:
            raise RuntimeError("transactional write accepted synthetic rollback failure")
        text = str(caught)
        if "synthetic operation evidence primary validation failure" not in text:
            raise RuntimeError(f"rollback failure masked primary diagnostic: {text}")
        if "rollback incomplete" not in text:
            raise RuntimeError(f"rollback failure omitted incomplete diagnostic: {text}")
        if "synthetic operation evidence rollback failure" not in text:
            raise RuntimeError(f"rollback failure omitted rollback diagnostic: {text}")
        expected_calls = [
            reconciler.OPERATIONS_PATH,
            reconciler.STATUS_PATH,
            reconciler.OPERATIONS_PATH,
            reconciler.STATUS_PATH,
        ]
        if calls != expected_calls:
            raise RuntimeError(f"rollback stopped before restoring every authority: {calls!r}")
        if reconciler.STATUS_PATH.read_bytes() != originals[reconciler.STATUS_PATH]:
            raise RuntimeError("first rollback failure prevented later production-status restore")
        if (reconciler.STATUS_PATH.stat().st_mode & 0o777) != modes[reconciler.STATUS_PATH]:
            raise RuntimeError("later production-status restore changed mode")
    finally:
        reconciler.validate_written_authority = original_validator
        reconciler._CANONICAL_VALIDATE_WRITTEN_AUTHORITY = original_canonical_validator
        reconciler.atomic_write_bytes = original_writer
        reconciler._CANONICAL_ATOMIC_WRITE_BYTES = original_canonical_writer
        for path, original in originals.items():
            if path.read_bytes() != original:
                original_writer(path, original)
            path.chmod(modes[path])

    for path in originals:
        if list(path.parent.glob(f".{path.name}.*.tmp")):
            raise RuntimeError(f"rollback failure left temp residue for {path.relative_to(ROOT)}")


def main() -> int:
    reconciler = load_module()
    expect_authority_identity(reconciler)
    reconciler.enforce_execution_authorities()
    prove_execution_authority_identity(reconciler)
    prove_validator_chain(reconciler)
    prove_atomic_replace_failure(reconciler)
    prove_transaction_rollback(reconciler)
    prove_transaction_rollback_failure_is_exhaustive(reconciler)

    print("PASS: rate-limit operation evidence exact data/executable authorities reject substitution")
    print("PASS: rate-limit operation evidence execution guard and module/subprocess transports reject substitution")
    print("PASS: post-write validation includes operations, aggregate rate-limit, operability and entry-doc authorities")
    print("PASS: atomic replacement failure preserves canonical authority bytes/mode without temporary residue")
    print("PASS: post-write failure restores operations contract and production status with exhaustive rollback")
    print("production evidence generated: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())