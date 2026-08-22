#!/usr/bin/env python3
"""Register backup/restore generation binding in the correct operability area.

This also repairs historical misclassification where this reconciler appended
restore-generation evidence to OPS-P0-003 (observability) instead of OPS-P0-007
(backup_restore). Canonical production blockers are validation-only authority
here and are never rewritten by this generation-binding layer.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-generation-binding-contract.v1.json")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-generation-binding.py")
BACKUP_VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
VALIDATOR = ROOT / VALIDATOR_REL
BACKUP_VALIDATOR = ROOT / BACKUP_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL

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


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"authority path escapes repository: {path}") from exc


def require_repo_file(path: Path, message: str) -> Path:
    relative = repo_relative(path)
    require((ROOT / relative).is_file(), message)
    return relative


def require_exact_repo_file(path: Path, expected_relative: Path, message: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{message} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{message} authority drift",
    )
    return expected_relative


def enforce_runtime_authorities() -> None:
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "generation binding contract"),
        (VALIDATOR, VALIDATOR_REL, "generation binding validator"),
        (BACKUP_VALIDATOR, BACKUP_VALIDATOR_REL, "backup validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (STATUS, STATUS_REL, "production operability status"),
    ):
        require_exact_repo_file(path, expected, field)


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def append_once(items: list[Any], value: str) -> None:
    if value not in items:
        items.append(value)


def run_validator(path: Path, expected_relative: Path, label: str) -> None:
    relative = require_exact_repo_file(path, expected_relative, label)
    completed = subprocess.run([sys.executable, str(ROOT / relative)], cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise Fail(f"{label} failed with exit code {completed.returncode}")


def main() -> int:
    enforce_runtime_authorities()
    run_validator(VALIDATOR, VALIDATOR_REL, "generation binding validator")

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
        require(valid_count(value), f"invalid restore generation boundary count: {field}")
    require(candidate_count <= restore_count <= backup_count, "restore generation boundary count ordering drift")
    require(boundary.get("productionEquivalentRestoreEvidence") is (candidate_count > 0), "production-equivalent restore evidence derivation drift")
    require(boundary.get("independentReviewCompleted") is (candidate_count > 0), "candidate-level independent evidence review derivation drift")
    for key in ("humanProductionPromotionReviewCompleted", "humanProductionPromotionAuthorized", "productionEvidence", "productionReady"):
        require(boundary.get(key) is False, f"restore foundation cannot enable {key}")
    require(boundary.get("productionDecision") == "NO_GO", "restore foundation cannot change production decision")

    status = load(STATUS)
    require(status.get("productionDecision") == "NO_GO", "productionDecision must remain NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "operability areas missing")
    observability = next((item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-003"), None)
    backup = next((item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(observability, dict) and isinstance(backup, dict), "OPS-P0-003 or OPS-P0-007 missing")
    require(backup.get("status") in {"PARTIAL_FOUNDATIONS_ONLY", "PARTIAL"} and backup.get("blocking") is True, "OPS-P0-007 must remain blocking and incomplete")
    require_canonical_gaps(backup.get("missingEvidence"), Fail)

    obs_existing = observability.get("existingEvidence")
    obs_refs = observability.get("evidenceRefs")
    require(isinstance(obs_existing, list) and isinstance(obs_refs, list), "OPS-P0-003 authority arrays missing")
    observability["existingEvidence"] = [item for item in obs_existing if item != EVIDENCE]
    observability["evidenceRefs"] = [ref for ref in obs_refs if ref not in set(REFS)]

    existing = backup.get("existingEvidence")
    refs = backup.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(refs, list), "OPS-P0-007 authority arrays missing")
    prefix = "future production-equivalent restore promotion is generation-bound:"
    existing[:] = [item for item in existing if not (isinstance(item, str) and item.startswith(prefix))]
    append_once(existing, EVIDENCE)
    for ref in REFS:
        ref_path = Path(ref)
        require(not ref_path.is_absolute() and ".." not in ref_path.parts, f"restore-generation ref must be canonical repository-relative path: {ref}")
        relative = require_repo_file(ROOT / ref_path, f"missing restore-generation ref: {ref}")
        require(relative == ref_path, f"restore-generation ref resolution drift: {ref}")
        append_once(refs, ref)

    require_canonical_gaps(backup.get("missingEvidence"), Fail)
    require(status.get("productionDecision") == "NO_GO", "productionDecision changed unexpectedly")
    original_status = STATUS.read_bytes()
    try:
        STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        run_validator(BACKUP_VALIDATOR, BACKUP_VALIDATOR_REL, "backup validator")
        run_validator(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    except Exception:
        STATUS.write_bytes(original_status)
        raise

    print("Memory OS backup/restore generation status reconciliation PASS")
    print("misclassified OPS-P0-003 restore evidence: removed")
    print("generation binding foundation: registered under OPS-P0-007")
    print(f"production-equivalent recovery candidates: {candidate_count}")
    print(f"candidate-level independent evidence review complete: {str(candidate_count > 0).lower()}")
    print("human production-promotion review completed: false")
    print("human production promotion authorized: false")
    print("canonical generation-status data/executable authorities enforced: true")
    print("canonical backup/restore blockers rewritten by this layer: false")
    print("OPS-P0-007: incomplete")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE GENERATION STATUS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
