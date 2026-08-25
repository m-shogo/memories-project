#!/usr/bin/env python3
"""Prove live-load reconcile pins canonical authorities and rolls back on failure."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-live-load-status.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
LOAD = ROOT / "contracts/operations/load-test-scenario-contract.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    spec = importlib.util.spec_from_file_location("live_load_reconcile", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load live-load reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def expect_authority_rejection(mutator, expected_text: str) -> None:
    module = load_module()
    mutator(module)
    try:
        module.validate_authority_identity()
    except module.ReconcileFailure as exc:
        require(expected_text in str(exc), f"unexpected authority rejection: {exc}")
    else:
        raise Fail(f"live-load reconciler accepted authority substitution: {expected_text}")


def expect_runtime_rejection(mutator, expected_text: str) -> None:
    before_status = STATUS.read_bytes()
    before_load = LOAD.read_bytes()
    module = load_module()
    mutator(module)
    try:
        module.enforce_runtime_authorities()
    except module.ReconcileFailure as exc:
        require(expected_text in str(exc), f"unexpected runtime rejection: {exc}")
    else:
        raise Fail(f"live-load reconciler accepted runtime substitution: {expected_text}")
    require(STATUS.read_bytes() == before_status, "runtime rejection mutated canonical production status")
    require(LOAD.read_bytes() == before_load, "runtime rejection mutated canonical load contract")


def main() -> int:
    expect_authority_rejection(
        lambda module: setattr(
            module,
            "POSTGRES_VALIDATOR",
            ROOT / "scripts/validate-memory-os-load.py",
        ),
        "canonical PostgreSQL live-load validator authority drift",
    )
    expect_authority_rejection(
        lambda module: setattr(module, "STATUS_PATH", LOAD),
        "canonical production status authority drift",
    )
    expect_runtime_rejection(
        lambda module: setattr(module.subprocess, "run", lambda *args, **kwargs: None),
        "live-load subprocess transport substitution",
    )

    module = load_module()
    before_status = STATUS.read_bytes()
    before_load = LOAD.read_bytes()
    try:
        module.main(_guard=lambda: None)
    except module.ReconcileFailure as exc:
        require("live-load runtime guard substitution" in str(exc), f"unexpected guard rejection: {exc}")
    else:
        raise Fail("live-load reconciler accepted runtime guard substitution")
    require(STATUS.read_bytes() == before_status, "guard rejection mutated canonical production status")
    require(LOAD.read_bytes() == before_load, "guard rejection mutated canonical load contract")

    module = load_module()
    try:
        module.run_validator(
            ROOT / "scripts/validate-memory-os-load.py",
            "load",
            _guard=lambda: None,
        )
    except module.ReconcileFailure as exc:
        require("live-load runtime guard substitution" in str(exc), f"unexpected validator guard rejection: {exc}")
    else:
        raise Fail("live-load validator accepted runtime guard substitution")

    module = load_module()
    expected_sha = "1" * 40

    with tempfile.TemporaryDirectory(prefix="memory-os-live-load-rollback-") as tmp:
        tmp_root = Path(tmp)
        status_path = tmp_root / "production-operability-status.json"
        load_path = tmp_root / "load-test-scenario-contract.v1.json"
        postgres_result = tmp_root / "live-postgres.json"
        object_result = tmp_root / "live-object.json"
        pass_validator = tmp_root / "pass.py"
        fail_validator = tmp_root / "fail.py"

        status = json.loads(STATUS.read_text(encoding="utf-8"))
        load_contract = json.loads(LOAD.read_text(encoding="utf-8"))

        area = next(
            item
            for item in status["areas"]
            if isinstance(item, dict) and item.get("id") == "OPS-P0-006"
        )
        area["existingEvidence"] = [
            item
            for item in area["existingEvidence"]
            if item != module.POSTGRES_EVIDENCE
        ]
        load_contract["readiness"]["exactHeadLiveResultsCommitted"] = False

        write_json(status_path, status)
        write_json(load_path, load_contract)
        write_json(
            postgres_result,
            {
                "commitSha": expected_sha,
                "scenarios": [{"result": "PASS", "integrityResult": "PASS"}],
            },
        )
        write_json(
            object_result,
            {
                "commitSha": expected_sha,
                "scenarios": [{"result": "PASS", "integrityResult": "PASS"}],
            },
        )
        pass_validator.write_text("raise SystemExit(0)\n", encoding="utf-8")
        fail_validator.write_text("raise SystemExit(17)\n", encoding="utf-8")

        module.STATUS_PATH = status_path
        module.LOAD_CONTRACT_PATH = load_path
        module.POSTGRES_RESULT = postgres_result
        module.OBJECT_RESULT = object_result
        module.LOAD_VALIDATOR = pass_validator
        module.OPERABILITY_VALIDATOR = fail_validator
        module.validate_authority_identity = lambda: None
        module.validate_live_authorities = lambda expected: None

        before_status = status_path.read_bytes()
        before_load = load_path.read_bytes()
        previous_expected = os.environ.get("EXPECTED_COMMIT_SHA")
        os.environ["EXPECTED_COMMIT_SHA"] = expected_sha
        try:
            try:
                module.main()
            except module.ReconcileFailure as exc:
                require(
                    "canonical operability validation failed" in str(exc),
                    f"unexpected failure reason: {exc}",
                )
            else:
                raise Fail("reconciler accepted a failing post-write operability validator")
        finally:
            if previous_expected is None:
                os.environ.pop("EXPECTED_COMMIT_SHA", None)
            else:
                os.environ["EXPECTED_COMMIT_SHA"] = previous_expected

        require(status_path.read_bytes() == before_status, "status was not rolled back byte-for-byte")
        require(load_path.read_bytes() == before_load, "load contract was not rolled back byte-for-byte")
        require(not list(tmp_root.glob(".*.tmp")), "transaction rollback left an atomic temp file")

        atomic_target = tmp_root / "atomic-target.json"
        atomic_target.write_bytes(b"before\n")
        original_replace = module.os.replace
        failed = False

        def fail_replace(source, destination):
            nonlocal failed
            if Path(destination) == atomic_target and not failed:
                failed = True
                raise OSError("synthetic atomic replace failure")
            return original_replace(source, destination)

        module.os.replace = fail_replace
        try:
            try:
                module.atomic_write_bytes(atomic_target, b"after\n")
            except OSError as exc:
                require("synthetic atomic replace failure" in str(exc), f"unexpected atomic failure: {exc}")
            else:
                raise Fail("atomic writer accepted a synthetic replacement failure")
        finally:
            module.os.replace = original_replace

        require(failed, "synthetic atomic replacement failure was not exercised")
        require(atomic_target.read_bytes() == b"before\n", "atomic replacement failure mutated target bytes")
        require(not list(tmp_root.glob(".*.tmp")), "atomic replacement failure left a temp file")

    print(
        "PASS: live-load reconcile pins canonical data, execution transport and runtime guard authorities, publishes atomically, and rolls back both derived authorities after post-write validation failure"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError, json.JSONDecodeError) as exc:
        print(f"LIVE LOAD RECONCILE ROLLBACK NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
