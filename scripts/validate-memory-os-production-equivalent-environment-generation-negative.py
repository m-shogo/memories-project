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
        "independentReviewRef": ".gitignore",
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

    implementation_review_reuse = copy.deepcopy(equivalent)
    implementation_review_reuse["evidenceBoundary"]["independentReviewRef"] = implementation_review_reuse["postgresql"]["restoreEvidenceRef"]
    expect_rejected("environment review reused as implementation restore evidence", lambda: env_validator.validate_environment_record(implementation_review_reuse))

    material_review_reuse = copy.deepcopy(equivalent)
    material_review_reuse["evidenceBoundary"]["independentReviewRef"] = material_review_reuse["materialDeltas"][0]["independentReviewRef"]
    expect_rejected("environment review reused as material-delta review evidence", lambda: env_validator.validate_environment_record(material_review_reuse))

    real_env_root = env_validator.ROOT
    with tempfile.TemporaryDirectory(prefix="memory-os-semantic-ref-root-") as root_tmp, tempfile.TemporaryDirectory(prefix="memory-os-semantic-ref-external-") as external_tmp:
        root_path = Path(root_tmp)
        external_path = Path(external_tmp) / "external-evidence.txt"
        (root_path / "evidence.txt").write_text("local evidence\n", encoding="utf-8")
        external_path.write_text("external evidence\n", encoding="utf-8")
        env_validator.ROOT = root_path
        try:
            expect_rejected("absolute semantic environment evidence ref", lambda: env_validator.repo_ref(str((root_path / "evidence.txt").resolve()), "negative.absolute", required=True))
            expect_rejected("parent-traversal semantic environment evidence ref", lambda: env_validator.repo_ref("nested/../evidence.txt", "negative.parent", required=True))
            escape_link = root_path / "escaped-evidence.txt"
            escape_link.symlink_to(external_path)
            expect_rejected("semantic environment evidence symlink escapes repository root", lambda: env_validator.repo_ref("escaped-evidence.txt", "negative.symlink", required=True))
            loop_link = root_path / "loop-evidence.txt"
            loop_link.symlink_to(loop_link.name)
            expect_rejected("semantic environment evidence symlink loop", lambda: env_validator.repo_ref("loop-evidence.txt", "negative.loop", required=True))
        finally:
            env_validator.ROOT = real_env_root

    real_root = writer.ROOT
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-ref-root-") as root_tmp, tempfile.TemporaryDirectory(prefix="memory-os-generation-ref-external-") as external_tmp:
        root_path = Path(root_tmp)
        external_path = Path(external_tmp) / "external-environment.json"
        (root_path / "environment.json").write_text("{}\n", encoding="utf-8")
        external_path.write_text("{}\n", encoding="utf-8")
        writer.ROOT = root_path
        try:
            expect_rejected("absolute generation environment ref", lambda: writer.repo_ref(str((root_path / "environment.json").resolve()), "environmentRecordRef"))
            expect_rejected("parent-traversal generation environment ref", lambda: writer.repo_ref("nested/../environment.json", "environmentRecordRef"))
            escape_link = root_path / "escaped-environment.json"
            escape_link.symlink_to(external_path)
            expect_rejected("generation environment symlink escapes repository root", lambda: writer.repo_ref("escaped-environment.json", "environmentRecordRef"))
            loop_link = root_path / "loop-environment.json"
            loop_link.symlink_to(loop_link.name)
            expect_rejected("generation environment ref symlink loop", lambda: writer.repo_ref("loop-environment.json", "environmentRecordRef"))
        finally:
            writer.ROOT = real_root

    with tempfile.TemporaryDirectory(prefix="memory-os-semantic-load-negative-") as tmp:
        tmp_path = Path(tmp)
        invalid_utf8 = tmp_path / "invalid-utf8.json"
        invalid_utf8.write_bytes(b"{\xff}\n")
        expect_rejected("invalid UTF-8 semantic environment record", lambda: env_validator.load_file(invalid_utf8))
        directory_record = tmp_path / "directory-record.json"
        directory_record.mkdir()
        expect_rejected("unreadable semantic environment record directory", lambda: env_validator.load_file(directory_record))

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-negative-") as tmp:
        tmp_path = Path(tmp)
        env_path = tmp_path / "environment.json"
        env_path.write_text(json.dumps(planned, indent=2) + "\n", encoding="utf-8")
        real_repo_ref = writer.repo_ref
        real_source_binding = writer.require_repo_file_bound_to_source
        writer.repo_ref = lambda value, field: env_path if field == "environmentRecordRef" else real_repo_ref(value, field)
        writer.require_repo_file_bound_to_source = (
            lambda source_commit, path, field: None
            if field == "environmentRecordRef" and path == env_path
            else real_source_binding(source_commit, path, field)
        )
        try:
            valid_generation = generation_record(commit_sha, env_path, planned)
            require(writer.validate_record(valid_generation) is False, "PLANNED generation registration must remain preflight-ineligible")
            print("PASS registration: PLANNED generation history is allowed without preflight eligibility")

            real_loader = writer.load_environment_validator
            class BrokenValidator:
                class Fail(RuntimeError):
                    pass

                @staticmethod
                def validate_environment_record(*args: Any, **kwargs: Any) -> bool:
                    raise TypeError("synthetic implementation failure")

            writer.load_environment_validator = lambda: BrokenValidator
            try:
                writer.validate_record(valid_generation)
            except TypeError:
                print("PASS implementation boundary: semantic validator TypeError surfaced")
            except writer.Fail as exc:
                raise Fail(f"semantic validator implementation failure was folded into domain rejection: {exc}") from exc
            else:
                raise Fail("semantic validator implementation failure was unexpectedly accepted")
            finally:
                writer.load_environment_validator = real_loader

            mutable_alias = copy.deepcopy(valid_generation)
            mutable_alias["generationId"] = "pegen-latest-negative"
            expect_rejected("mutable generation alias", lambda: writer.validate_record(mutable_alias))

            digest_mismatch = copy.deepcopy(valid_generation)
            digest_mismatch["environmentRecordSha256"] = "f" * 64
            expect_rejected("environment record digest mismatch", lambda: writer.validate_record(digest_mismatch))

            production_flag = copy.deepcopy(valid_generation)
            production_flag["productionEvidence"] = True
            expect_rejected("production evidence relabel", lambda: writer.validate_record(production_flag))
        finally:
            writer.require_repo_file_bound_to_source = real_source_binding
            writer.repo_ref = real_repo_ref

    healthy_registry = {
        "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
        "registryClass": "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS",
        "appendOnly": True,
        "productionEvidence": False,
        "registeredGenerationCount": 0,
        "currentGenerationId": None,
        "generations": [],
        "limitations": [],
    }
    require(writer.validate_registry_for_append(copy.deepcopy(healthy_registry)) == [], "healthy empty generation registry append authority must remain valid")
    print("PASS append authority: healthy empty generation registry")

    registry_cases = (
        ("generation registry schema drift before append", "schemaVersion", "memory-os-production-equivalent-environment-generation-registry.v0"),
        ("generation registry class drift before append", "registryClass", "UNTRUSTED_GENERATION_AUTHORITY"),
        ("generation registry appendOnly disabled before append", "appendOnly", False),
        ("generation registry production evidence boundary drift before append", "productionEvidence", True),
        ("generation registry registeredGenerationCount drift before append", "registeredGenerationCount", 1),
        ("generation registry boolean registeredGenerationCount before append", "registeredGenerationCount", False),
        ("generation registry current pointer drift before append", "currentGenerationId", "pegen_unregistered"),
    )
    for name, field, invalid_value in registry_cases:
        mutated = copy.deepcopy(healthy_registry)
        mutated[field] = invalid_value
        expect_rejected(name, lambda value=mutated: writer.validate_registry_for_append(value))

    print("Memory OS production-equivalent environment generation negative suite PASS")
    print("canonical registry mutated: false")
    print("registration implies preflight eligibility: false")
    print("incomplete equivalent environment accepted: false")
    print("environment independent review reuse accepted: false")
    print("semantic environment evidence refs escape repository: false")
    print("generation environment refs escape repository: false")
    print("semantic environment ref symlink loops accepted: false")
    print("generation environment ref symlink loops accepted: false")
    print("invalid or unreadable semantic environment authority accepted: false")
    print("semantic validator implementation exceptions folded into rejection: false")
    print("unexpected implementation exception accepted as valid rejection: false")
    print("generation registry append authority drift accepted: false")
    print("boolean generation registry counts accepted before append: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT GENERATION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
