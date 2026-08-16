#!/usr/bin/env python3
"""Fail-closed negatives for approved release compatibility pair authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
REGISTRY = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_release_pair_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load release pair writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def expect_rejected(name: str, action: Callable[[], None]) -> None:
    try:
        action()
    except Exception:
        return
    raise Fail(f"release pair authority accepted invalid case: {name}")


def synthetic_releases(rollback_status: str) -> dict[str, Any]:
    head = git("rev-parse", "HEAD")
    parent = git("rev-parse", "HEAD^")
    return {
        "approvedReleaseCount": 2,
        "releases": [
            {
                "releaseId": "rel_20260815_pairpred",
                "approvalClass": "PRODUCTION_RELEASE_BASELINE",
                "evidenceComplete": True,
                "productionReady": True,
                "commitSha": parent,
                "rollbackEligibility": {"status": rollback_status, "verified": rollback_status == "ELIGIBLE", "conditions": []},
            },
            {
                "releaseId": "rel_20260816_pairsucc",
                "approvalClass": "PRODUCTION_RELEASE_BASELINE",
                "evidenceComplete": True,
                "productionReady": True,
                "commitSha": head,
                "rollbackEligibility": {"status": "NOT_ELIGIBLE", "verified": False, "conditions": []},
            },
        ],
    }


def synthetic_pair(writer: ModuleType) -> dict[str, Any]:
    releases = synthetic_releases("ELIGIBLE")["releases"]
    return {
        "schemaVersion": "memory-os-release-compatibility-pair-record.v1",
        "pairId": "rcp_release_pair_test1",
        "predecessorReleaseId": releases[0]["releaseId"],
        "predecessorCommitSha": releases[0]["commitSha"],
        "successorReleaseId": releases[1]["releaseId"],
        "successorCommitSha": releases[1]["commitSha"],
        "rollingDeploymentEvidenceRefs": ["README.md"],
        "applicationRollbackEvidenceRefs": ["SECURITY.md"],
        "persistedRouteEvidenceRefs": ["docs/runbooks/memory-os-version-compatibility.md"],
        "databaseUpgradeEvidenceRefs": ["docs/runbooks/memory-os-migration-recovery.md"],
        "artifactRetentionEvidenceRefs": ["contracts/operations/release-baseline-registry-contract.v1.json"],
        "independentReviewRefs": ["README.md", "SECURITY.md"],
        "approvedAt": "2026-08-16T00:00:00Z",
        "openFindings": [],
        "pairEvidenceComplete": True,
        "productionEvidence": False,
        "productionReady": False,
    }


def main() -> int:
    writer = load_writer()

    canonical_release_registry = writer.validated_release_registry()
    require(canonical_release_registry.get("approvedReleaseCount") == 0,
            "negative suite requires current canonical approved release count to remain zero")

    original_registry_provider = writer.validated_release_registry
    try:
        writer.validated_release_registry = lambda: synthetic_releases("ELIGIBLE")
        pair = synthetic_pair(writer)
        writer.validate_record(pair)

        writer.validated_release_registry = lambda: synthetic_releases("NOT_ELIGIBLE")
        expect_rejected("non-eligible predecessor", lambda: writer.validate_record(pair))
    finally:
        writer.validated_release_registry = original_registry_provider

    base = load(REGISTRY)
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("boolean approved count", lambda value: value.__setitem__("approvedPairCount", True)),
        ("boolean rollback count", lambda value: value.__setitem__("rollbackEligiblePairCount", True)),
        ("approved count drift", lambda value: value.__setitem__("approvedPairCount", 1)),
        ("latest pointer drift", lambda value: value.__setitem__("latestPairId", "rcp_invalid_pointer")),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("production ready promotion", lambda value: value.__setitem__("productionReady", True)),
        ("unknown registry field", lambda value: value.__setitem__("unexpectedAuthority", True)),
    ]
    for name, mutate in cases:
        corrupt = copy.deepcopy(base)
        mutate(corrupt)
        expect_rejected(name, lambda corrupt=corrupt: writer.validate_registry_for_append(corrupt))

    require(REGISTRY.read_bytes() == (ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json").read_bytes(),
            "negative suite mutated canonical pair registry")
    print("PASS: release compatibility pair authority rejects registry corruption and honors nested rollback eligibility")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
