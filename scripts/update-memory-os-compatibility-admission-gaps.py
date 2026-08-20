#!/usr/bin/env python3
"""Generate a machine-readable next-admission report from canonical compatibility registries."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RELEASES_REL = Path("contracts/operations/release-baseline-registry.v1.json")
PAIRS_REL = Path("contracts/operations/release-compatibility-pair-registry.v1.json")
CLIENTS_REL = Path("contracts/operations/client-baseline-registry.v1.json")
PARSERS_REL = Path("contracts/operations/parser-artifact-registry.v1.json")
FOUNDATIONS_REL = Path("contracts/operations/version-compatibility-foundations.v1.json")
EXECUTION_REL = Path("contracts/operations/version-compatibility-execution-evidence.v1.json")
OUTPUT_REL = Path("contracts/operations/compatibility-admission-gaps.v1.json")
RELEASE_WRITER_REL = Path("scripts/register-memory-os-release-baseline.py")
PAIR_WRITER_REL = Path("scripts/register-memory-os-release-compatibility-pair.py")
CLIENT_WRITER_REL = Path("scripts/register-memory-os-client-baseline.py")
PARSER_WRITER_REL = Path("scripts/register-memory-os-parser-artifact.py")
FOUNDATIONS_VALIDATOR_REL = Path("scripts/validate-memory-os-version-compatibility-foundations.py")
EXECUTION_VALIDATOR_REL = Path("scripts/validate-memory-os-version-compatibility-execution-evidence.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
WORKFLOW_REL = Path(".github/workflows/compatibility-admission-gaps.yml")
RELEASES = ROOT / RELEASES_REL
PAIRS = ROOT / PAIRS_REL
CLIENTS = ROOT / CLIENTS_REL
PARSERS = ROOT / PARSERS_REL
FOUNDATIONS = ROOT / FOUNDATIONS_REL
EXECUTION = ROOT / EXECUTION_REL
OUTPUT = ROOT / OUTPUT_REL
RELEASE_WRITER = ROOT / RELEASE_WRITER_REL
PAIR_WRITER = ROOT / PAIR_WRITER_REL
CLIENT_WRITER = ROOT / CLIENT_WRITER_REL
PARSER_WRITER = ROOT / PARSER_WRITER_REL
FOUNDATIONS_VALIDATOR = ROOT / FOUNDATIONS_VALIDATOR_REL
EXECUTION_VALIDATOR = ROOT / EXECUTION_VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
WORKFLOW = ROOT / WORKFLOW_REL


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"{field} missing or escapes repository") from exc
    if lexical != expected_relative or resolved != expected_relative or not path.is_file():
        raise SystemExit(f"{field} authority drift")
    return path


def enforce_runtime_authorities() -> None:
    for path, relative, field in (
        (RELEASES, RELEASES_REL, "release registry"),
        (PAIRS, PAIRS_REL, "release pair registry"),
        (CLIENTS, CLIENTS_REL, "client registry"),
        (PARSERS, PARSERS_REL, "parser registry"),
        (FOUNDATIONS, FOUNDATIONS_REL, "compatibility foundations"),
        (EXECUTION, EXECUTION_REL, "compatibility execution evidence"),
        (OUTPUT, OUTPUT_REL, "compatibility admission gaps output"),
        (RELEASE_WRITER, RELEASE_WRITER_REL, "release writer"),
        (PAIR_WRITER, PAIR_WRITER_REL, "release pair writer"),
        (CLIENT_WRITER, CLIENT_WRITER_REL, "client writer"),
        (PARSER_WRITER, PARSER_WRITER_REL, "parser writer"),
        (FOUNDATIONS_VALIDATOR, FOUNDATIONS_VALIDATOR_REL, "compatibility foundations validator"),
        (EXECUTION_VALIDATOR, EXECUTION_VALIDATOR_REL, "compatibility execution validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
        (WORKFLOW, WORKFLOW_REL, "compatibility admission gaps workflow"),
    ):
        require_exact_repo_file(path, relative, field)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str) -> Any:
    if not path.is_file():
        raise SystemExit(f"canonical authority module missing: {path.relative_to(ROOT)}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load canonical authority module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise SystemExit(f"cannot load canonical authority module {path.name}: {exc}") from exc
    return module


def run_validator(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"canonical compatibility validator missing: {path.relative_to(ROOT)}")
    completed = subprocess.run(["python", str(path)], cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"canonical compatibility validator failed: {path.name}")


def write_validated_output(document: dict[str, Any]) -> None:
    original = OUTPUT.read_bytes() if OUTPUT.exists() else None
    try:
        OUTPUT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        run_validator(OPERABILITY_VALIDATOR)
    except BaseException:
        if original is None:
            OUTPUT.unlink(missing_ok=True)
        else:
            OUTPUT.write_bytes(original)
        raise


def non_negative_count(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SystemExit(f"{field} must be a non-negative integer")
    return value


def validate_registry_authorities(
    releases: dict[str, Any],
    pairs: dict[str, Any],
    clients: dict[str, Any],
    parsers: dict[str, Any],
) -> None:
    enforce_runtime_authorities()
    release_writer = load_module(RELEASE_WRITER, "compat_release_writer")
    pair_writer = load_module(PAIR_WRITER, "compat_pair_writer")
    client_writer = load_module(CLIENT_WRITER, "compat_client_writer")
    parser_writer = load_module(PARSER_WRITER, "compat_parser_writer")

    if Path(getattr(release_writer, "REGISTRY_PATH", "")).resolve() != RELEASES.resolve():
        raise SystemExit("release registry authority drift")
    if Path(getattr(pair_writer, "REGISTRY", "")).resolve() != PAIRS.resolve():
        raise SystemExit("release pair registry authority drift")
    if Path(getattr(client_writer, "REGISTRY", "")).resolve() != CLIENTS.resolve():
        raise SystemExit("client registry authority drift")
    if Path(getattr(parser_writer, "REGISTRY_PATH", "")).resolve() != PARSERS.resolve():
        raise SystemExit("parser registry authority drift")

    try:
        release_contract = load(Path(release_writer.CONTRACT_PATH))
        release_writer.validate_registry_for_append(releases, release_contract)
        pair_writer.validate_registry_for_append(pairs)
        client_writer.validate_registry_for_append(clients)
        parser_writer.validate_registry_for_append(parsers)
    except Exception as exc:
        raise SystemExit(f"compatibility registry authority invalid: {exc}") from exc


def main() -> int:
    enforce_runtime_authorities()
    releases = load(RELEASES)
    pairs = load(PAIRS)
    clients = load(CLIENTS)
    parsers = load(PARSERS)
    foundations = load(FOUNDATIONS)
    execution = load(EXECUTION)

    validate_registry_authorities(releases, pairs, clients, parsers)
    run_validator(FOUNDATIONS_VALIDATOR)
    run_validator(EXECUTION_VALIDATOR)

    release_count = non_negative_count(releases.get("approvedReleaseCount"), "approvedReleaseCount")
    pair_count = non_negative_count(pairs.get("rollbackEligiblePairCount"), "rollbackEligiblePairCount")
    client_count = non_negative_count(clients.get("approvedClientBaselineCount"), "approvedClientBaselineCount")
    parser_count = non_negative_count(parsers.get("reviewedArtifactCount"), "reviewedArtifactCount")

    execution_readiness = execution.get("readiness", {})
    proven_candidate = {
        "candidateOnlyMixedVersionExecution": execution_readiness.get("candidateOnlyMixedVersionExecutionProven") is True,
        "candidateApplyConcurrencyAndSIGKILLRecovery": execution_readiness.get("candidateApplyConcurrencyAndSIGKILLRecoveryProven") is True,
        "postgresql17LogicalForwardExecution": execution_readiness.get("postgresql17LogicalForwardExecutionProven") is True,
    }
    if not all(proven_candidate.values()):
        raise SystemExit("candidate/local execution evidence regressed")

    blockers: list[dict[str, Any]] = []
    if release_count < 2:
        blockers.append({
            "id": "COMPAT-GAP-APPROVED-RELEASE-PAIR",
            "blocking": True,
            "current": release_count,
            "requiredMinimum": 2,
            "reason": "an approved predecessor and approved successor are required before release compatibility can be executed",
        })
    if pair_count < 1:
        blockers.append({
            "id": "COMPAT-GAP-ROLLBACK-PAIR",
            "blocking": True,
            "current": pair_count,
            "requiredMinimum": 1,
            "reason": "at least one rollback-eligible approved release pair with retained exact artifacts and admitted rehearsal is required",
        })
    if client_count < 1:
        blockers.append({
            "id": "COMPAT-GAP-APPROVED-CLIENT-BASELINE",
            "blocking": True,
            "current": client_count,
            "requiredMinimum": 1,
            "reason": "client/server support windows cannot exist without an immutable approved client artifact baseline",
        })
    if parser_count < 1:
        blockers.append({
            "id": "COMPAT-GAP-REVIEWED-PARSER-ARTIFACT",
            "blocking": True,
            "current": parser_count,
            "requiredMinimum": 1,
            "reason": "production parser compatibility requires a reviewed immutable parser artifact and replay evidence",
        })

    blockers.extend([
        {
            "id": "COMPAT-GAP-ROLLING-DEPLOYMENT",
            "blocking": True,
            "current": False,
            "required": True,
            "reason": "approved old/current simultaneous traffic, connection drain, rollout ordering, stop conditions and application rollback are not proven",
        },
        {
            "id": "COMPAT-GAP-REMAINING-ROUTES",
            "blocking": True,
            "current": False,
            "required": True,
            "reason": "candidate/local execution covers session and Apply but not all import, Preview, parser and other persisted-state routes against an approved pair",
        },
        {
            "id": "COMPAT-GAP-DB-PRODUCTION-UPGRADE",
            "blocking": True,
            "current": False,
            "required": True,
            "reason": "local PostgreSQL 16-to-17 logical forward restore passes, but production-shaped pool drain, replication, WAL, failover and rollback decision evidence is absent",
        },
        {
            "id": "COMPAT-GAP-INDEPENDENT-REVIEW",
            "blocking": True,
            "current": False,
            "required": True,
            "reason": "integrated compatibility review with zero unresolved Critical or High findings is absent",
        },
    ])

    document = {
        "schemaVersion": "memory-os-compatibility-admission-gaps.v1",
        "sourceAuthorities": [
            str(RELEASES.relative_to(ROOT)),
            str(PAIRS.relative_to(ROOT)),
            str(CLIENTS.relative_to(ROOT)),
            str(PARSERS.relative_to(ROOT)),
            str(FOUNDATIONS.relative_to(ROOT)),
            str(EXECUTION.relative_to(ROOT)),
        ],
        "currentCounts": {
            "approvedBackendReleases": release_count,
            "approvedClientBaselines": client_count,
            "reviewedProductionParserArtifacts": parser_count,
            "approvedRollbackPairs": pair_count,
        },
        "alreadyProvenCandidateLocalOnly": proven_candidate,
        "blockingGaps": blockers,
        "blockingGapCount": len(blockers),
        "releaseCompatibilityEvidence": pair_count > 0,
        "productionEvidence": False,
        "productionReady": False,
        "productionDecision": "NO_GO",
        "nextAdmissionOrder": [
            "approve an immutable backend release baseline only after its existing release-evidence gate passes",
            "obtain a second approved release and form an approved predecessor/successor pair",
            "approve at least one immutable client baseline and reviewed parser artifact",
            "execute approved-pair mixed-version routes and rolling rollback rehearsal",
            "execute production-shaped PostgreSQL upgrade/failover evidence",
            "complete independent integrated compatibility review"
        ]
    }
    write_validated_output(document)
    print("Memory OS compatibility admission gaps updated")
    print(f"blocking gaps: {len(blockers)}")
    print(f"approved backend releases: {release_count}")
    print(f"approved client baselines: {client_count}")
    print(f"reviewed parser artifacts: {parser_count}")
    print(f"approved rollback pairs: {pair_count}")
    print("productionDecision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())