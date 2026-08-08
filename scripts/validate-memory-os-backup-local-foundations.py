#!/usr/bin/env python3
"""Fail-closed validator for committed local backup/restore foundations."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "contracts/operations/backup-local-foundation-evidence.v1.json"
LOGICAL_RESULT = ROOT / "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json"
OBJECT_RESULT = ROOT / "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_IDS = {
    "LOCAL_POSTGRESQL_LOGICAL_RESTORE",
    "LOCAL_EXACT_OBJECT_VERSION_RESTORE",
}
EXPECTED_REFS = {
    "contracts/operations/backup-local-foundation-evidence.v1.json",
    "contracts/operations/local-logical-restore-contract.v1.json",
    "contracts/operations/local-object-version-restore-contract.v1.json",
    "docs/fixtures/memory-os-operability/local-logical-restore-results.sample.v1.json",
    "docs/fixtures/memory-os-operability/local-object-version-restore-results.sample.v1.json",
    "scripts/validate-memory-os-backup-local-foundations.py",
    "scripts/reconcile-memory-os-backup-authority.py",
    ".github/workflows/reconcile-backup-authority.yml",
}


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def strings(value: Any, field: str, minimum: int = 1) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(len(value) >= minimum, f"{field} requires at least {minimum} entries")
    require(all(isinstance(item, str) and item.strip() for item in value),
            f"{field} contains an empty or non-string value")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    return value


def source_is_ancestor(value: Any) -> bool:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        return False
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", value, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def validate_logical(result: dict[str, Any]) -> None:
    require(result.get("schemaVersion") == "memory-os-local-logical-restore-results.v1",
            "logical restore result schema drift")
    require(source_is_ancestor(result.get("commitSha")),
            "logical restore result SHA is not an ancestor of current HEAD")
    environment = result.get("environment")
    require(isinstance(environment, dict), "logical restore environment missing")
    require(environment.get("databaseMode") ==
            "EPHEMERAL_POSTGRESQL_16_SAME_CLUSTER_LOGICAL_RESTORE",
            "logical restore mode drift")
    require(environment.get("productionEvidence") is False and
            environment.get("containsSecrets") is False,
            "logical restore evidence boundary drift")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "logical restore scenario missing")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "logical restore is not PASS")
    require(scenario.get("migrationFilesApplied") == 11 and
            scenario.get("sqlIntegrationTestsExecuted") == 11,
            "logical restore did not execute the full canonical migration/test sequence")
    require(isinstance(scenario.get("dumpBytes"), int) and scenario["dumpBytes"] > 0,
            "logical dump size invalid")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict), "logical restore assertions missing")
    require(assertions.get("runtimeRolesWithoutBypassRls") == 4,
            "logical restore runtime role assertion failed")
    require(isinstance(assertions.get("forceRlsTables"), int) and
            assertions["forceRlsTables"] > 0,
            "logical restore FORCE RLS assertion failed")
    for field in (
        "deletedSyntheticAccountsAfterRestore",
        "deletedSyntheticSessionDigestsAfterRestore",
        "deletedSyntheticSessionsResolvedAfterRestore",
        "expiredSyntheticSessionsResolvedAfterRestore",
        "revokedSyntheticSessionsResolvedAfterRestore",
    ):
        require(assertions.get(field) == 0,
                f"logical restore non-resurrection assertion failed: {field}")
    require(assertions.get("expiredSyntheticSessionRowsAfterRestore") == 1,
            "expired session terminal state was not preserved")
    require(assertions.get("revokedSyntheticSessionRowsAfterRestore") == 1,
            "revoked session terminal state was not preserved")


def validate_object(result: dict[str, Any]) -> None:
    require(result.get("schemaVersion") ==
            "memory-os-local-object-version-restore-results.v1",
            "object restore result schema drift")
    require(source_is_ancestor(result.get("commitSha")),
            "object restore result SHA is not an ancestor of current HEAD")
    environment = result.get("environment")
    require(isinstance(environment, dict), "object restore environment missing")
    require(environment.get("objectStoreMode") ==
            "LOCAL_MINIO_VERSIONED_THREE_BUCKET_RECOVERY",
            "object restore mode drift")
    require(environment.get("productionEvidence") is False and
            environment.get("containsSecrets") is False,
            "object restore evidence boundary drift")
    for field in ("endpointIdentityDigest", "bucketSetIdentityDigest"):
        value = environment.get(field)
        require(isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None,
                f"object restore {field} must be a digest")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict), "object restore scenario missing")
    require(scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "object restore is not PASS")
    require(scenario.get("sourceVersionsCreated") >= 3 and
            scenario.get("sourceVersionsRemainingAfterLoss") == 0,
            "object restore source-version loss simulation failed")
    for field in (
        "selectedSourceVersionDigest", "backupVersionDigest",
        "restoreVersionDigest", "objectKeyDigest", "contentChecksumSha256",
    ):
        value = scenario.get(field)
        require(isinstance(value, str) and DIGEST_RE.fullmatch(value) is not None,
                f"object restore {field} must be a digest")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and assertions,
            "object restore assertions missing")
    require(all(value is True for value in assertions.values()),
            "object restore contains a failed assertion")


def main() -> int:
    index = load(INDEX_PATH)
    require(index.get("schemaVersion") ==
            "memory-os-backup-local-foundation-evidence.v1",
            "local backup foundation schema drift")
    require(index.get("productionEvidence") is False,
            "local foundation index cannot claim production evidence")
    require(index.get("productionDecision") == "NO_GO",
            "local foundation index cannot change production decision")
    require(index.get("evidenceClass") == "LOCAL_CI_FOUNDATION",
            "local foundation evidence class drift")
    require(index.get("validator") ==
            "scripts/validate-memory-os-backup-local-foundations.py",
            "local foundation validator path drift")
    require(index.get("reconcile") ==
            "scripts/reconcile-memory-os-backup-authority.py",
            "local foundation reconcile path drift")

    foundations = index.get("foundations")
    require(isinstance(foundations, list), "foundations must be a list")
    by_id = {item.get("id"): item for item in foundations if isinstance(item, dict)}
    require(set(by_id) == EXPECTED_IDS,
            f"local foundation set drift: {sorted(by_id)}")
    require(len(foundations) == len(by_id), "local foundations contain duplicates")
    for foundation_id, item in by_id.items():
        require(item.get("status") == "PASS_EVIDENCE_COMMITTED",
                f"foundation is not committed PASS: {foundation_id}")
        for field in ("contract", "result", "validator", "workflow"):
            path = item.get(field)
            require(isinstance(path, str) and (ROOT / path).is_file(),
                    f"foundation path missing: {foundation_id}.{field}")
        strings(item.get("proves"), f"{foundation_id}.proves", 6)
        strings(item.get("doesNotProve"), f"{foundation_id}.doesNotProve", 5)
    logical_proves = "\n".join(by_id["LOCAL_POSTGRESQL_LOGICAL_RESTORE"]["proves"])
    for phrase in ("expired active session", "revoked unexpired session", "cannot resolve"):
        require(phrase in logical_proves, f"logical foundation index omits terminal-session proof: {phrase}")

    boundary = index.get("combinedBoundary")
    require(isinstance(boundary, dict), "combinedBoundary must be an object")
    require(boundary.get("bothExactSourceResultsCommitted") is True,
            "combined local results are not marked committed")
    for unproven in (
        "coherentDatabaseObjectRestoreCompleted",
        "postgresPitrConfigured",
        "independentObjectRetentionConfigured",
        "productionTlsAndCredentialSeparationVerified",
        "rpoRtoApprovedAndMeasured",
        "productionPromotionRehearsed",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(boundary.get(unproven) is False,
                f"local foundation index cannot claim {unproven}")

    refs = strings(index.get("evidenceRefs"), "evidenceRefs", 8)
    require(set(refs) == EXPECTED_REFS, f"local foundation evidenceRefs drift: {refs}")
    for ref in refs:
        require((ROOT / ref).is_file(), f"local foundation evidence missing: {ref}")

    validate_logical(load(LOGICAL_RESULT))
    validate_object(load(OBJECT_RESULT))

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "local backup foundations cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-007"), None)
    require(isinstance(gate, dict), "OPS-P0-007 missing")
    require(gate.get("status") != "READY",
            "local backup foundations cannot make OPS-P0-007 READY")

    print("Memory OS local backup/restore foundation validation PASS")
    print("committed foundations: 2")
    print("expired/revoked session restore semantics: PASS")
    print(f"OPS-P0-007 status: {gate.get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"BACKUP LOCAL FOUNDATION VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
