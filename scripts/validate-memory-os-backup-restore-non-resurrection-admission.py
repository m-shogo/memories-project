#!/usr/bin/env python3
"""Validate typed non-resurrection coverage for generation-bound restore admission."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
WRITER = ROOT / "scripts/register-memory-os-backup-restore-non-resurrection-evidence.py"
NEGATIVE = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-negative.py"
LOCAL_APPLE_VALIDATOR = ROOT / "scripts/validate-memory-os-local-apple-replay-restore.py"
LOCAL_COHERENT_VALIDATOR = ROOT / "scripts/validate-memory-os-local-coherent-recovery-set.py"

class Fail(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)

def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_validator(path: Path, label: str) -> None:
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"{label} failed:\n{completed.stdout[-3000:]}{completed.stderr[-3000:]}")

def main() -> int:
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generation_registry = load(GEN_REGISTRY)
    writer = load_module(WRITER, "memory_os_non_resurrection_writer")
    generation_writer = load_module(GEN_WRITER, "memory_os_generation_recovery_writer_overlay")

    require(contract.get("schemaVersion") == "memory-os-backup-restore-non-resurrection-admission.v1", "contract schema drift")
    for field in ("registry", "generationEvidenceRegistry", "writer", "validator", "negativeAdmissionValidator", "reconcile", "workflow"):
        ref = contract.get(field)
        require(isinstance(ref, str) and ref and (ROOT / ref).is_file(), f"contract artifact missing: {field}")
    rules = contract.get("recordRules")
    require(isinstance(rules, dict) and rules and all(value is True for value in rules.values()), "recordRules must remain fail-closed")
    coverage_rule = contract.get("candidateCoverageRule")
    require(isinstance(coverage_rule, dict) and coverage_rule and all(value is True for value in coverage_rule.values()), "candidateCoverageRule drift")
    required_domains = contract.get("requiredDomains")
    require(isinstance(required_domains, list) and len(required_domains) == 8 and len(required_domains) == len(set(required_domains)), "requiredDomains drift")

    local = contract.get("localFoundationEvidence")
    require(isinstance(local, dict), "localFoundationEvidence missing")
    require(local.get("localEvidenceMaySatisfyProductionEquivalentTypedRecord") is False, "local evidence cannot satisfy production-equivalent typed record")
    for key in ("appleReplayRestoreContract", "appleReplayRestoreResult", "coherentRecoverySetContract", "coherentRecoverySetResult"):
        ref = local.get(key)
        require(isinstance(ref, str) and (ROOT / ref).is_file(), f"local foundation missing: {key}")
    run_validator(LOCAL_APPLE_VALIDATOR, "local Apple replay restore validator")
    run_validator(LOCAL_COHERENT_VALIDATOR, "local coherent recovery-set validator")

    require(registry.get("schemaVersion") == "memory-os-backup-restore-non-resurrection-admission-registry.v1", "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    require(registry.get("productionEvidence") is False and registry.get("productionReady") is False, "registry production boundary drift")
    rows = registry.get("records")
    count = registry.get("registeredRecordCount")
    complete_count = registry.get("completeRecordCount")
    covered_count = registry.get("candidateCoveredCount")
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "typed registry records invalid")
    require(isinstance(count, int) and count == len(rows), "registeredRecordCount drift")
    ids: set[str] = set()
    generation_ids: set[str] = set()
    for row in rows:
        writer.validate_record(row)
        record_id = row.get("recordId")
        generation_id = row.get("generationEvidenceId")
        require(isinstance(record_id, str) and record_id not in ids, f"duplicate recordId: {record_id}")
        require(isinstance(generation_id, str) and generation_id not in generation_ids, f"duplicate typed coverage for generation evidence: {generation_id}")
        ids.add(record_id)
        generation_ids.add(generation_id)
    derived_complete = sum(1 for row in rows if row.get("evidenceComplete") is True)
    require(complete_count == derived_complete, "completeRecordCount drift")

    generation_rows = generation_registry.get("records")
    require(isinstance(generation_rows, list) and all(isinstance(row, dict) for row in generation_rows), "generation recovery registry records invalid")
    base_candidate_ids = {row.get("evidenceId") for row in generation_rows if generation_writer.base_candidate(row)}
    final_candidate_ids = {row.get("evidenceId") for row in generation_rows if generation_writer.candidate(row)}
    require(None not in base_candidate_ids and None not in final_candidate_ids, "candidate evidenceId missing")
    complete_typed_ids = {row.get("generationEvidenceId") for row in rows if row.get("evidenceComplete") is True}
    covered_base_ids = base_candidate_ids & complete_typed_ids
    pending_typed_ids = base_candidate_ids - complete_typed_ids
    require(final_candidate_ids == covered_base_ids, "final candidate derivation bypasses typed non-resurrection coverage")
    require(isinstance(covered_count, int) and covered_count == len(covered_base_ids), "candidateCoveredCount drift")
    require(generation_registry.get("productionEquivalentRecoveryCandidateCount") == len(final_candidate_ids), "generation registry final candidate count drift")

    boundary = contract.get("currentBoundary")
    readiness = contract.get("readiness")
    require(isinstance(boundary, dict) and isinstance(readiness, dict), "contract authority state missing")
    require(boundary.get("registeredTypedRecordCount") == count, "contract typed record count drift")
    require(boundary.get("completeTypedRecordCount") == derived_complete, "contract complete typed count drift")
    require(boundary.get("productionEquivalentRecoveryCandidateCount") == len(final_candidate_ids), "contract candidate count drift")
    require(boundary.get("candidateCoveredCount") == len(covered_base_ids), "contract covered candidate count drift")
    require(boundary.get("uncoveredCandidateCount") == len(pending_typed_ids), "contract pending typed coverage count drift")
    require(boundary.get("productionEquivalentNonResurrectionEvidence") is (len(final_candidate_ids) > 0), "contract non-resurrection evidence derivation drift")
    require(boundary.get("productionEvidence") is False and boundary.get("productionReady") is False, "contract cannot promote production")
    require(boundary.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")
    require(readiness.get("localAppleReplayRestoreProven") is True, "local Apple replay proof readiness drift")
    require(readiness.get("localCoherentRecoverySetProven") is True, "local coherent recovery proof readiness drift")
    require(readiness.get("productionEquivalentCandidateAvailable") is (len(final_candidate_ids) > 0), "candidate availability drift")
    require(readiness.get("productionEquivalentCandidateTypedCoverageComplete") is (len(final_candidate_ids) > 0), "typed candidate coverage readiness drift")
    require(readiness.get("independentReviewCompleted") is (len(final_candidate_ids) > 0), "independent review readiness drift")
    require(readiness.get("productionEquivalentNonResurrectionEvidence") is (len(final_candidate_ids) > 0), "non-resurrection readiness drift")
    require(readiness.get("productionReady") is False, "overlay cannot make application production ready")

    run_validator(NEGATIVE, "non-resurrection negative admission suite")
    print("Memory OS backup/restore typed non-resurrection admission validation PASS")
    print(f"pre-overlay eligible generation records: {len(base_candidate_ids)}")
    print(f"typed records: {count}")
    print(f"final production-equivalent recovery candidates: {len(final_candidate_ids)}")
    print(f"pending typed coverage: {len(pending_typed_ids)}")
    print("generic PASS candidate bypass: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
