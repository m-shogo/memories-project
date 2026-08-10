#!/usr/bin/env python3
"""Validate structural hygiene of the canonical operability status ledger."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "contracts/operations/production-operability-status.json"
INVENTORY = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
BACKUP_BINDING = ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json"
CANONICAL_SCHEMA = "memory-os-operability-status.0.1"
INVENTORY_SCHEMA = "memory-os-operability-admission-inventory.v1"
SOAK_REVIEW_REFS = {
    "contracts/operations/sustained-soak-independent-review-contract.v1.json",
    "contracts/operations/sustained-soak-independent-review-registry.v1.json",
    "scripts/register-memory-os-sustained-soak-independent-review.py",
    "scripts/validate-memory-os-sustained-soak-independent-review.py",
    "scripts/validate-memory-os-sustained-soak-independent-review-negative.py",
}


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, ValueError) as exc:
        raise Fail(f"authority path escapes repository: {path}") from exc


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError) as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def unique_strings(value: Any, field: str) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(all(isinstance(item, str) and item.strip() for item in value), f"{field} contains empty/non-string value")
    require(len(value) == len(set(value)), f"{field} contains exact duplicates")
    return value


def main() -> int:
    status = load(STATUS)
    require(status.get("schemaVersion") == CANONICAL_SCHEMA, "status schema drift")
    require(status.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list) and areas, "areas missing")
    ids: set[str] = set()
    p0_count = 0
    p0_006: dict[str, Any] | None = None
    p0_007: dict[str, Any] | None = None
    for index, area in enumerate(areas):
        require(isinstance(area, dict), f"areas[{index}] invalid")
        area_id = area.get("id")
        require(isinstance(area_id, str) and area_id and area_id not in ids, f"areas[{index}].id invalid/duplicate")
        ids.add(area_id)
        if area_id == "OPS-P0-006":
            p0_006 = area
        if area_id == "OPS-P0-007":
            p0_007 = area
        if not area_id.startswith("OPS-P0-"):
            continue
        p0_count += 1
        existing = unique_strings(area.get("existingEvidence"), f"{area_id}.existingEvidence")
        missing = unique_strings(area.get("missingEvidence"), f"{area_id}.missingEvidence")
        refs = unique_strings(area.get("evidenceRefs"), f"{area_id}.evidenceRefs")
        require(not (set(existing) & set(missing)), f"{area_id} has the same statement in existingEvidence and missingEvidence")
        for ref in refs:
            relative = Path(ref)
            require(not relative.is_absolute() and ".." not in relative.parts, f"{area_id} unsafe evidence ref: {ref}")
            resolved_relative = repo_relative(ROOT / relative)
            require((ROOT / resolved_relative).is_file(), f"{area_id} evidence ref missing: {ref}")
            require("diagnostic.last.json" not in ref, f"{area_id} failure diagnostic cannot be canonical proof: {ref}")
        area_status = area.get("status")
        blocking = area.get("blocking")
        require(blocking is True, f"{area_id} is a P0 gate and must remain classified as blocking")
        if area_status == "READY":
            require(not missing, f"{area_id} READY cannot retain missingEvidence")
            require(existing and refs, f"{area_id} READY requires named evidence")
        else:
            require(missing, f"{area_id} incomplete status requires missingEvidence")

    require(p0_count >= 9, "unexpected P0 area count")
    require(p0_006 is not None, "OPS-P0-006 sustained-soak area missing")
    require(p0_007 is not None, "OPS-P0-007 backup/restore area missing")
    require_canonical_gaps(p0_007.get("missingEvidence"), Fail)

    inventory = load(INVENTORY)
    backup_binding = load(BACKUP_BINDING)
    require(inventory.get("schemaVersion") == INVENTORY_SCHEMA, "operability admission inventory schema drift")
    require(inventory.get("productionDecision") == "NO_GO", "inventory production decision must remain NO_GO")
    require(inventory.get("productionEvidence") is False, "inventory productionEvidence must remain false")
    require(inventory.get("productionReady") is False, "inventory productionReady must remain false")
    backup_independent_review = inventory.get("backupRestoreIndependentEvidenceReviewCompleted")
    require(isinstance(backup_independent_review, bool), "inventory backup/restore independent evidence review flag invalid")
    binding_boundary = backup_binding.get("currentBoundary")
    require(isinstance(binding_boundary, dict), "backup/restore generation binding currentBoundary missing")
    binding_backup_count = binding_boundary.get("generationBoundBackupCount")
    binding_restore_count = binding_boundary.get("generationBoundRestoreCount")
    binding_candidate_count = binding_boundary.get("productionEquivalentRecoveryCandidateCount")
    binding_independent_review = binding_boundary.get("independentReviewCompleted")
    require(isinstance(binding_backup_count, int) and not isinstance(binding_backup_count, bool) and binding_backup_count >= 0, "backup/restore generation binding backup count invalid")
    require(isinstance(binding_restore_count, int) and not isinstance(binding_restore_count, bool) and binding_restore_count >= 0, "backup/restore generation binding restore count invalid")
    require(binding_restore_count <= binding_backup_count, "backup/restore generation binding restore count exceeds backup count")
    require(isinstance(binding_candidate_count, int) and not isinstance(binding_candidate_count, bool) and binding_candidate_count >= 0, "backup/restore generation binding candidate count invalid")
    require(binding_candidate_count <= binding_restore_count, "backup/restore generation binding candidate count exceeds complete restore count")
    require(isinstance(binding_independent_review, bool), "backup/restore generation binding independent review flag invalid")
    require(binding_independent_review is (binding_candidate_count > 0), "backup/restore generation binding candidate/review authority drift")
    require(backup_independent_review is binding_independent_review, "inventory backup/restore independent evidence review drift from generation binding authority")
    require(inventory.get("humanProductionPromotionReviewCompleted") is False, "inventory cannot manufacture human production-promotion review")
    require(inventory.get("humanProductionPromotionAuthorized") is False, "inventory cannot authorize human production promotion")

    inventory_areas = inventory.get("areas")
    require(isinstance(inventory_areas, list), "inventory areas missing")
    inventory_p0_006 = next((area for area in inventory_areas if isinstance(area, dict) and area.get("id") == "OPS-P0-006"), None)
    inventory_p0_007 = next((area for area in inventory_areas if isinstance(area, dict) and area.get("id") == "OPS-P0-007"), None)
    require(isinstance(inventory_p0_006, dict), "inventory OPS-P0-006 missing")
    require(isinstance(inventory_p0_007, dict), "inventory OPS-P0-007 missing")

    approved_criteria = inventory.get("approvedLeakStabilityCriteriaCount")
    passing_reviews = inventory.get("passingIndependentSustainedSoakReviewCount")
    leak_proof = inventory.get("sustainedSoakLeakProof")
    require(isinstance(approved_criteria, int) and not isinstance(approved_criteria, bool) and approved_criteria >= 0, "OPS-P0-006 approved criteria count invalid")
    require(isinstance(passing_reviews, int) and not isinstance(passing_reviews, bool) and 0 <= passing_reviews <= 1, "OPS-P0-006 current independent review count invalid")
    require(passing_reviews <= approved_criteria, "OPS-P0-006 current independent review count exceeds approved criteria authority")
    require(isinstance(leak_proof, bool), "OPS-P0-006 leak proof invalid")
    require(not leak_proof or passing_reviews > 0, "OPS-P0-006 leak proof requires a passing independent review")
    require(inventory_p0_006.get("approvedLeakStabilityCriteriaCount") == approved_criteria, "OPS-P0-006 row/top-level approved criteria drift")
    require(inventory_p0_006.get("passingIndependentReviewCount") == passing_reviews, "OPS-P0-006 row/top-level independent review drift")
    require(inventory_p0_006.get("leakProof") is leak_proof, "OPS-P0-006 row/top-level leak proof drift")
    require(inventory_p0_006.get("blocking") is True, "OPS-P0-006 inventory must remain blocking")
    require(inventory_p0_006.get("status") == p0_006.get("status"), "OPS-P0-006 status/inventory status drift")
    soak_deps = inventory_p0_006.get("dependencyCounts")
    require(isinstance(soak_deps, dict), "OPS-P0-006 inventory dependencyCounts missing")
    require(soak_deps.get("approvedLeakStabilityCriteria") == approved_criteria, "OPS-P0-006 approved criteria dependency drift")
    require(soak_deps.get("passingIndependentReviews") == passing_reviews, "OPS-P0-006 independent review dependency drift")
    require(isinstance(soak_deps.get("localSustainedSoakEvidence"), bool), "OPS-P0-006 local sustained-soak flag invalid")
    if soak_deps.get("localSustainedSoakEvidence") is True and (approved_criteria == 0 or passing_reviews == 0):
        require(leak_proof is False, "local sustained-soak evidence alone cannot establish leak proof")

    soak_existing = p0_006.get("existingEvidence")
    soak_missing = p0_006.get("missingEvidence")
    soak_refs = p0_006.get("evidenceRefs")
    require(isinstance(soak_existing, list), "OPS-P0-006 existingEvidence missing")
    require(isinstance(soak_missing, list), "OPS-P0-006 missingEvidence missing")
    require(isinstance(soak_refs, list), "OPS-P0-006 evidenceRefs missing")
    require(SOAK_REVIEW_REFS.issubset(set(soak_refs)), "OPS-P0-006 must retain independent sustained-soak review authority refs")
    require(any(
        isinstance(item, str)
        and "append-only independent sustained-soak review authority" in item
        and "accepts only externally supplied human-approved" in item
        and "automatic threshold selection" in item
        and "registry is currently empty" not in item
        for item in soak_existing
    ), "OPS-P0-006 must describe stable independent review authority without embedding transient registry emptiness")
    require(not any(
        isinstance(item, str)
        and "append-only independent sustained-soak review authority" in item
        and "registry is currently empty" in item
        for item in soak_existing
    ), "OPS-P0-006 cannot retain stale dynamic empty-registry evidence")
    if approved_criteria == 0 or passing_reviews == 0:
        require(any(
            isinstance(item, str)
            and "independently approved leak/stability criteria" in item
            and "leakProof remains false" in item
            for item in soak_missing
        ), "OPS-P0-006 must preserve the independent leak/stability review blocker while current review authority is absent")

    require(inventory_p0_007.get("independentEvidenceReviewCompleted") is backup_independent_review, "OPS-P0-007 row/top-level independent evidence review drift")
    require(inventory_p0_007.get("humanProductionPromotionReviewCompleted") is False, "OPS-P0-007 inventory cannot manufacture promotion review")
    require(inventory_p0_007.get("humanProductionPromotionAuthorized") is False, "OPS-P0-007 inventory cannot authorize promotion")
    require(inventory_p0_007.get("blocking") is True, "OPS-P0-007 inventory must remain blocking")
    require(inventory_p0_007.get("status") == p0_007.get("status"), "OPS-P0-007 status/inventory status drift")

    counts = inventory_p0_007.get("dependencyCounts")
    require(isinstance(counts, dict), "OPS-P0-007 inventory dependencyCounts missing")
    registered = counts.get("environmentGenerations")
    semantic = counts.get("preflightEligibleEnvironmentGenerations")
    unsuperseded_registered = counts.get("unsupersededEnvironmentGenerations")
    unsuperseded_semantic = counts.get("unsupersededPreflightEligibleEnvironmentGenerations")
    distinct_semantic = counts.get("distinctUnsupersededPreflightEligibleEnvironments")
    generation_bound_backups = counts.get("generationBoundBackups")
    generation_bound_restores = counts.get("generationBoundRestores")
    candidate_count = counts.get("productionEquivalentRecoveryCandidates")
    require(all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in (registered, semantic, unsuperseded_registered, unsuperseded_semantic, distinct_semantic, generation_bound_backups, generation_bound_restores, candidate_count)), "OPS-P0-007 dependency counts invalid")
    require(semantic <= registered, "semantic preflight-eligible generation count exceeds registered count")
    require(unsuperseded_registered <= registered, "unsuperseded generation count exceeds registered count")
    require(unsuperseded_semantic <= semantic, "unsuperseded semantic generation count exceeds semantic count")
    require(unsuperseded_semantic <= unsuperseded_registered, "unsuperseded semantic generation count exceeds unsuperseded registered count")
    require(distinct_semantic <= unsuperseded_semantic, "distinct semantic environment count exceeds eligible generations")
    require(generation_bound_backups == binding_backup_count, "OPS-P0-007 generation-bound backup count drift from generation binding authority")
    require(generation_bound_restores == binding_restore_count, "OPS-P0-007 generation-bound restore count drift from generation binding authority")
    require(candidate_count == binding_candidate_count, "OPS-P0-007 candidate count drift from generation binding authority")
    require(candidate_count <= generation_bound_restores, "OPS-P0-007 recovery candidates exceed complete generation-bound restores")
    require(backup_independent_review is (candidate_count > 0), "OPS-P0-007 candidate/review projection drift")

    existing = p0_007.get("existingEvidence")
    require(isinstance(existing, list), "OPS-P0-007 existingEvidence missing")
    require(any(isinstance(item, str) and "registered generation inventory alone" in item and "restore-planning authority" in item for item in existing), "OPS-P0-007 must state that registered generation inventory alone creates no restore-planning authority")
    require(any(isinstance(item, str) and "human production-promotion review" in item and "separate non-automatic decision" in item for item in existing), "OPS-P0-007 must preserve separate non-automatic human promotion review")
    require(any(isinstance(item, str) and "human production-promotion review/authorization=false/false" in item for item in existing), "OPS-P0-007 must expose current false/false human promotion authority")

    print("Memory OS operability status hygiene validation PASS")
    print(f"status schema: {CANONICAL_SCHEMA}")
    print(f"P0 areas checked: {p0_count}")
    print(f"OPS-P0-006 approved criteria/current independent review/leak proof: {approved_criteria}/{passing_reviews}/{str(leak_proof).lower()}")
    print("OPS-P0-006 independent review authority refs: bound to canonical status")
    print("OPS-P0-006 stale empty-registry authority text accepted: false")
    print("OPS-P0-006 local soak cannot manufacture independent leak proof: true")
    print("OPS-P0-007 canonical production blockers: exact shared authority")
    print("OPS-P0-007 semantic generation authority: bound to deterministic inventory")
    print("OPS-P0-007 backup/restore/candidate counts: bound to generation binding authority")
    print("OPS-P0-007 candidate count/review authority: bound to generation binding, top-level inventory and area row")
    print("OPS-P0-007 human production-promotion authority: separate and false")
    print("exact duplicate authority entries: none")
    print("failure diagnostics referenced as proof: none")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY STATUS HYGIENE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
