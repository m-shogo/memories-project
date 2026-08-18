#!/usr/bin/env python3
"""Pin transactional rollback and deterministic gap projection for release compatibility pair reconciliation."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-release-compatibility-pair.py"
CONTRACT = ROOT / "contracts/operations/release-compatibility-pair-contract.v1.json"
GAPS = ROOT / "contracts/operations/compatibility-admission-gaps.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_release_pair_reconcile_negative", RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load release pair reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "CONTRACT", None) == CONTRACT, "reconciler contract authority drift")
    require(getattr(module, "GAPS", None) == GAPS, "reconciler gaps authority drift")
    require(getattr(module, "STATUS", None) == STATUS, "reconciler status authority drift")
    return module


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def fail_post_write() -> None:
    raise RuntimeError("synthetic post-write validator failure")


def validate_gap_projection(reconciler: ModuleType) -> None:
    gaps = [
        {
            "id": "COMPAT-GAP-APPROVED-RELEASE-PAIR",
            "blocking": True,
            "current": 2,
            "requiredMinimum": 2,
        },
        {
            "id": "COMPAT-GAP-ROLLBACK-PAIR",
            "blocking": True,
            "current": 1,
            "requiredMinimum": 1,
        },
        {
            "id": "COMPAT-GAP-ROLLING-DEPLOYMENT",
            "blocking": True,
            "current": False,
            "required": True,
        },
    ]
    reconciler.remove_satisfied_pair_count_gaps(gaps)
    require([gap.get("id") for gap in gaps] == ["COMPAT-GAP-ROLLING-DEPLOYMENT"],
            "satisfied release/pair count gaps were not removed deterministically")

    unsatisfied = [
        {
            "id": "COMPAT-GAP-APPROVED-RELEASE-PAIR",
            "blocking": True,
            "current": 1,
            "requiredMinimum": 2,
        },
        {
            "id": "COMPAT-GAP-ROLLBACK-PAIR",
            "blocking": True,
            "current": 0,
            "requiredMinimum": 1,
        },
    ]
    reconciler.remove_satisfied_pair_count_gaps(unsatisfied)
    require(len(unsatisfied) == 2,
            "unsatisfied release/pair count gaps were removed")


def main() -> int:
    reconciler = load_module()
    validate_gap_projection(reconciler)
    originals = {path: path.read_bytes() for path in (CONTRACT, GAPS, STATUS)}

    contract = copy.deepcopy(load(CONTRACT))
    gaps = copy.deepcopy(load(GAPS))
    status = copy.deepcopy(load(STATUS))

    authority = contract.get("currentAuthority")
    require(isinstance(authority, dict), "pair currentAuthority missing")
    authority["latestPairId"] = "rcp_transaction_rollback_probe"
    gaps["releaseCompatibilityEvidence"] = not bool(gaps.get("releaseCompatibilityEvidence"))
    gate = next(
        (item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-008"),
        None,
    )
    require(isinstance(gate, dict), "OPS-P0-008 missing")
    existing = gate.get("existingEvidence")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence missing")
    existing.append("synthetic release-pair rollback probe")

    try:
        reconciler.commit_authority_transaction(
            contract,
            gaps,
            status,
            validator_runner=fail_post_write,
        )
    except RuntimeError as exc:
        require("synthetic post-write validator failure" in str(exc), "unexpected rollback failure reason")
    else:
        raise Fail("release pair reconcile accepted synthetic post-write validation failure")

    for path, payload in originals.items():
        require(path.read_bytes() == payload, f"partial release-pair authority write survived rollback: {path.relative_to(ROOT)}")

    print("PASS: release compatibility pair gap projection is monotonic and reconcile rollback is transactional")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR RECONCILE NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
