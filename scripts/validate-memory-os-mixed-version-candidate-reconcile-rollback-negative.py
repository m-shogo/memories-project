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

    try:
        reconciler.main(_guard=lambda: None)
    except reconciler.ReconcileFailure as exc:
        if "runtime guard substitution" not in str(exc):
            raise RuntimeError(f"unexpected runtime guard rejection: {exc}") from exc
    else:
        raise RuntimeError("candidate runtime guard substitution must be rejected")

    original_run = reconciler.subprocess.run
    reconciler.subprocess.run = lambda *args, **kwargs: None
    try:
        try:
            reconciler.enforce_runtime_authorities()
        except reconciler.ReconcileFailure as exc:
            if "subprocess transport substitution" not in str(exc):
                raise RuntimeError(f"unexpected subprocess transport rejection: {exc}") from exc
        else:
            raise RuntimeError("candidate subprocess transport substitution must be rejected")
    finally:
        reconciler.subprocess.run = original_run

    if CONTRACT.read_bytes() != contract_before or STATUS.read_bytes() != status_before:
        raise RuntimeError("candidate authority substitution changed canonical bytes")

    contract = json.loads(contract_before.decode("utf-8"))
    readiness = contract.get("readiness")
    if not isinstance(readiness, dict):
        raise RuntimeError("candidate readiness missing in fixture")
    readiness["exactSourcePassResultCommitted"] = False
    CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    transaction_before = CONTRACT.read_bytes()

    version_before = reconciler.VERSION_VALIDATOR.read_bytes()
    failing_version_validator = (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('synthetic version aggregate rejection', file=sys.stderr)\n"
        "raise SystemExit(1)\n"
    ).encode("utf-8")
    reconciler.VERSION_VALIDATOR.write_bytes(failing_version_validator)
    try:
        try:
            reconciler.main()
        except reconciler.ReconcileFailure as exc:
            if "version compatibility authority rejected after candidate reconcile" not in str(exc):
                raise RuntimeError(f"unexpected candidate rejection: {exc}") from exc
        else:
            raise RuntimeError("candidate reconciler accepted rejected version aggregate authority")

        if CONTRACT.read_bytes() != transaction_before:
            raise RuntimeError("candidate reconciler did not restore the pre-transaction contract bytes after aggregate rejection")
        if STATUS.read_bytes() != status_before:
            raise RuntimeError("candidate reconciler mutated production status after aggregate rejection")
    finally:
        reconciler.VERSION_VALIDATOR.write_bytes(version_before)
        CONTRACT.write_bytes(contract_before)
        STATUS.write_bytes(status_before)

    temp_before = set(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp"))
    original_replace = reconciler.os.replace
    replace_calls = 0

    def fail_first_replace(src: Any, dst: Any) -> None:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 1:
            raise OSError("synthetic atomic replacement failure")
        original_replace(src, dst)

    atomic_contract = json.loads(contract_before.decode("utf-8"))
    atomic_readiness = atomic_contract.get("readiness")
    if not isinstance(atomic_readiness, dict):
        raise RuntimeError("candidate readiness missing in atomic fixture")
    atomic_readiness["exactSourcePassResultCommitted"] = False
    reconciler.os.replace = fail_first_replace
    try:
        try:
            reconciler.commit_outputs_transactionally({CONTRACT: atomic_contract})
        except reconciler.ReconcileFailure as exc:
            if "synthetic atomic replacement failure" not in str(exc):
                raise RuntimeError(f"unexpected atomic replacement rejection: {exc}") from exc
        else:
            raise RuntimeError("candidate reconciler accepted failed atomic replacement")
    finally:
        reconciler.os.replace = original_replace

    if CONTRACT.read_bytes() != contract_before:
        raise RuntimeError("candidate atomic replacement failure changed canonical contract bytes")
    if STATUS.read_bytes() != status_before:
        raise RuntimeError("candidate atomic replacement failure changed production status bytes")
    temp_after = set(CONTRACT.parent.glob(f".{CONTRACT.name}.*.tmp"))
    if temp_after != temp_before:
        raise RuntimeError("candidate atomic replacement failure left temporary authority residue")
    if replace_calls < 2:
        raise RuntimeError("candidate atomic replacement failure did not exercise atomic rollback")

    print("PASS: mixed-version candidate authority identity, runtime guard, execution transport, atomic replacement, and reconcile rollback are fail-closed")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
