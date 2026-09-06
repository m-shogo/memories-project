#!/usr/bin/env python3
"""Negative checks for semantic local sustained-soak operability admission."""

from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/validate-memory-os-operability.py"
SOAK_PATH = ROOT / "contracts/operations/sustained-local-soak-contract.v1.json"
POSTGRES_PATH = ROOT / "contracts/operations/live-postgres-load-scenario-contract.v1.json"
OBJECT_PATH = ROOT / "contracts/operations/live-object-load-scenario-contract.v1.json"

SPEC = importlib.util.spec_from_file_location("memory_os_operability", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("OPERABILITY LOCAL SOAK NEGATIVE FAILED: cannot load operability validator")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def copy_authority(source: Path, repo_root: Path, relative: Path) -> None:
    target = repo_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def pending_soak_contract() -> dict:
    contract = json.loads(SOAK_PATH.read_text(encoding="utf-8"))
    readiness = contract["readiness"]
    readiness["trendReviewCompleted"] = False
    readiness["localSustainedSoakEvidence"] = False
    for claim in (
        "productionSustainedSoakEvidence",
        "leakProofAvailable",
        "productionReady",
    ):
        readiness[claim] = False
    return contract


def validate_pending(repo_root: Path, contract: dict) -> None:
    copy_authority(
        POSTGRES_PATH,
        repo_root,
        module.LIVE_POSTGRES_CONTRACT_PATH,
    )
    copy_authority(
        OBJECT_PATH,
        repo_root,
        module.LIVE_OBJECT_CONTRACT_PATH,
    )
    write_json(repo_root / module.LONG_SOAK_CONTRACT_PATH, contract)

    refs = sorted(
        module.LIVE_LOAD_FOUNDATION_REFS
        | {module.LONG_SOAK_CONTRACT_PATH.as_posix()}
    )
    existing = [
        "live PostgreSQL local checkpoint",
        "live MinIO local checkpoint",
    ]
    # Deliberately omit any wording such as "sustained soak". Pending admission
    # must be derived from the typed readiness authority, not prose matching.
    missing = [
        "capacity boundary remains unproven",
        "production-equivalent dependencies remain unproven",
        "additional local stability evidence remains under review",
    ]
    area = {"status": "PARTIAL"}
    module.validate_load_gate(repo_root, area, existing, missing, refs)


def expect_semantic_reject(label: str, mutate) -> None:
    contract = pending_soak_contract()
    mutate(contract["readiness"])
    with tempfile.TemporaryDirectory(prefix="memory-os-operability-soak-negative-") as tmp:
        try:
            validate_pending(Path(tmp), contract)
        except module.ValidationFailure as exc:
            expected = "incomplete local sustained-soak authority must remain semantically pending"
            if expected not in str(exc):
                raise AssertionError(f"unexpected rejection for {label}: {exc}") from exc
        else:
            raise AssertionError(f"semantic corruption accepted: {label}")
    print(f"PASS reject: {label}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="memory-os-operability-soak-pending-") as tmp:
        validate_pending(Path(tmp), pending_soak_contract())
    print("PASS semantic pending state without prose coupling")

    expect_semantic_reject(
        "production sustained-soak evidence manufactured",
        lambda readiness: readiness.__setitem__("productionSustainedSoakEvidence", True),
    )
    expect_semantic_reject(
        "leak proof manufactured",
        lambda readiness: readiness.__setitem__("leakProofAvailable", True),
    )
    expect_semantic_reject(
        "production readiness manufactured",
        lambda readiness: readiness.__setitem__("productionReady", True),
    )
    expect_semantic_reject(
        "production readiness omitted",
        lambda readiness: readiness.pop("productionReady"),
    )

    print("Memory OS operability local-soak semantic negative suite PASS")
    print("pending state depends on typed readiness authority: true")
    print("pending state depends on missingEvidence prose: false")
    print("production sustained-soak promotion accepted: false")
    print("leak-proof promotion accepted: false")
    print("production readiness promotion accepted: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
