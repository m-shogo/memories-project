#!/usr/bin/env python3
"""Prove emergency drill authority rejects detached sources and rolls back on post-write failure."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-rate-limit-emergency-drill.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-rate-limit-emergency-drill.py"


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
    prove_transactional_rollback()
    print("PASS: detached emergency drill sources are rejected")
    print("PASS: emergency drill reconcile rolls back contract and status on post-write failure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
