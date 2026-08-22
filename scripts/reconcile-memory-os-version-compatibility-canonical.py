#!/usr/bin/env python3
"""Remove supplemental foundation fields from the canonical compatibility policy.

Candidate-only and local-CI-only evidence belongs exclusively in
version-compatibility-foundations.v1.json. This reconciler is intentionally
idempotent and never promotes a canonical matrix entry.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
PATH_REL = Path("contracts/operations/version-compatibility-contract.v1.json")
VALIDATOR_REL = Path("scripts/validate-memory-os-version-compatibility.py")
WORKFLOW_REL = Path(".github/workflows/version-compatibility-foundations.yml")
PATH = ROOT / PATH_REL
VALIDATOR_PATH = ROOT / VALIDATOR_REL
WORKFLOW_PATH = ROOT / WORKFLOW_REL


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    for path, relative, field in (
        (PATH, PATH_REL, "canonical compatibility contract"),
        (VALIDATOR_PATH, VALIDATOR_REL, "canonical compatibility validator"),
        (WORKFLOW_PATH, WORKFLOW_REL, "compatibility foundations workflow"),
    ):
        require_exact_repo_file(path, relative, field)


def load() -> dict[str, Any]:
    try:
        value = json.loads(PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure("canonical compatibility contract is missing") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"canonical compatibility JSON is invalid: {exc}") from exc
    require(isinstance(value, dict), "canonical compatibility root must be an object")
    return value


def remove_keys(value: dict[str, Any], keys: tuple[str, ...]) -> bool:
    changed = False
    for key in keys:
        if key in value:
            del value[key]
            changed = True
    return changed


def run_canonical_validator() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise ReconcileFailure(
            "canonical compatibility validation failed after reconcile"
            + (f": {detail}" if detail else "")
        )


def commit_transaction(
    document: dict[str, Any],
    *,
    validator_runner: Callable[[], None] = run_canonical_validator,
) -> None:
    original = PATH.read_bytes()
    PATH.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    try:
        validator_runner()
    except Exception:
        PATH.write_bytes(original)
        raise


def main() -> int:
    enforce_runtime_authorities()
    document = load()
    require(document.get("schemaVersion") == "memory-os-version-compatibility.v1",
            "canonical compatibility schema drift")
    require(document.get("productionDecision") == "NO_GO",
            "canonical compatibility production decision drift")

    changed = remove_keys(document, (
        "supplementalCompatibilityEvidence",
        "foundationEvidenceRefs",
    ))

    support = document.get("supportPolicy")
    require(isinstance(support, dict), "supportPolicy missing")
    rolling = support.get("backendRollingWindow")
    database = support.get("database")
    parser = support.get("parserArtifacts")
    require(isinstance(rolling, dict), "backendRollingWindow missing")
    require(isinstance(database, dict), "database support policy missing")
    require(isinstance(parser, dict), "parserArtifacts support policy missing")

    changed = remove_keys(rolling, (
        "historicalCandidateAndCurrentTested",
        "approvedCurrentAndPreviousReleaseTested",
        "candidateOnlyEvidenceRef",
    )) or changed
    changed = remove_keys(database, (
        "postgresql17LogicalForwardUpgradeRehearsed",
        "postgresql17InPlaceOrBlueGreenCutoverRehearsed",
        "postgresql17PhysicalReplicationOrFailoverRehearsed",
        "postgresql17ProductionSupported",
        "logicalUpgradeEvidenceRef",
    )) or changed
    changed = remove_keys(parser, (
        "reviewedRegistryAuthorityImplemented",
        "reviewedArtifactCount",
        "rollbackRetainedArtifactCount",
        "testHarnessApproved",
        "registryRef",
    )) or changed

    readiness = document.get("readiness")
    require(isinstance(readiness, dict), "readiness missing")
    changed = remove_keys(readiness, (
        "historicalCandidateNewSchemaProven",
        "historicalCandidateMixedProcessProven",
        "historicalCandidatePersistedApplyProven",
        "historicalCandidateConcurrentApplyRaceProven",
        "historicalCandidateInFlightTerminationRecoveryProven",
        "postgresql17LogicalForwardUpgradeProven",
        "parserArtifactRegistryAuthorityDefined",
        "reviewedParserArtifactAvailable",
        "rollbackRehearsalAdmissionGateDefined",
        "approvedRollbackPairAvailable",
    )) or changed

    conservative_note = (
        "Compatibility directions and release gates are explicit. Only the current backend "
        "against a clean current PostgreSQL 16 schema is proven in the canonical release "
        "matrix. Candidate-only, local-CI-only and empty-registry foundations are recorded "
        "separately and cannot promote release compatibility; OPS-P0-008 stays PARTIAL."
    )
    if readiness.get("note") != conservative_note:
        readiness["note"] = conservative_note
        changed = True

    require(rolling.get("currentAndPreviousTested") is False,
            "canonical rolling release pair cannot be marked tested")
    require(database.get("majorUpgradeRehearsalCompleted") is False,
            "canonical database major upgrade cannot be marked complete")
    require(parser.get("reviewedRegistryImplemented") is False and
            parser.get("oldArtifactReplayTested") is False,
            "canonical parser compatibility cannot be promoted")
    for field in (
        "oldBackendNewSchemaProven", "rollingBackendMixProven",
        "oldPersistedStateNewConsumerProven", "oldArtifactNewSupervisorProven",
        "clientServerSkewPolicyImplemented", "clientServerSkewProven",
        "databaseUpgradePolicyDefined", "productionRolloutRehearsalCompleted",
        "independentReviewCompleted", "ready",
    ):
        require(readiness.get(field) is False,
                f"canonical readiness overclaim: {field}")

    if not changed:
        run_canonical_validator()
        print("Canonical compatibility authority already conservative")
        return 0
    commit_transaction(document)
    print("Restored conservative canonical compatibility authority")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"CANONICAL COMPATIBILITY RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
