#!/usr/bin/env python3
"""Fail-closed validator for client/server support-window admission registries."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/client-server-support-window-contract.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
CLIENTS = ROOT / "contracts/operations/client-baseline-registry.v1.json"
SKEW = ROOT / "contracts/operations/client-server-skew-registry.v1.json"
RELEASE_WRITER = ROOT / "scripts/register-memory-os-release-baseline.py"
CLIENT_WRITER = ROOT / "scripts/register-memory-os-client-baseline.py"
SKEW_FIELDS = {
    "schemaVersion",
    "registryClass",
    "appendOnly",
    "productionEvidence",
    "admissibleSkewPairCount",
    "pairs",
    "limitations",
}


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


def load_module(path: Path, name: str) -> Any:
    require(path.is_file(), f"canonical authority missing: {path.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load canonical authority: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_upstream_registries(releases: dict[str, Any], clients: dict[str, Any]) -> None:
    release_writer = load_module(RELEASE_WRITER, "memory_os_release_writer_for_support_window")
    require(Path(release_writer.REGISTRY_PATH).resolve() == RELEASES.resolve(),
            "canonical release registry authority drift")
    release_contract = load(Path(release_writer.CONTRACT_PATH))
    try:
        release_writer.validate_registry_for_append(releases, release_contract)
    except Exception as exc:
        raise Fail(f"approved release authority invalid: {exc}") from exc

    client_writer = load_module(CLIENT_WRITER, "memory_os_client_writer_for_support_window")
    require(Path(client_writer.REGISTRY).resolve() == CLIENTS.resolve(),
            "canonical client registry authority drift")
    try:
        client_writer.validate_registry_for_append(clients)
    except Exception as exc:
        raise Fail(f"approved client authority invalid: {exc}") from exc


def validate_skew_registry(skew: dict[str, Any]) -> int:
    require(set(skew) == SKEW_FIELDS, "skew registry field set drift")
    require(skew.get("schemaVersion") == "memory-os-client-server-skew-registry.v1", "skew registry schema drift")
    require(skew.get("registryClass") == "ADMITTED_CLIENT_SERVER_SKEW_PAIRS", "skew registry class drift")
    require(skew.get("appendOnly") is True and skew.get("productionEvidence") is False, "skew registry boundary drift")
    pair_count = skew.get("admissibleSkewPairCount")
    pairs = skew.get("pairs")
    require(isinstance(pair_count, int) and not isinstance(pair_count, bool) and pair_count >= 0,
            "admissibleSkewPairCount invalid")
    require(isinstance(pairs, list) and len(pairs) == pair_count, "skew registry count mismatch")
    limitations = skew.get("limitations")
    require(isinstance(limitations, list) and limitations and
            all(isinstance(item, str) and item.strip() for item in limitations),
            "skew registry limitations invalid")
    return pair_count


def validate_intermediate_boundary(
    contract: dict[str, Any], approved_release_count: int, approved_client_count: int, pair_count: int
) -> None:
    """Allow approved inventory to accumulate without manufacturing skew/support authority."""
    require(pair_count == 0, "no client/server skew pair admission authority is implemented yet")

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "currentBoundary required")
    require(boundary.get("approvedBackendReleaseCount") == approved_release_count, "backend release boundary drift")
    require(boundary.get("approvedClientBaselineCount") == approved_client_count, "client baseline boundary drift")
    require(boundary.get("admissibleSkewPairCount") == 0, "skew pair boundary drift")
    for key in ("implementedClientSupportWindow", "clientServerSkewEvidence", "releaseCompatibilityEvidence", "productionEvidence", "productionReady"):
        require(boundary.get(key) is False, f"inventory-only state cannot enable {key}")
    require(boundary.get("productionDecision") == "NO_GO", "production decision must remain NO_GO")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness required")
    require(readiness.get("contractDefined") is True and readiness.get("registriesDefined") is True, "foundation definition drift")
    for key in ("validatorImplemented", "automaticWorkflowImplemented"):
        require(isinstance(readiness.get(key), bool), f"readiness.{key} must be boolean")
    require(readiness.get("approvedBackendReleaseAvailable") is (approved_release_count > 0),
            "approved backend release availability drift")
    require(readiness.get("approvedClientBaselineAvailable") is (approved_client_count > 0),
            "approved client baseline availability drift")
    for key in ("supportWindowImplemented", "skewPairExecuted", "independentReviewCompleted", "productionReady"):
        require(readiness.get(key) is False, f"inventory-only state cannot enable readiness.{key}")


def main() -> int:
    contract = load(CONTRACT)
    releases = load(RELEASES)
    clients = load(CLIENTS)
    skew = load(SKEW)

    validate_upstream_registries(releases, clients)

    require(contract.get("schemaVersion") == "memory-os-client-server-support-window.v1", "contract schema drift")
    require(contract.get("releaseRegistry") == str(RELEASES.relative_to(ROOT)), "release registry ref drift")
    require(contract.get("clientRegistry") == str(CLIENTS.relative_to(ROOT)), "client registry ref drift")
    require(contract.get("skewRegistry") == str(SKEW.relative_to(ROOT)), "skew registry ref drift")
    require(contract.get("supportedClientClasses") == ["IOS_APP", "PORTAL"], "client class drift")
    require(contract.get("admissibleDirections") == [
        "CURRENT_CLIENT_CURRENT_BACKEND",
        "PREVIOUS_CLIENT_CURRENT_BACKEND",
        "CURRENT_CLIENT_PREVIOUS_BACKEND",
    ], "skew direction drift")

    rules = contract.get("admissionRules")
    require(isinstance(rules, dict) and rules, "admissionRules required")
    required_rules = (
        "approvedBackendReleaseRequired",
        "approvedClientBaselineRequired",
        "exactClientArtifactDigestRequired",
        "exactBackendArtifactDigestRequired",
        "apiContractVersionBindingRequired",
        "databaseContractVersionBindingRequired",
        "parserProtocolVersionBindingRequired",
        "authenticationSessionCompatibilityRequired",
        "deletionFenceCompatibilityRequired",
        "persistedMutationIdempotencyCompatibilityRequired",
        "offlineResumeCompatibilityRequiredWhenClientCanOperateOffline",
        "explicitMinimumSupportedClientVersionRequired",
        "explicitMaximumSupportedSkewRequired",
        "expiryOrRetirementDateRequired",
        "rollbackEligibilityRequiredForPreviousBackend",
        "independentReviewRequired",
    )
    for key in required_rules:
        require(rules.get(key) is True, f"admission rule must remain true: {key}")

    forbidden = contract.get("forbiddenPromotionSources")
    require(isinstance(forbidden, list), "forbiddenPromotionSources required")
    joined_forbidden = "\n".join(str(item).lower() for item in forbidden)
    for term in ("branch head", "historical candidate", "ci pass", "unbound git tag", "manual compatibility"):
        require(term in joined_forbidden, f"forbidden promotion source missing: {term}")

    required_evidence = contract.get("requiredPairEvidence")
    require(isinstance(required_evidence, list), "requiredPairEvidence required")
    joined_evidence = "\n".join(str(item).lower() for item in required_evidence)
    for terms in (
        ("exact approved client artifact", "approved backend release"),
        ("old-client/new-server", "read", "write"),
        ("new-client/old-server", "read", "write"),
        ("session issuance", "resolution"),
        ("apply", "idempotency"),
        ("account deletion", "fencing"),
        ("offline resume",),
        ("below the minimum support boundary",),
        ("rollback boundary",),
        ("retirement", "silently widen"),
    ):
        require(all(term in joined_evidence for term in terms), f"pair evidence requirement missing: {terms}")

    require(releases.get("schemaVersion") == "memory-os-release-baseline-registry.v1", "release registry schema drift")
    require(releases.get("appendOnly") is True and releases.get("productionEvidence") is False, "release registry boundary drift")
    approved_release_count = releases.get("approvedReleaseCount")
    require(isinstance(approved_release_count, int) and not isinstance(approved_release_count, bool) and approved_release_count >= 0,
            "approvedReleaseCount invalid")
    release_rows = releases.get("releases")
    require(isinstance(release_rows, list) and len(release_rows) == approved_release_count, "release registry count mismatch")

    require(clients.get("schemaVersion") == "memory-os-client-baseline-registry.v1", "client registry schema drift")
    require(clients.get("appendOnly") is True and clients.get("productionEvidence") is False, "client registry boundary drift")
    approved_client_count = clients.get("approvedClientBaselineCount")
    require(isinstance(approved_client_count, int) and not isinstance(approved_client_count, bool) and approved_client_count >= 0,
            "approvedClientBaselineCount invalid")
    client_rows = clients.get("clients")
    require(isinstance(client_rows, list) and len(client_rows) == approved_client_count, "client registry count mismatch")

    pair_count = validate_skew_registry(skew)
    validate_intermediate_boundary(contract, approved_release_count, approved_client_count, pair_count)

    print("Memory OS client/server support-window validation PASS")
    print(f"approved backend releases: {approved_release_count}")
    print(f"approved client baselines: {approved_client_count}")
    print("admissible skew pairs: 0")
    print("client/server skew evidence: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"CLIENT SERVER SUPPORT WINDOW FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
