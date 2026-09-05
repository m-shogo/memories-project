#!/usr/bin/env python3
"""Fail-closed negatives for approved release compatibility pair authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/release-compatibility-pair-contract.v1.json"
WRITER = ROOT / "scripts/register-memory-os-release-compatibility-pair.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-release-compatibility-pair.py"
REGISTRY = ROOT / "contracts/operations/release-compatibility-pair-registry.v1.json"
LOCK = ROOT / "contracts/operations/.release-compatibility-pair.lock"
RECONCILER = ROOT / "scripts/reconcile-memory-os-release-compatibility-pair.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_writer() -> ModuleType:
    module = load_module(WRITER, "memory_os_release_pair_writer_negative")
    require(getattr(module, "CONTRACT", None) == CONTRACT, "release pair writer contract authority drift")
    require(getattr(module, "REGISTRY", None) == REGISTRY, "release pair writer registry authority drift")
    require(getattr(module, "LOCK", None) == LOCK, "release pair writer append lock authority drift")
    return module


def prove_reconcile_authority_substitution() -> None:
    reconciler = load_module(RECONCILER, "memory_os_release_pair_reconciler_authority_negative")
    reconciler.enforce_runtime_authorities()
    authority_names = (
        "CONTRACT",
        "RELEASES",
        "REGISTRY",
        "EXECUTION",
        "GAPS",
        "STATUS",
        "VALIDATOR",
        "WRITER",
        "INDEPENDENT_REVIEW_VALIDATOR",
        "VERSION_EXECUTION_VALIDATOR",
        "OPERABILITY_VALIDATOR",
    )
    originals = {name: getattr(reconciler, name) for name in authority_names}
    replacements = {
        "CONTRACT": originals["REGISTRY"],
        "RELEASES": originals["REGISTRY"],
        "REGISTRY": originals["RELEASES"],
        "EXECUTION": originals["GAPS"],
        "GAPS": originals["EXECUTION"],
        "STATUS": originals["CONTRACT"],
        "VALIDATOR": originals["OPERABILITY_VALIDATOR"],
        "WRITER": originals["VALIDATOR"],
        "INDEPENDENT_REVIEW_VALIDATOR": originals["VALIDATOR"],
        "VERSION_EXECUTION_VALIDATOR": originals["OPERABILITY_VALIDATOR"],
        "OPERABILITY_VALIDATOR": originals["VALIDATOR"],
    }
    canonical_contract = originals["CONTRACT"]
    canonical_status = originals["STATUS"]
    contract_before = canonical_contract.read_bytes()
    status_before = canonical_status.read_bytes()

    for name in authority_names:
        setattr(reconciler, name, replacements[name])
        try:
            rejected = False
            try:
                reconciler.enforce_runtime_authorities()
            except reconciler.Fail as exc:
                require("authority" in str(exc), f"unexpected {name} authority rejection: {exc}")
                rejected = True
            require(rejected, f"release pair reconciler accepted substituted authority: {name}")
            require(canonical_contract.read_bytes() == contract_before,
                    f"rejected {name} substitution mutated canonical release pair contract")
            require(canonical_status.read_bytes() == status_before,
                    f"rejected {name} substitution mutated canonical production status")
        finally:
            setattr(reconciler, name, originals[name])
    reconciler.enforce_runtime_authorities()


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


def expect_validator_rejected(label: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR)], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    require(completed.returncode != 0,
            f"standalone release pair validator accepted corrupt authority: {label}")


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
    pair = {
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
    writer.bind_evidence_digests(pair)
    return pair


def main() -> int:
    prove_reconcile_authority_substitution()
    writer = load_writer()
    contract_bytes = CONTRACT.read_bytes()
    contract = json.loads(contract_bytes.decode("utf-8"))
    require(contract.get("appendLockPath") == str(LOCK.relative_to(ROOT)),
            "release pair contract append lock authority drift")

    canonical_release_registry = writer.validated_release_registry()
    require(canonical_release_registry.get("approvedReleaseCount") == 0,
            "negative suite requires current canonical approved release count to remain zero")

    original_registry_provider = writer.validated_release_registry
    try:
        writer.validated_release_registry = lambda: synthetic_releases("ELIGIBLE")
        pair = synthetic_pair(writer)
        writer.validate_record(pair)

        missing_digest_field = copy.deepcopy(pair)
        missing_digest_field.pop("evidenceDigestsByField")
        expect_rejected("missing evidence digest authority", lambda: writer.validate_record(missing_digest_field))

        missing_digest_ref = copy.deepcopy(pair)
        missing_digest_ref["evidenceDigestsByField"]["rollingDeploymentEvidenceRefs"].clear()
        expect_rejected("missing evidence digest ref", lambda: writer.validate_record(missing_digest_ref))

        malformed_digest = copy.deepcopy(pair)
        malformed_digest["evidenceDigestsByField"]["rollingDeploymentEvidenceRefs"]["README.md"] = "not-a-sha256"
        expect_rejected("malformed evidence digest", lambda: writer.validate_record(malformed_digest))

        stale_digest = copy.deepcopy(pair)
        stale_digest["evidenceDigestsByField"]["rollingDeploymentEvidenceRefs"]["README.md"] = "0" * 64
        expect_rejected("stale evidence digest", lambda: writer.validate_record(stale_digest))

        link = ROOT / ".release-pair-negative-link"
        require(not link.exists() and not link.is_symlink(), "negative symlink fixture path already exists")
        with tempfile.TemporaryDirectory(prefix="release-pair-evidence-") as temp_dir:
            outside = Path(temp_dir)
            (outside / "evidence.json").write_text("{}\n", encoding="utf-8")
            link.symlink_to(outside, target_is_directory=True)
            try:
                escaped = copy.deepcopy(pair)
                escaped["rollingDeploymentEvidenceRefs"] = [".release-pair-negative-link/evidence.json"]
                expect_rejected("parent symlink evidence escape", lambda: writer.bind_evidence_digests(escaped))
            finally:
                link.unlink(missing_ok=True)

        untracked = ROOT / ".release-pair-negative-untracked.json"
        require(not untracked.exists(), "negative untracked fixture path already exists")
        untracked.write_text("{}\n", encoding="utf-8")
        try:
            uncommitted = copy.deepcopy(pair)
            uncommitted["rollingDeploymentEvidenceRefs"] = [untracked.name]
            expect_rejected("uncommitted evidence reference", lambda: writer.bind_evidence_digests(uncommitted))
        finally:
            untracked.unlink(missing_ok=True)

        writer.validated_release_registry = lambda: synthetic_releases("NOT_ELIGIBLE")
        expect_rejected("non-eligible predecessor", lambda: writer.validate_record(pair))
    finally:
        writer.validated_release_registry = original_registry_provider

    base = load(REGISTRY)
    contract_cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("append lock binding drift", lambda value: value.__setitem__("appendLockPath", "contracts/operations/.release-compatibility-pair-alternate.lock")),
        ("transactional append rule drift", lambda value: value["rules"].__setitem__("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure", False)),
        ("independent review validator drift", lambda value: value.__setitem__("independentReviewValidator", "scripts/validate-memory-os-operability.py")),
        ("registry authority drift", lambda value: value.__setitem__("registry", "contracts/operations/release-baseline-registry.v1.json")),
    ]
    for label, mutate in contract_cases:
        try:
            corrupt_contract = copy.deepcopy(contract)
            mutate(corrupt_contract)
            CONTRACT.write_text(json.dumps(corrupt_contract, indent=2) + "\n", encoding="utf-8")
            expect_rejected(f"direct writer {label}", lambda: writer.validate_registry_for_append(base))
            expect_validator_rejected(label)
        finally:
            CONTRACT.write_bytes(contract_bytes)

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

    original_registry_bytes = REGISTRY.read_bytes()
    original_registry_mode = stat.S_IMODE(REGISTRY.stat().st_mode)
    os.chmod(REGISTRY, 0o640)
    protected_registry_mode = stat.S_IMODE(REGISTRY.stat().st_mode)
    original_atomic_write = writer.atomic_write
    original_post_validator = writer.validate_registry_for_append
    observed = {"changed": False}
    candidate = copy.deepcopy(base)
    candidate["limitations"] = list(base.get("limitations", [])) + ["synthetic rollback sentinel"]

    def observing_atomic_write(value: dict[str, Any]) -> None:
        original_atomic_write(value)
        observed["changed"] = REGISTRY.read_bytes() != original_registry_bytes

    def reject_after_write(_value: dict[str, Any]) -> None:
        raise writer.Fail("synthetic post-append validation failure")

    try:
        writer.atomic_write = observing_atomic_write
        writer.validate_registry_for_append = reject_after_write
        expect_rejected("post-append canonical validation failure", lambda: writer.write_registry_transactionally(candidate))
        require(observed["changed"], "transactional append negative did not exercise a registry write")
        require(REGISTRY.read_bytes() == original_registry_bytes,
                "release pair registry was not restored after post-append validation failure")
        require(stat.S_IMODE(REGISTRY.stat().st_mode) == protected_registry_mode,
                "release pair registry mode was not restored after post-append validation failure")
    finally:
        writer.atomic_write = original_atomic_write
        writer.validate_registry_for_append = original_post_validator
        if REGISTRY.read_bytes() != original_registry_bytes:
            writer.atomic_restore(original_registry_bytes)

    original_replace = writer.os.replace

    def reject_replace(_source: str | Path, _target: str | Path) -> None:
        raise OSError("synthetic release pair replace rejection")

    try:
        writer.os.replace = reject_replace
        expect_rejected("registry replace rejection", lambda: writer.atomic_write(candidate))
        require(REGISTRY.read_bytes() == original_registry_bytes,
                "release pair replace rejection mutated canonical registry bytes")
        require(stat.S_IMODE(REGISTRY.stat().st_mode) == protected_registry_mode,
                "release pair replace rejection mutated canonical registry mode")
        residues = list(REGISTRY.parent.glob(".release-pair.*.tmp"))
        require(not residues, f"release pair replace rejection left temp residue: {residues}")
    finally:
        writer.os.replace = original_replace
        if REGISTRY.read_bytes() != original_registry_bytes:
            writer.atomic_restore(original_registry_bytes)
        os.chmod(REGISTRY, original_registry_mode)

    require(REGISTRY.read_bytes() == original_registry_bytes,
            "negative suite mutated canonical pair registry")
    print("PASS: release compatibility pair authority rejects reconciler substitution, contract substitution, registry corruption, evidence drift, and preserves registry bytes/mode across append rollback and replace rejection")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE COMPATIBILITY PAIR NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
