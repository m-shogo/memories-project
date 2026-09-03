#!/usr/bin/env python3
"""Negative proof for mixed-version Apply authority identity and transaction."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-mixed-version-apply.py"


def load_module():
    spec = importlib.util.spec_from_file_location("memory_os_mixed_version_apply_reconcile_negative", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load mixed-version Apply reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_authority_rejection(module, attr: str, replacement: Path) -> None:
    original = getattr(module, attr)
    setattr(module, attr, replacement)
    try:
        try:
            module.enforce_runtime_authorities()
        except module.ReconcileFailure:
            pass
        else:
            raise RuntimeError(f"mixed-version Apply {attr} substitution must be rejected")
    finally:
        setattr(module, attr, original)


def main() -> int:
    module = load_module()
    original_contract = module.CONTRACT_PATH.read_bytes()
    original_status = module.STATUS_PATH.read_bytes()
    expect_authority_rejection(module, "CONTRACT_PATH", module.STATUS_PATH)
    expect_authority_rejection(module, "RESULT_PATH", module.CONTRACT_PATH)
    expect_authority_rejection(module, "STATUS_PATH", module.RESULT_PATH)
    expect_authority_rejection(module, "APPLY_VALIDATOR", module.VERSION_VALIDATOR)
    expect_authority_rejection(module, "VERSION_VALIDATOR", module.OPERABILITY_VALIDATOR)
    expect_authority_rejection(module, "OPERABILITY_VALIDATOR", module.APPLY_VALIDATOR)
    if module.CONTRACT_PATH.read_bytes() != original_contract or module.STATUS_PATH.read_bytes() != original_status:
        raise RuntimeError("mixed-version Apply substitution changed canonical authority")

    current_sha = "1" * 40
    old_sha = "0" * 40
    with tempfile.TemporaryDirectory(prefix="memory-os-mixed-version-apply-negative-") as tmp:
        root = Path(tmp)
        result_path = root / "result.json"
        contract_path = root / "contract.json"
        status_path = root / "status.json"
        result = {
            "currentCommitSha": current_sha,
            "oldBackendCommitSha": old_sha,
            "assertions": {
                "concurrentOldCurrentClaimRacePassed": True,
                "oldProcessTerminationRecoveryPassed": True,
            },
        }
        contract = {
            "readiness": {
                "exactSourcePassResultCommitted": False,
                "concurrentClaimRaceExecuted": False,
                "inProgressProcessTerminationExecuted": False,
                "approvedReleasePairAvailable": False,
                "rollbackRehearsalExecuted": False,
                "productionReady": False,
            },
            "evidenceRefs": [],
        }
        status = {
            "productionDecision": "NO_GO",
            "areas": [
                {
                    "id": "OPS-P0-008",
                    "status": "PARTIAL",
                    "existingEvidence": [],
                    "missingEvidence": [
                        "old/current backend mixed-version executable tests against an expanded schema",
                        "approved predecessor successor release pair",
                        "approved-release concurrent idempotency traffic",
                        "approved-release termination in-progress evidence",
                        "rolling rollback rollback-eligible evidence",
                        "parser artifact compatibility evidence",
                        "client/server compatibility evidence",
                        "PostgreSQL compatibility evidence",
                    ],
                    "evidenceRefs": [],
                }
            ],
        }
        result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
        contract_bytes = json.dumps(contract, indent=2).encode("utf-8") + b"\n"
        status_bytes = json.dumps(status, indent=2).encode("utf-8") + b"\n"
        contract_path.write_bytes(contract_bytes)
        status_path.write_bytes(status_bytes)

        # The rollback transaction fixture intentionally lives outside the
        # repository. Point diagnostic path rendering at that fixture root
        # after canonical authority-substitution checks have already passed.
        module.ROOT = root
        module.RESULT_PATH = result_path
        module.CONTRACT_PATH = contract_path
        module.STATUS_PATH = status_path
        module.enforce_runtime_authorities = lambda: None
        module.is_ancestor = lambda _base, _head: True
        module.REFS = ()

        calls: list[tuple[str, bool]] = []

        def reject_after_write(validated_sha: str, *, require_reconciled: bool) -> None:
            calls.append((validated_sha, require_reconciled))
            if len(calls) == 2:
                raise module.ReconcileFailure("synthetic post-write aggregate rejection")

        module.validate_authority_chain = reject_after_write
        try:
            module.main()
        except module.ReconcileFailure as exc:
            if "synthetic post-write aggregate rejection" not in str(exc):
                raise RuntimeError(f"unexpected mixed-version Apply rejection: {exc}") from exc
        else:
            raise RuntimeError("mixed-version Apply reconcile accepted post-write aggregate rejection")

        if calls != [(current_sha, False), (current_sha, True)]:
            raise RuntimeError(f"mixed-version Apply validator order drift: {calls}")
        if contract_path.read_bytes() != contract_bytes:
            raise RuntimeError("mixed-version Apply reconcile did not roll back contract")
        if status_path.read_bytes() != status_bytes:
            raise RuntimeError("mixed-version Apply reconcile did not roll back Production Status")

    print("PASS: mixed-version Apply exact authority and reconcile rollback are fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
