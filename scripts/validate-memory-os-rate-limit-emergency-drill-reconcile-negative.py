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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def prove_evaluator_authority_boundaries() -> None:
    evaluator = load_module(EVALUATOR_PATH, "memory_os_rate_limit_emergency_evaluator_negative")

    class SyntheticValidationFailure(RuntimeError):
        pass

    original_loader = evaluator.load_validator
    evaluator.load_validator = lambda: SimpleNamespace(
        main=lambda: False,
        ValidationFailure=SyntheticValidationFailure,
        load_contract_context=lambda: ({}, set()),
        validate_record=lambda record, contract, policy_ids: None,
    )
    try:
        try:
            evaluator.validate_authority(evaluator.DEFAULT_LEDGER.resolve(), {})
        except SystemExit as exc:
            if "returned non-zero: False" not in str(exc):
                raise AssertionError(f"unexpected boolean-exit rejection: {exc}") from exc
        else:
            raise AssertionError("boolean false validator result was incorrectly accepted as exit zero")
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
    prove_evaluator_authority_boundaries()
    prove_transactional_rollback()
    print("PASS: detached emergency drill sources are rejected")
    print("PASS: emergency evaluator validator authority and exact exit semantics are fail-closed")
    print("PASS: emergency evaluator rejects invalid UTC timestamps without traceback semantics")
    print("PASS: emergency evaluator rejects symlink operation evidence records")
    print("PASS: emergency drill reconcile rolls back contract and status on post-write failure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
