#!/usr/bin/env python3
"""Prove emergency drill/evaluator authority rejects detached or weak sources and rolls back."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-emergency-drill.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rate-limit-emergency-drill.py"
EVALUATOR_PATH = ROOT / "scripts/evaluate-memory-os-rate-limit-emergency-state.py"
RUNNER_PATH = ROOT / "scripts/run-memory-os-rate-limit-emergency-drill.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(callback, expected: str) -> None:
    try:
        callback()
    except (Exception, SystemExit) as exc:
        if expected not in str(exc):
            raise AssertionError(f"unexpected authority rejection: {exc}") from exc
    else:
        raise AssertionError(f"authority substitution was incorrectly accepted: {expected}")


def git(*args: str, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def detached_side_commit() -> str:
    tree = git("rev-parse", "HEAD^{tree}")
    parent = git("rev-parse", "HEAD^")
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "memory-os-lineage-test",
        "GIT_AUTHOR_EMAIL": "memory-os-lineage-test@example.invalid",
        "GIT_COMMITTER_NAME": "memory-os-lineage-test",
        "GIT_COMMITTER_EMAIL": "memory-os-lineage-test@example.invalid",
    })
    return git("commit-tree", tree, "-p", parent, "-m", "synthetic side commit", env=env)


def prove_lineage_rejection() -> None:
    validator = load_module(VALIDATOR_PATH, "memory_os_rate_limit_emergency_validator_negative")
    current_head = git("rev-parse", "HEAD")
    validator.require_commit_ancestor(current_head)
    side_commit = detached_side_commit()
    try:
        validator.require_commit_ancestor(side_commit)
    except validator.ValidationFailure as exc:
        if "ancestor of current HEAD" not in str(exc):
            raise AssertionError(f"unexpected lineage rejection: {exc}") from exc
    else:
        raise AssertionError("detached emergency drill source was incorrectly accepted")
    if git("rev-parse", "HEAD") != current_head:
        raise AssertionError("lineage negative changed the current branch ref")


def prove_reconciler_authority_identity() -> None:
    reconciler = load_module(RECONCILER_PATH, "memory_os_rate_limit_emergency_authority_identity_negative")
    substitutions = (
        ("CONTRACT_PATH", ROOT / "README.md", "emergency drill contract authority drift"),
        ("RESULT_PATH", ROOT / "README.md", "emergency drill result authority drift"),
        ("OPERATIONS_PATH", ROOT / "README.md", "rate-limit operations contract authority drift"),
        ("STATUS_PATH", ROOT / "SECURITY.md", "production operability status authority drift"),
        ("VALIDATOR_PATH", EVALUATOR_PATH, "emergency drill validator authority drift"),
        ("OPERATIONS_VALIDATOR", VALIDATOR_PATH, "rate-limit operations validator authority drift"),
        ("RATE_LIMIT_VALIDATOR", VALIDATOR_PATH, "rate-limit validator authority drift"),
        ("OPERABILITY_VALIDATOR", VALIDATOR_PATH, "operability validator authority drift"),
    )
    for attr, substitute, expected in substitutions:
        original = getattr(reconciler, attr)
        try:
            setattr(reconciler, attr, substitute)
            expect_rejection(reconciler.enforce_runtime_authorities, expected)
        finally:
            setattr(reconciler, attr, original)

    paired_paths = (
        ("CONTRACT_PATH", "CANONICAL_CONTRACT_PATH", ROOT / "README.md", "canonical emergency drill contract identity drift"),
        ("RESULT_PATH", "CANONICAL_RESULT_PATH", ROOT / "README.md", "canonical emergency drill result identity drift"),
        ("OPERATIONS_PATH", "CANONICAL_OPERATIONS_PATH", ROOT / "README.md", "canonical rate-limit operations contract identity drift"),
        ("STATUS_PATH", "CANONICAL_STATUS_PATH", ROOT / "SECURITY.md", "canonical production operability status identity drift"),
        ("VALIDATOR_PATH", "CANONICAL_VALIDATOR_PATH", EVALUATOR_PATH, "canonical emergency drill validator identity drift"),
        ("OPERATIONS_VALIDATOR", "CANONICAL_OPERATIONS_VALIDATOR", VALIDATOR_PATH, "canonical rate-limit operations validator identity drift"),
        ("RATE_LIMIT_VALIDATOR", "CANONICAL_RATE_LIMIT_VALIDATOR", VALIDATOR_PATH, "canonical rate-limit validator identity drift"),
        ("OPERABILITY_VALIDATOR", "CANONICAL_OPERABILITY_VALIDATOR", VALIDATOR_PATH, "canonical operability validator identity drift"),
    )
    for runtime_attr, canonical_attr, substitute, expected in paired_paths:
        runtime_original = getattr(reconciler, runtime_attr)
        canonical_original = getattr(reconciler, canonical_attr)
        try:
            setattr(reconciler, runtime_attr, substitute)
            setattr(reconciler, canonical_attr, substitute)
            expect_rejection(reconciler.enforce_runtime_authorities, expected)
        finally:
            setattr(reconciler, runtime_attr, runtime_original)
            setattr(reconciler, canonical_attr, canonical_original)

    original_root = reconciler.ROOT
    try:
        reconciler.ROOT = ROOT / "scripts"
        expect_rejection(reconciler.enforce_runtime_authorities, "emergency drill repository authority drift")
    finally:
        reconciler.ROOT = original_root

    original_run = reconciler.subprocess.run
    canonical_run = reconciler.CANONICAL_SUBPROCESS_RUN
    fake_run = lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="")
    try:
        reconciler.subprocess.run = fake_run
        reconciler.CANONICAL_SUBPROCESS_RUN = fake_run
        expect_rejection(reconciler.enforce_runtime_authorities, "emergency drill subprocess execution authority drift")
    finally:
        reconciler.subprocess.run = original_run
        reconciler.CANONICAL_SUBPROCESS_RUN = canonical_run

    original_replace = reconciler.os.replace
    canonical_replace = reconciler.CANONICAL_OS_REPLACE
    fake_replace = lambda *args, **kwargs: None
    try:
        reconciler.os.replace = fake_replace
        reconciler.CANONICAL_OS_REPLACE = fake_replace
        expect_rejection(reconciler.enforce_runtime_authorities, "emergency drill atomic replacement transport authority drift")
    finally:
        reconciler.os.replace = original_replace
        reconciler.CANONICAL_OS_REPLACE = canonical_replace


def prove_execution_helper_identity() -> None:
    reconciler = load_module(RECONCILER_PATH, "memory_os_rate_limit_emergency_execution_identity_negative")

    original_run_validator = reconciler.run_validator
    try:
        reconciler.run_validator = lambda *args, **kwargs: None
        expect_rejection(
            lambda: reconciler.validate_written_authority("0" * 40),
            "emergency drill validator execution authority drift",
        )
    finally:
        reconciler.run_validator = original_run_validator

    original_json_writer = reconciler.atomic_write_json
    try:
        reconciler.atomic_write_json = lambda *args, **kwargs: None
        expect_rejection(
            lambda: reconciler.transactional_write({}, {}, "0" * 40),
            "emergency drill JSON writer authority drift",
        )
    finally:
        reconciler.atomic_write_json = original_json_writer

    original_bytes_writer = reconciler.atomic_write_bytes
    try:
        reconciler.atomic_write_bytes = lambda *args, **kwargs: None
        expect_rejection(
            lambda: reconciler.transactional_write({}, {}, "0" * 40),
            "emergency drill atomic writer authority drift",
        )
    finally:
        reconciler.atomic_write_bytes = original_bytes_writer

    original_post_validator = reconciler.validate_written_authority
    try:
        reconciler.validate_written_authority = lambda source_sha: None
        expect_rejection(
            lambda: reconciler.transactional_write({}, {}, "0" * 40),
            "emergency drill post-write validator authority drift",
        )
    finally:
        reconciler.validate_written_authority = original_post_validator

    original_guard = reconciler.enforce_runtime_authorities
    try:
        reconciler.enforce_runtime_authorities = lambda: None
        expect_rejection(reconciler.main, "emergency drill runtime guard authority drift")
    finally:
        reconciler.enforce_runtime_authorities = original_guard

    original_transaction = reconciler.transactional_write
    try:
        reconciler.transactional_write = lambda *args, **kwargs: None
        expect_rejection(reconciler.main, "emergency drill transaction execution authority drift")
    finally:
        reconciler.transactional_write = original_transaction


def prove_evaluator_authority_boundaries() -> None:
    evaluator = load_module(EVALUATOR_PATH, "memory_os_rate_limit_emergency_evaluator_negative")

    class SyntheticValidationFailure(RuntimeError):
        pass

    original_loader = evaluator.load_validator
    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-evaluator-record-") as tmp:
        record_path = Path(tmp) / "record.json"
        record_path.write_text("{}\n", encoding="utf-8")
        record_bytes = record_path.read_bytes()

        evaluator.load_validator = lambda: SimpleNamespace(
            main=lambda: False,
            ValidationFailure=SyntheticValidationFailure,
            load_contract_context=lambda: ({}, set()),
            validate_record=lambda record, contract, policy_ids: None,
        )
        try:
            try:
                evaluator.validate_authority(evaluator.DEFAULT_LEDGER.resolve(), record_path, {}, record_bytes)
            except SystemExit as exc:
                if "returned non-zero: False" not in str(exc):
                    raise AssertionError(f"unexpected boolean-exit rejection: {exc}") from exc
            else:
                raise AssertionError("boolean false validator result was incorrectly accepted as exit zero")
        finally:
            evaluator.load_validator = original_loader

        calls: list[str] = []
        evaluator.load_validator = lambda: SimpleNamespace(
            main=lambda: 0,
            ValidationFailure=SyntheticValidationFailure,
            load_contract_context=lambda: ({}, set()),
            validate_record=lambda record, contract, policy_ids: calls.append("record"),
        )
        try:
            evaluator.validate_authority(evaluator.DEFAULT_LEDGER.resolve(), record_path, {}, record_bytes)
        finally:
            evaluator.load_validator = original_loader
        if calls != ["record"]:
            raise AssertionError(f"canonical evaluator did not validate the exact record after ledger validation: {calls}")

        def mutate_record(record, contract, policy_ids) -> None:
            record_path.write_text('{"mutated":true}\n', encoding="utf-8")

        evaluator.load_validator = lambda: SimpleNamespace(
            main=lambda: 0,
            ValidationFailure=SyntheticValidationFailure,
            load_contract_context=lambda: ({}, set()),
            validate_record=mutate_record,
        )
        try:
            try:
                evaluator.validate_authority(Path(tmp), record_path, {}, record_bytes)
            except SystemExit as exc:
                if "changed during authority validation" not in str(exc):
                    raise AssertionError(f"unexpected record-drift rejection: {exc}") from exc
            else:
                raise AssertionError("operation evidence record drift during validation was accepted")
        finally:
            evaluator.load_validator = original_loader

    original_path = evaluator.VALIDATOR_PATH
    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-evaluator-authority-") as tmp:
        rogue = Path(tmp) / "validator.py"
        rogue.write_text(
            "class ValidationFailure(RuntimeError):\n    pass\n\ndef main():\n    return 0\n",
            encoding="utf-8",
        )
        evaluator.VALIDATOR_PATH = rogue
        try:
            try:
                evaluator.load_validator()
            except SystemExit as exc:
                if "validator authority" not in str(exc):
                    raise AssertionError(f"unexpected evaluator path rejection: {exc}") from exc
            else:
                raise AssertionError("out-of-repository evaluator validator authority was incorrectly accepted")
        finally:
            evaluator.VALIDATOR_PATH = original_path

    try:
        evaluator.timestamp("2026-99-99T99:99:99Z")
    except SystemExit as exc:
        if "valid UTC RFC3339" not in str(exc):
            raise AssertionError(f"unexpected invalid timestamp rejection: {exc}") from exc
    else:
        raise AssertionError("invalid RFC3339 timestamp was incorrectly accepted")

    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-evaluator-ledger-") as tmp:
        ledger = Path(tmp) / "ledger"
        ledger.mkdir()
        external = Path(tmp) / "external-record.json"
        external.write_text("{}\n", encoding="utf-8")
        operation_id = "RLOP-20260820T000000Z-symlink"
        record_path = ledger / f"{operation_id}.json"
        record_path.symlink_to(external)
        try:
            evaluator.resolve_operation_record(ledger, operation_id)
        except SystemExit as exc:
            if "must not be a symlink" not in str(exc):
                raise AssertionError(f"unexpected symlink record rejection: {exc}") from exc
        else:
            raise AssertionError("symlink operation evidence record was incorrectly accepted")


def prove_evaluator_runtime_guard_identity() -> None:
    evaluator = load_module(EVALUATOR_PATH, "memory_os_rate_limit_emergency_evaluator_guard_negative")
    original_guard = evaluator.enforce_runtime_authorities
    evaluator.enforce_runtime_authorities = lambda: None
    try:
        expect_rejection(
            evaluator.main,
            "emergency evaluator runtime guard execution authority drift",
        )
    finally:
        evaluator.enforce_runtime_authorities = original_guard

    substitutions = (
        ("ROOT", ROOT / "scripts", "emergency evaluator repository authority drift"),
        ("DEFAULT_LEDGER", ROOT / "README.md", "emergency evaluator ledger authority drift"),
        ("VALIDATOR_PATH", EVALUATOR_PATH, "emergency evaluator validator authority drift"),
        ("load", lambda path: ({}, b""), "emergency evaluator load execution authority drift"),
        ("load_validator", lambda: None, "emergency evaluator validator loader execution authority drift"),
        ("timestamp", lambda value: None, "emergency evaluator timestamp execution authority drift"),
        ("resolve_ledger", lambda raw: ROOT, "emergency evaluator ledger resolver execution authority drift"),
        ("resolve_operation_record", lambda ledger, operation_id: None, "emergency evaluator record resolver execution authority drift"),
        ("validate_authority", lambda *args: None, "emergency evaluator record validator execution authority drift"),
    )
    for attr, substitute, expected in substitutions:
        original = getattr(evaluator, attr)
        try:
            setattr(evaluator, attr, substitute)
            expect_rejection(evaluator.enforce_runtime_authorities, expected)
        finally:
            setattr(evaluator, attr, original)


def prove_runner_foundation_delegation() -> None:
    runner = load_module(RUNNER_PATH, "memory_os_rate_limit_emergency_runner_negative")
    original_run = runner.subprocess.run
    calls: list[list[str]] = []

    def reject_foundation(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(returncode=17, stdout="", stderr="synthetic canonical foundation rejection")

    runner.subprocess.run = reject_foundation
    try:
        try:
            runner.validate_foundation_authority()
        except runner.DrillFailure as exc:
            if "canonical emergency drill authority invalid" not in str(exc):
                raise AssertionError(f"unexpected runner foundation rejection: {exc}") from exc
        else:
            raise AssertionError("direct emergency drill runner bypassed canonical foundation validation")
    finally:
        runner.subprocess.run = original_run

    expected = ["python", str(runner.VALIDATOR_PATH)]
    if calls != [expected]:
        raise AssertionError(f"runner delegated to unexpected foundation authority: {calls}")


def prove_atomic_replace_failure_and_mode() -> None:
    reconciler = load_module(RECONCILER_PATH, "memory_os_rate_limit_emergency_atomic_negative")
    with tempfile.TemporaryDirectory(prefix="memory-os-rate-limit-emergency-atomic-") as tmp:
        root = Path(tmp)
        path = root / "authority.json"
        path.write_bytes(b"original\n")
        path.chmod(0o640)
        reconciler.atomic_write_bytes(path, b"replacement\n")
        if path.read_bytes() != b"replacement\n":
            raise AssertionError("emergency atomic writer did not replace candidate bytes")
        if path.stat().st_mode & 0o777 != 0o640:
            raise AssertionError("emergency atomic writer did not preserve existing file mode")

        destination_directory = root / "destination-directory"
        destination_directory.mkdir()
        pattern = f".{destination_directory.name}.*.tmp"
        before = {item.name for item in root.glob(pattern)}
        try:
            reconciler.atomic_write_bytes(destination_directory, b"synthetic emergency authority\n")
        except OSError:
            pass
        else:
            raise AssertionError("atomic emergency authority replacement failure was accepted")
        after = {item.name for item in root.glob(pattern)}
        if after != before:
            raise AssertionError(f"emergency atomic replacement left temporary residue: {sorted(after - before)}")


def prove_transactional_rollback() -> None:
    reconciler = load_module(RECONCILER_PATH, "memory_os_rate_limit_emergency_reconciler_negative")
    contract_before = reconciler.CONTRACT_PATH.read_bytes()
    status_before = reconciler.STATUS_PATH.read_bytes()
    validator_path = reconciler.OPERABILITY_VALIDATOR
    validator_before = validator_path.read_bytes()
    validator_mode = validator_path.stat().st_mode & 0o777
    contract = json.loads(contract_before)
    status = json.loads(status_before)
    contract["description"] = str(contract.get("description", "")) + " synthetic-rollback-probe"
    status["asOf"] = "2099-01-01"
    result = json.loads(reconciler.RESULT_PATH.read_text(encoding="utf-8"))
    source_sha = result.get("commitSha")
    if not isinstance(source_sha, str) or len(source_sha) != 40:
        raise AssertionError("canonical emergency result source SHA missing")

    try:
        validator_path.write_text("#!/usr/bin/env python3\nraise SystemExit(17)\n", encoding="utf-8")
        validator_path.chmod(validator_mode)
        try:
            reconciler.transactional_write(contract, status, source_sha)
        except reconciler.ReconcileFailure as exc:
            if "post-write validation failed for validate-memory-os-operability.py" not in str(exc):
                raise AssertionError(f"unexpected rollback rejection: {exc}") from exc
        else:
            raise AssertionError("post-write aggregate failure was incorrectly accepted")
    finally:
        validator_path.write_bytes(validator_before)
        validator_path.chmod(validator_mode)

    if reconciler.CONTRACT_PATH.read_bytes() != contract_before:
        raise AssertionError("emergency drill contract was not rolled back byte-for-byte")
    if reconciler.STATUS_PATH.read_bytes() != status_before:
        raise AssertionError("production status was not rolled back byte-for-byte")


def main() -> int:
    prove_lineage_rejection()
    prove_reconciler_authority_identity()
    prove_execution_helper_identity()
    prove_evaluator_authority_boundaries()
    prove_evaluator_runtime_guard_identity()
    prove_runner_foundation_delegation()
    prove_atomic_replace_failure_and_mode()
    prove_transactional_rollback()
    print("PASS: detached emergency drill sources are rejected")
    print("PASS: emergency reconcile pins immutable canonical data and validator authorities")
    print("PASS: emergency reconcile rejects paired path, transport, guard, writer, and transaction substitution")
    print("PASS: emergency evaluator validator authority and exact exit semantics are fail-closed")
    print("PASS: emergency evaluator runtime guard and execution helpers are fail-closed")
    print("PASS: emergency evaluator validates the exact record used for state evaluation")
    print("PASS: emergency evaluator rejects record drift during authority validation")
    print("PASS: emergency evaluator rejects invalid UTC timestamps without traceback semantics")
    print("PASS: emergency evaluator rejects symlink operation evidence records")
    print("PASS: direct emergency drill runner delegates to canonical foundation validation")
    print("PASS: emergency drill atomic replacement preserves mode and cleans temp files")
    print("PASS: emergency drill reconcile rolls back contract and status on canonical aggregate failure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
