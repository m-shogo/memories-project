#!/usr/bin/env python3
"""Prove fail-closed environment-generation admission and preflight eligibility."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
ENV_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-record.py"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64


class Fail(RuntimeError):
    pass


EXPECTED_FAILURES: tuple[type[Exception], ...] = (Fail,)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def head_sha() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, "cannot resolve HEAD")
    value = completed.stdout.strip()
    require(len(value) == 40, "HEAD must be full SHA")
    return value


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except EXPECTED_FAILURES:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def planned_env() -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-production-equivalent-environment-record.v1",
        "environmentId": "pe-negative-a",
        "generationId": "pegen-negative-a-v1",
        "status": "PLANNED",
        "topology": {
            "regionClass": "regional-nonproduction",
            "nonLoopback": False,
            "productionTraffic": False,
            "productionCredentials": False,
        },
        "postgresql": {
            "tlsVerified": False,
            "runtimeRoleBypassRLS": False,
            "forceRLSVerified": False,
            "connectionBudgetDeclared": False,
            "poolTelemetryVerified": False,
            "restoreEvidenceRef": None,
        },
        "objectStorage": {
            "tlsVerified": False,
            "scopedCredentialsVerified": False,
            "versioningVerified": False,
            "retentionLifecycleVerified": False,
            "exactVersionDeleteVerified": False,
            "restoreEvidenceRef": None,
        },
        "queueWorkers": {
            "boundedBackpressureVerified": False,
            "queueTelemetryVerified": False,
            "deletionBacklogTelemetryVerified": False,
            "leaseRetryVerified": False,
        },
        "network": {
            "tlsVerificationRequired": True,
            "latencyProfileRef": None,
            "failureInjectionRef": None,
        },
        "identityAndSecrets": {
            "dedicatedNonProductionCredentials": False,
            "credentialScopeRef": None,
            "containsSecretMaterial": False,
        },
        "backupRestore": {
            "sameGenerationLinked": False,
            "isolatedRestoreVerified": False,
            "evidenceRef": None,
        },
        "materialDeltas": [],
        "evidenceBoundary": {
            "productionEvidence": False,
            "productionEquivalentDependencies": False,
            "independentReviewCompleted": False,
            "independentReviewRef": None,
            "productionReady": False,
        },
    }


def equivalent_env() -> dict[str, Any]:
    value = planned_env()
    value["status"] = "VALIDATED_LOCAL_NONPRODUCTION"
    value["topology"]["nonLoopback"] = True
    for key in ("tlsVerified", "forceRLSVerified", "connectionBudgetDeclared", "poolTelemetryVerified"):
        value["postgresql"][key] = True
    value["postgresql"]["restoreEvidenceRef"] = "README.md"
    for key in ("tlsVerified", "scopedCredentialsVerified", "versioningVerified", "retentionLifecycleVerified", "exactVersionDeleteVerified"):
        value["objectStorage"][key] = True
    value["objectStorage"]["restoreEvidenceRef"] = "README.md"
    for key in ("boundedBackpressureVerified", "queueTelemetryVerified", "deletionBacklogTelemetryVerified", "leaseRetryVerified"):
        value["queueWorkers"][key] = True
    value["network"]["latencyProfileRef"] = "README.md"
    value["network"]["failureInjectionRef"] = "SECURITY.md"
    value["identityAndSecrets"]["dedicatedNonProductionCredentials"] = True
    value["identityAndSecrets"]["credentialScopeRef"] = "SECURITY.md"
    value["backupRestore"]["sameGenerationLinked"] = True
    value["backupRestore"]["isolatedRestoreVerified"] = True
    value["backupRestore"]["evidenceRef"] = "README.md"
    value["materialDeltas"] = [{
        "deltaId": "NEGATIVE-MATERIAL-001",
        "description": "synthetic reviewed topology delta for negative-suite coverage",
        "classification": "MATERIAL",
        "accepted": True,
        "independentReviewRef": "SECURITY.md",
    }]
    value["evidenceBoundary"] = {
        "productionEvidence": False,
        "productionEquivalentDependencies": True,
        "independentReviewCompleted": True,
        "independentReviewRef": "SECURITY.md",
        "productionReady": False,
    }
    return value


def generation_record(commit_sha: str, env_path: Path, env: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-production-equivalent-environment-generation-record.v1",
        "environmentId": env["environmentId"],
        "generationId": env["generationId"],
        "registeredAt": "2026-08-08T00:00:00Z",
        "sourceCommitSha": commit_sha,
        "environmentManifestSha256": DIGEST_A,
        "dependencyInventorySha256": DIGEST_B,
        "evidenceBundleManifestSha256": DIGEST_C,
        "materialDeltaLedgerSha256": DIGEST_D,
        "environmentRecordRef": "synthetic-environment-record.json",
        "environmentRecordSha256": hashlib.sha256(env_path.read_bytes()).hexdigest(),
        "supersedesGenerationId": None,
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionReady": False,
    }


def main() -> int:
    global EXPECTED_FAILURES
    require(WRITER.is_file() and ENV_VALIDATOR.is_file(), "generation validation foundation missing")
    writer = load_module(WRITER, "memory_os_generation_writer_negative")
    env_validator = load_module(ENV_VALIDATOR, "memory_os_environment_semantic_negative")
    EXPECTED_FAILURES = (writer.Fail, env_validator.Fail)
    commit_sha = head_sha()

    planned = planned_env()
    require(env_validator.validate_environment_record(planned) is False, "PLANNED environment must be structurally valid but preflight-ineligible")
    print("PASS non-eligible: PLANNED generation environment")

    equivalent = equivalent_env()
    require(env_validator.validate_environment_record(equivalent) is True, "complete equivalent environment must satisfy semantic preflight predicate")
    print("PASS eligible: complete validated equivalent environment")

    missing_section = copy.deepcopy(planned)
    del missing_section["queueWorkers"]
    expect_rejected("missing required nested section", lambda: env_validator.validate_environment_record(missing_section))

    unknown_field = copy.deepcopy(planned)
    unknown_field["unexpected"] = True
    expect_rejected("unknown top-level field", lambda: env_validator.validate_environment_record(unknown_field))

    prod_traffic = copy.deepcopy(planned)
    prod_traffic["topology"]["productionTraffic"] = True
    expect_rejected("production traffic enabled", lambda: env_validator.validate_environment_record(prod_traffic))

    secret_material = copy.deepcopy(planned)
    secret_material["identityAndSecrets"]["containsSecretMaterial"] = True
    expect_rejected("secret material present", lambda: env_validator.validate_environment_record(secret_material))

    incomplete_equivalent = copy.deepcopy(equivalent)
    incomplete_equivalent["postgresql"]["forceRLSVerified"] = False
    expect_rejected("equivalent classification with incomplete dependency control", lambda: env_validator.validate_environment_record(incomplete_equivalent))

    missing_ref = copy.deepcopy(equivalent)
    missing_ref["network"]["latencyProfileRef"] = None
    expect_rejected("equivalent classification with missing evidence ref", lambda: env_validator.validate_environment_record(missing_ref))

    missing_review_ref = copy.deepcopy(equivalent)
    missing_review_ref["evidenceBoundary"]["independentReviewRef"] = None
    expect_rejected("independent review completed without review evidence ref", lambda: env_validator.validate_environment_record(missing_review_ref))

    material_without_review = copy.deepcopy(equivalent)
    material_without_review["materialDeltas"][0]["independentReviewRef"] = None
    expect_rejected("accepted material delta without independent review", lambda: env_validator.validate_environment_record(material_without_review))

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-negative-") as tmp:
        tmp_path = Path(tmp)
        env_path = tmp_path / "environment.json"
        env_path.write_text(json.dumps(planned, indent=2) + "\n", encoding="utf-8")
        real_repo_ref = writer.repo_ref
        writer.repo_ref = lambda value, field: env_path if field == "environmentRecordRef" else real_repo_ref(value, field)

        valid_generation = generation_record(commit_sha, env_path, planned)
        require(writer.validate_record(valid_generation) is False, "PLANNED generation registration must remain preflight-ineligible")
        print("PASS registration: PLANNED generation history is allowed without preflight eligibility")

        mutable_alias = copy.deepcopy(valid_generation)
        mutable_alias["generationId"] = "pegen-latest-negative"
        expect_rejected("mutable generation alias", lambda: writer.validate_record(mutable_alias))

        digest_mismatch = copy.deepcopy(valid_generation)
        digest_mismatch["environmentRecordSha256"] = "f" * 64
        expect_rejected("environment record digest mismatch", lambda: writer.validate_record(digest_mismatch))

        production_flag = copy.deepcopy(valid_generation)
        production_flag["productionEvidence"] = True
        expect_rejected("production evidence relabel", lambda: writer.validate_record(production_flag))

        writer.repo_ref = real_repo_ref

    print("Memory OS production-equivalent environment generation negative suite PASS")
    print("canonical registry mutated: false")
    print("registration implies preflight eligibility: false")
    print("incomplete equivalent environment accepted: false")
    print("unexpected implementation exception accepted as valid rejection: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
