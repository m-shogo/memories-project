#!/usr/bin/env python3
"""Register backup/restore generation binding in the correct operability area.

This also repairs historical misclassification where this reconciler appended
restore-generation evidence to OPS-P0-003 (observability) instead of OPS-P0-007
(backup_restore), and normalizes the duplicated backup/restore blocker list.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py"
BACKUP_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"

EVIDENCE = (
    "future production-equivalent restore promotion is generation-bound: backup artifact/manifest hashes, source environment generation/manifest, "
    "source commit, restore target generation/manifest and restore evidence bundle must match append-only registered generations; legacy local restore "
    "evidence cannot be relabeled, cross-generation restores require material-delta review, candidate-level independent evidence review remains required, "
    "and human production-promotion review remains a separate non-automatic decision"
)
REFS = (
    "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    "scripts/validate-memory-os-backup-restore-generation-binding.py",
    ".github/workflows/backup-restore-generation-binding.yml",
    "contracts/operations/production-equivalent-environment-generation-contract.v1.json",
    "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
)
CANONICAL_MISSING = [
    "production PostgreSQL backup and PITR schedule with encrypted independent retention, WAL continuity and tested point-in-time recovery selection",
    "production independent object backup retention with TLS, restore-only credential separation, deletion protection, immutability, lifecycle controls and provider durability evidence",
    "approved and measured RPO and RTO under production-shaped recovery, with coherent PostgreSQL/object recovery-point skew measurement plus backup monitoring, freshness enforcement and paging",
    "production-shaped cross-cluster isolated restore drill with an approved recovery owner, coherent PostgreSQL and exact object-version recovery points, and an explicit promotion decision",
    "production deletion, expired/revoked-session, replay, idempotency and lease non-resurrection verification after restore",
    "independent review of generation-bound recovery evidence, security/privacy invariants, measured objectives and the restore promotion decision",
]


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"root must be object: {path.relative_to(ROOT)}")
    return value


def append_once(items: list[Any], value: str) -> None:
    if value not in items:
        items.append(value)


def main() -> int:
    subprocess.run(["python", str(VALIDATOR)], cwd=ROOT, check=True)
    contract = load(CONTRACT)
    boundary = contract.get("currentBoundary", {})
    generation_count = boundary.get("registeredProductionEquivalentGenerationCount")
    backup_count = boundary.get("generationBoundBackupCount")
    restore_count = boundary.get("generationBoundRestoreCount")
    candidate_count = boundary.get("productionEquivalentRecoveryCandidateCount")
    for value, field in (
        (generation_count, "registeredProductionEquivalentGenerationCount"),
        (backup_count, "generationBoundBackupCount"),
        (restore_count, "generationBoundRestoreCount"),
        (candidate_count, "productionEquivalentRecoveryCandidateCount"),
    ):
        if not isinstance(value, int) or value < 0:
            raise SystemExit(f"invalid restore generation boundary count: {field}")
    if not (candidate_count <= restore_count <= backup_count):
        raise SystemExit("restore generation boundary count ordering drift")
    if boundary.get("productionEquivalentRestoreEvidence") is not (candidate_count > 0):
        raise SystemExit("production-equivalent restore evidence derivation drift")
    if boundary.get("independentReviewCompleted") is not (candidate_count > 0):
        raise SystemExit("candidate-level independent evidence review derivation drift")
    for key in ("humanProductionPromotionReviewCompleted", "humanProductionPromotionAuthorized", "productionEvidence", "productionReady"):
        if boundary.get(key) is not False:
            raise SystemExit(f"restore foundation cannot enable {key}")
    if boundary.get("productionDecision") != "NO_GO":
        raise SystemExit("restore foundation cannot change production decision")

    status = load(STATUS)
    if status.get("productionDecision") != "NO_GO":
        raise SystemExit("productionDecision must remain NO_GO")
    areas = status.get("areas")
    if not isinstance(areas, list):
        raise SystemExit("operability areas missing")
    observability = next((item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-003"), None)
    backup = next((item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    if not isinstance(observability, dict) or not isinstance(backup, dict):
        raise SystemExit("OPS-P0-003 or OPS-P0-007 missing")
    if backup.get("status") not in {"PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"} or backup.get("blocking") is not True:
        raise SystemExit("OPS-P0-007 must remain blocking and incomplete")

    # Repair historical misclassification if the old reconciler ever wrote to
    # observability. Do not remove any unrelated observability authority.
    obs_existing = observability.get("existingEvidence")
    obs_refs = observability.get("evidenceRefs")
    if not isinstance(obs_existing, list) or not isinstance(obs_refs, list):
        raise SystemExit("OPS-P0-003 authority arrays missing")
    observability["existingEvidence"] = [item for item in obs_existing if item != EVIDENCE]
    observability["evidenceRefs"] = [ref for ref in obs_refs if ref not in set(REFS)]

    existing = backup.get("existingEvidence")
    refs = backup.get("evidenceRefs")
    if not isinstance(existing, list) or not isinstance(refs, list):
        raise SystemExit("OPS-P0-007 authority arrays missing")
    # Replace older wording for this authority without touching unrelated evidence.
    prefix = "future production-equivalent restore promotion is generation-bound:"
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(prefix))]
    append_once(existing, EVIDENCE)
    for ref in REFS:
        if not (ROOT / ref).is_file():
            raise SystemExit(f"missing restore-generation ref: {ref}")
        append_once(refs, ref)
    backup["missingEvidence"] = list(CANONICAL_MISSING)

    joined = "\n".join(CANONICAL_MISSING)
    for term in (
        "PostgreSQL backup and PITR",
        "independent object",
        "RPO and RTO",
        "isolated restore",
        "non-resurrection",
        "restore drill",
        "backup monitoring",
        "independent review",
    ):
        if term not in joined:
            raise SystemExit(f"canonical backup blocker missing validator term: {term}")

    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(["python", str(BACKUP_VALIDATOR)], cwd=ROOT, check=True)
    print("Memory OS backup/restore generation status reconciliation PASS")
    print("misclassified OPS-P0-003 restore evidence: removed")
    print("generation binding foundation: registered under OPS-P0-007")
    print(f"production-equivalent recovery candidates: {candidate_count}")
    print(f"candidate-level independent evidence review complete: {str(candidate_count > 0).lower()}")
    print("human production-promotion review completed: false")
    print("human production promotion authorized: false")
    print("backup/restore blocker list: normalized")
    print("OPS-P0-007: incomplete")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
