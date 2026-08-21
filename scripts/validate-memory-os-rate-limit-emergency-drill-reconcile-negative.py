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
    except Exception as exc:
        if expected not in str(exc):
            raise AssertionError(f"unexpected authority rejection: {exc}") from exc
    else:
        raise AssertionError(f"authority substitution was incorrectly accepted: {expected}")


def git(*args: str, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def detached_side_commit() -> str:
    tree = git("rev-parse", "HEAD^{tree}")
    parent = git("rev-parse", "HEAD^")
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "memory-os-lineage-test",
            "GIT_AUTHOR_EMAIL": "memory-os-lineage-test@example.invalid",
            "GIT_COMMITTER_NAME": "memory-os-lineage-test",
            "GIT_COMMITTER_EMAIL": "memory-os-lineage-test@example.invalid",
        }
    )
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
    reconciler = load_module(
        RECONCILER_PATH,
        "memory_os_rate_limit_emergency_authority_identity_negative",
    )
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
                evaluator.validate_authority(
                    evaluator.DEFAULT_LEDGER.resolve(), record_path, {}, record_bytes
                )
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
            evaluator.validate_authority(
                evaluator.DEFAULT_LEDGER.resolve(), record_path, {}, record_bytes
            )
        finally:
            evaluator.load_validator = original_loader
        if calls != ["record"]:
            raise AssertionError(
                f"canonical evaluator did not validate the exact record after ledger validation: {calls}"
            )

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
        rogue.write_text("class ValidationFailure(RuntimeError):\n    pass\n\ndef main():\n    return 0\n", encoding="utf-8")
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


def prove_runner_foundation_delegation() -> None:
    runner = load_module(RUNNER_PATH, "memory_os_rate_limit_emergency_runner_negative")
    original_run = runner.subprocess.run
    calls: list[list[str]] = []

    def reject_foundation(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(
            returncode=17,
            stdout="",
            stderr="synthetic canonical foundation rejection",
        )

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


def prove_aggregate_validator_delegation() -> None:
    reconciler = load_module(
        RECONCILER_PATH,
        "memory_os_rate_limit_emergency_aggregate_negative",
    )
    original = reconciler.run_validator
    calls: list[Path] = []

    def reject_rate_limit(path: Path, *args: str) -> None:
        calls.append(path)
        if path == reconciler.RATE_LIMIT_VALIDATOR:
            raise reconciler.ReconcileFailure("synthetic aggregate rate-limit rejection")

    reconciler.run_validator = reject_rate_limit
    try:
        try:
            reconciler.validate_written_authority("0" * 40)
        except reconciler.ReconcileFailure as exc:
            if "synthetic aggregate rate-limit rejection" not in str(exc):
                raise AssertionError(f"unexpected aggregate rejection: {exc}") from exc
        else:
            raise AssertionError("aggregate rate-limit rejection was incorrectly accepted")
    finally:
        reconciler.run_validator = original

    expected = [
        reconciler.VALIDATOR_PATH,
        reconciler.OPERATIONS_VALIDATOR,
        reconciler.RATE_LIMIT_VALIDATOR,
    ]
    if calls != expected:
        raise AssertionError(f"emergency reconcile aggregate validator order drift: {calls}")
    if reconciler.OPERABILITY_VALIDATOR in calls:
        raise AssertionError("operability validation ran after an earlier aggregate rejection")


def prove_transactional_rollback() -> None:
    reconciler = load_module(
        RECONCILER_PATH,
        "memory_os_rate_limit_emergency_reconciler_negative",
    )
    contract_before = reconciler.CONTRACT_PATH.read_bytes()
    status_before = reconciler.STATUS_PATH.read_bytes()
    contract = json.loads(contract_before)
    status = json.loads(status_before)

    contract["description"] = str(contract.get("description", "")) + " synthetic-rollback-probe"
    status["asOf"] = "2099-01-01"

    original_validator = reconciler.validate_written_authority

    def reject_after_write(source_sha: str) -> None:
        if reconciler.CONTRACT_PATH.read_bytes() == contract_before:
            raise AssertionError("contract candidate was not written before post-write validation")
        if reconciler.STATUS_PATH.read_bytes() == status_before:
            raise AssertionError("status candidate was not written before post-write validation")
        raise reconciler.ReconcileFailure("synthetic post-write validation failure")

    reconciler.validate_written_authority = reject_after_write
    try:
        try:
            reconciler.transactional_write(contract, status, "0" * 40)
        except reconciler.ReconcileFailure as exc:
            if "synthetic post-write validation failure" not in str(exc):
                raise AssertionError(f"unexpected rollback rejection: {exc}") from exc
        else:
            raise AssertionError("post-write failure was incorrectly accepted")
    finally:
        reconciler.validate_written_authority = original_validator

    if reconciler.CONTRACT_PATH.read_bytes() != contract_before:
        raise AssertionError("emergency drill contract was not rolled back byte-for-byte")
    if reconciler.STATUS_PATH.read_bytes() != status_before:
        raise AssertionError("production status was not rolled back byte-for-byte")


def main() -> int:
    prove_lineage_rejection()
    prove_reconciler_authority_identity()
    prove_evaluator_authority_boundaries()
    prove_runner_foundation_delegation()
    prove_aggregate_validator_delegation()
    prove_transactional_rollback()
    print("PASS: detached emergency drill sources are rejected")
    print("PASS: emergency reconcile pins canonical data and validator authorities")
    print("PASS: emergency evaluator validator authority and exact exit semantics are fail-closed")
    print("PASS: emergency evaluator validates the exact record used for state evaluation")
    print("PASS: emergency evaluator rejects record drift during authority validation")
    print("PASS: emergency evaluator rejects invalid UTC timestamps without traceback semantics")
    print("PASS: emergency evaluator rejects symlink operation evidence records")
    print("PASS: direct emergency drill runner delegates to canonical foundation validation")
    print("PASS: emergency drill reconcile includes rate-limit and operability aggregate validation")
    print("PASS: emergency drill reconcile rolls back contract and status on post-write failure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
