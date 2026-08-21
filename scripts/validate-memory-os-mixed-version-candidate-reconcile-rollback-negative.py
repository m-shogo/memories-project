#!/usr/bin/env python3
"""Prove mixed-version candidate authority identity and aggregate rollback are fail-closed."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/mixed-version-candidate-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
RECONCILER = ROOT / "scripts/reconcile-memory-os-mixed-version-candidate.py"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_authority_rejection(reconciler: Any, attr: str, replacement: Path) -> None:
    original = getattr(reconciler, attr)
    setattr(reconciler, attr, replacement)
    try:
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"candidate {attr} substitution must be rejected")
    finally:
        setattr(reconciler, attr, original)


def main() -> int:
    reconciler = load_module(RECONCILER, "mixed_version_candidate_reconcile_rollback_negative")
    contract_before = CONTRACT.read_bytes()
    status_before = STATUS.read_bytes()

    expect_authority_rejection(reconciler, "CONTRACT_PATH", reconciler.STATUS_PATH)
    expect_authority_rejection(reconciler, "RESULT_PATH", reconciler.CONTRACT_PATH)
    expect_authority_rejection(reconciler, "REJECTION_PATH", reconciler.RESULT_PATH)
    expect_authority_rejection(reconciler, "STATUS_PATH", reconciler.CONTRACT_PATH)
    expect_authority_rejection(reconciler, "CANDIDATE_VALIDATOR", reconciler.VERSION_VALIDATOR)
    expect_authority_rejection(reconciler, "VERSION_VALIDATOR", reconciler.OPERABILITY_VALIDATOR)
    expect_authority_rejection(reconciler, "OPERABILITY_VALIDATOR", reconciler.CANDIDATE_VALIDATOR)
    if CONTRACT.read_bytes() != contract_before or STATUS.read_bytes() != status_before:
        raise RuntimeError("candidate authority substitution changed canonical bytes")

    contract = json.loads(contract_before.decode("utf-8"))
    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        raise RuntimeError("candidate readiness missing in fixture")
    readiness["exactSourcePassResultCommitted"] = False
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    original_run = reconciler.subprocess.run
    calls: list[Path] = []

    class Result:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(command: list[str], **_: Any) -> Result:
        if command and command[0] == "git":
            return Result(0)
        path = Path(command[1]).resolve()
        calls.append(path)
        if path == reconciler.VERSION_VALIDATOR.resolve():
            return Result(1, stderr="synthetic version aggregate rejection")
        return Result(0)

    reconciler.subprocess.run = fake_run
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            if "version compatibility authority rejected after candidate reconcile" not in str(exc):
                raise RuntimeError(f"unexpected candidate rejection: {exc}") from exc
        else:
            raise RuntimeError("candidate reconciler accepted rejected version aggregate authority")

        if reconciler.CANDIDATE_VALIDATOR.resolve() not in calls:
            raise RuntimeError("candidate reconciler did not invoke candidate validator")
        if reconciler.VERSION_VALIDATOR.resolve() not in calls:
            raise RuntimeError("candidate reconciler did not invoke version aggregate validator")
        if reconciler.OPERABILITY_VALIDATOR.resolve() in calls:
            raise RuntimeError("candidate reconciler continued after version aggregate rejection")
        if CONTRACT.read_bytes() != contract_before:
            raise RuntimeError("candidate reconciler retained contract mutation after aggregate rejection")
        if STATUS.read_bytes() != status_before:
            raise RuntimeError("candidate reconciler mutated production status after aggregate rejection")
    finally:
        reconciler.subprocess.run = original_run
        CONTRACT.write_bytes(contract_before)
        STATUS.write_bytes(status_before)

    print("PASS: mixed-version candidate authority identity and reconcile rollback are fail-closed")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
