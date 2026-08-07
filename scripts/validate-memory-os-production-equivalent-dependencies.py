#!/usr/bin/env python3
"""Fail-closed validator for the production-equivalent dependency admission contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/production-equivalent-dependency-contract.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), "contract root must be object")
    return value


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(
        contract.get("schemaVersion") == "memory-os-production-equivalent-dependencies.v1",
        "schema drift",
    )
    require(contract.get("dependencyMode") == "PRODUCTION_EQUIVALENT", "dependency mode drift")
    require(contract.get("classification") == "PRODUCTION_EQUIVALENT_ADMISSION", "classification drift")

    domains = contract.get("requiredDomains")
    require(isinstance(domains, dict), "requiredDomains must be object")
    for domain in ("postgresql", "objectStorage", "queueAndWorkers", "network", "identityAndSecrets"):
        require(isinstance(domains.get(domain), dict), f"missing required domain: {domain}")

    postgres = domains["postgresql"]
    for key in (
        "tlsRequired",
        "runtimeRoleMustNotBypassRLS",
        "forceRLSEnabled",
        "connectionBudgetDeclared",
        "connectionPoolTelemetryRequired",
        "backupAndRestoreEvidenceRequired",
        "failoverOrOutageBehaviorRequired",
    ):
        require(postgres.get(key) is True, f"postgresql safeguard missing: {key}")

    object_storage = domains["objectStorage"]
    for key in (
        "tlsRequired",
        "scopedCredentialsRequired",
        "versioningRequired",
        "retentionLifecycleDeclared",
        "exactVersionDeleteRequired",
        "outageAndRecoveryEvidenceRequired",
    ):
        require(object_storage.get(key) is True, f"object-storage safeguard missing: {key}")

    queue_workers = domains["queueAndWorkers"]
    for key in (
        "boundedBackpressureRequired",
        "queueDepthAndAgeTelemetryRequired",
        "deletionBacklogTelemetryRequired",
        "workerLeaseAndRetryBehaviorRequired",
    ):
        require(queue_workers.get(key) is True, f"queue/worker safeguard missing: {key}")

    network = domains["network"]
    for key in (
        "nonLoopbackTopologyRequired",
        "tlsVerificationRequired",
        "latencyProfileRecorded",
        "failureInjectionBounded",
    ):
        require(network.get(key) is True, f"network safeguard missing: {key}")

    identity = domains["identityAndSecrets"]
    require(identity.get("productionCredentialsForbidden") is True, "production credentials must stay forbidden")
    require(identity.get("dedicatedNonProductionCredentialsRequired") is True, "dedicated non-production credentials required")
    require(identity.get("credentialScopeRecorded") is True, "credential scope must be recorded")
    require(identity.get("secretMaterialForbiddenFromEvidence") is True, "secret material must be forbidden from evidence")

    evidence = contract.get("requiredEvidence")
    require(isinstance(evidence, list) and len(evidence) >= 8, "requiredEvidence is incomplete")
    require(len(evidence) == len(set(evidence)), "requiredEvidence contains duplicates")

    delta = contract.get("materialDeltaPolicy")
    require(isinstance(delta, dict), "materialDeltaPolicy must be object")
    for key in (
        "emptyDeltaSetRequiredForAutomaticEquivalence",
        "automaticWaiverForbidden",
        "independentReviewRequiredForAnyAcceptedDelta",
        "unknownDeltaFailsClosed",
    ):
        require(delta.get(key) is True, f"material-delta safeguard missing: {key}")
    require(delta.get("productionTrafficRequired") is False, "production traffic must not be required")
    require(delta.get("productionCredentialsRequired") is False, "production credentials must not be required")

    promotion = contract.get("promotionRules")
    require(isinstance(promotion, dict), "promotionRules must be object")
    for key in (
        "contractAloneIsEvidence",
        "localPostgresMinioCanBeRelabeled",
        "githubHostedRunnerCanBeRelabeled",
        "singlePassingScenarioCanPromoteEnvironment",
    ):
        require(promotion.get(key) is False, f"unsafe promotion rule enabled: {key}")
    for key in (
        "allRequiredDomainsMustPass",
        "allRequiredEvidenceMustBeCommitted",
        "independentReviewRequired",
        "automaticProductionReadyPromotionForbidden",
    ):
        require(promotion.get(key) is True, f"promotion safeguard missing: {key}")

    boundary = contract.get("evidenceBoundary")
    require(isinstance(boundary, dict), "evidenceBoundary must be object")
    for key in (
        "environmentProvisioned",
        "environmentValidated",
        "productionTraffic",
        "productionCredentials",
        "productionEvidence",
        "productionEquivalentDependencies",
        "capacityBoundaryEstablished",
        "operationalThresholdApproved",
        "independentReviewCompleted",
        "productionReady",
    ):
        require(boundary.get(key) is False, f"foundation cannot pre-claim evidenceBoundary.{key}")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be object")
    require(readiness.get("contractDefined") is True, "contractDefined must be true")
    require(isinstance(readiness.get("validatorImplemented"), bool), "validatorImplemented must be boolean")
    require(isinstance(readiness.get("automaticValidationImplemented"), bool), "automaticValidationImplemented must be boolean")
    for key in (
        "environmentProvisioned",
        "environmentInventoryCommitted",
        "postgresqlEvidenceCommitted",
        "objectStorageEvidenceCommitted",
        "queueWorkerEvidenceCommitted",
        "networkEvidenceCommitted",
        "backupRestoreEvidenceCommitted",
        "materialDeltaLedgerCommitted",
        "independentReviewCompleted",
        "productionEquivalentDependencies",
        "productionReady",
    ):
        require(readiness.get(key) is False, f"foundation cannot pre-claim readiness.{key}")

    print("Memory OS production-equivalent dependency contract PASS")
    print("environment provisioned: false")
    print("production-equivalent dependencies: false")
    print("production evidence: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT DEPENDENCY CONTRACT FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
