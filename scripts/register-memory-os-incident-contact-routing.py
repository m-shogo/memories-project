#!/usr/bin/env python3
"""Register one reviewed incident-contact routing evidence record."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/incident-contact-routing-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/incident-contact-routing-admission-registry.v1.json"
OBS_REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
OBS_WRITER = ROOT / "scripts/register-memory-os-observability-stack-deployment.py"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
LOCK = ROOT / "contracts/operations/.incident-contact-routing.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
ROUTING_ID = re.compile(r"^icr_[a-z0-9][a-z0-9_-]{7,63}$")
OWNER_REF = re.compile(r"^owner_[a-z0-9][a-z0-9_-]{5,63}$")
REVIEWER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
UTC_SECONDS = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
PRODUCTION_CONFIRMATION = "REGISTER PRODUCTION INCIDENT CONTACT ROUTING EVIDENCE"
REF_FIELDS = (
    "deliveryDrillEvidenceRefs", "escalationDrillEvidenceRefs",
    "userCommunicationExerciseRefs", "providerContactReviewRefs",
)


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load JSON authority: {path}") from exc
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def load_observability_writer() -> ModuleType:
    require(OBS_WRITER.is_file(), "canonical observability stack writer missing")
    spec = importlib.util.spec_from_file_location("memory_os_observability_writer_for_contact_routing", OBS_WRITER)
    require(spec is not None and spec.loader is not None, "cannot load observability stack writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(getattr(module, "REGISTRY", None) == OBS_REGISTRY,
            "observability stack writer registry authority drift")
    require(callable(getattr(module, "validate_registry_for_append", None)),
            "observability stack registry validator missing")
    return module


def source_is_ancestor(source: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source, "HEAD"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def source_bound_ref(item: str, source: str, field: str) -> None:
    ref = Path(item)
    require(item and not ref.is_absolute() and ".." not in ref.parts,
            f"{field} evidence path invalid: {item}")
    path = ROOT / ref
    cursor = ROOT
    for part in ref.parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), f"{field} evidence cannot traverse symlinks: {item}")
    require(path.is_file(), f"{field} evidence path missing: {item}")
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise Fail(f"{field} evidence escapes repository: {item}") from exc
    completed = subprocess.run(
        ["git", "show", f"{source}:{item}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    require(completed.returncode == 0,
            f"{field} evidence did not exist at sourceCommitSha: {item}")
    require(completed.stdout == path.read_bytes(),
            f"{field} evidence changed after sourceCommitSha: {item}")


def refs(value: Any, field: str, source: str) -> list[str]:
    require(isinstance(value, list) and value, f"{field} must be non-empty")
    require(all(isinstance(item, str) for item in value), f"{field} invalid")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for item in value:
        source_bound_ref(item, source, field)
    return value


def canonical_reviewed_at(value: Any, field: str) -> str:
    require(isinstance(value, str) and UTC_SECONDS.fullmatch(value) is not None,
            f"{field} must be canonical UTC RFC3339 seconds")
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise Fail(f"{field} is not a valid UTC timestamp") from exc
    require(parsed.strftime("%Y-%m-%dT%H:%M:%SZ") == value,
            f"{field} must be canonical UTC RFC3339 seconds")
    return value


def validate_review(record: dict[str, Any], ref_field: str, expected_role: str, source: str, contract: dict[str, Any]) -> str:
    ref = record.get(ref_field)
    require(isinstance(ref, str) and ref, f"{ref_field} invalid")
    source_bound_ref(ref, source, ref_field)
    review_dir = contract.get("independentReviewEvidenceDirectory")
    require(isinstance(review_dir, str) and review_dir, "independent review evidence directory authority missing")
    review_path = (ROOT / ref).resolve()
    review_base = (ROOT / review_dir).resolve()
    require(review_path.is_relative_to(review_base), f"{ref_field} must use monitored independent review evidence directory")
    review = load(review_path)
    required = set(contract.get("independentReviewRequiredFields", []))
    require(required == {
        "schemaVersion", "contactRoutingId", "observabilityStackId", "environmentIdentityDigest", "role",
        "reviewerId", "decision", "reviewedAt", "productionTrafficChanged", "credentialsIncluded",
        "automaticProductionPromotion",
    }, "independent review field authority drift")
    require(set(review) == required, f"{ref_field} field drift")
    require(review.get("schemaVersion") == contract.get("independentReviewSchemaVersion"),
            f"{ref_field} schema drift")
    require(review.get("contactRoutingId") == record.get("contactRoutingId"),
            f"{ref_field} contactRoutingId binding mismatch")
    require(review.get("observabilityStackId") == record.get("observabilityStackId"),
            f"{ref_field} observabilityStackId binding mismatch")
    require(review.get("environmentIdentityDigest") == record.get("environmentIdentityDigest"),
            f"{ref_field} environmentIdentityDigest binding mismatch")
    require(review.get("role") == expected_role, f"{ref_field} role must be {expected_role}")
    reviewer = review.get("reviewerId")
    require(isinstance(reviewer, str) and REVIEWER_ID.fullmatch(reviewer) is not None,
            f"{ref_field} reviewerId invalid")
    require(review.get("decision") == "APPROVED", f"{ref_field} decision must be APPROVED")
    canonical_reviewed_at(review.get("reviewedAt"), f"{ref_field}.reviewedAt")
    require(review.get("productionTrafficChanged") is False,
            f"{ref_field} cannot claim production traffic changes")
    require(review.get("credentialsIncluded") is False,
            f"{ref_field} cannot include production credentials")
    require(review.get("automaticProductionPromotion") is False,
            f"{ref_field} cannot authorize automatic production promotion")
    return reviewer


def validate_independent_reviews(record: dict[str, Any], source: str, contract: dict[str, Any]) -> None:
    privacy_ref = record.get("privacyReviewRef")
    operability_ref = record.get("operabilityReviewRef")
    require(isinstance(privacy_ref, str) and isinstance(operability_ref, str),
            "independent review refs invalid")
    require(privacy_ref != operability_ref, "privacy and operability review records must be distinct")
    privacy_reviewer = validate_review(record, "privacyReviewRef", "PRIVACY", source, contract)
    operability_reviewer = validate_review(record, "operabilityReviewRef", "OPERABILITY", source, contract)
    require(privacy_reviewer != operability_reviewer,
            "privacy and operability reviews require distinct reviewer identities")


def observability_stack(stack_id: str) -> dict[str, Any]:
    registry = load(OBS_REGISTRY)
    writer = load_observability_writer()
    try:
        writer.validate_registry_for_append(registry)
    except Exception as exc:
        raise Fail(f"observability stack authority invalid: {exc}") from exc
    rows = registry["stacks"]
    matches = [row for row in rows if row.get("stackId") == stack_id]
    require(len(matches) == 1, "observabilityStackId is not admitted exactly once")
    require(matches[0].get("evidenceComplete") is True, "observability stack evidence incomplete")
    return matches[0]


def generation_exists(generation_id: str) -> None:
    rows = load(GEN_REGISTRY).get("generations")
    require(isinstance(rows, list) and any(isinstance(row, dict) and row.get("generationId") == generation_id for row in rows), "environmentGenerationId is not registered")


def validate_record(record: dict[str, Any], confirmation: str) -> None:
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"record field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "record schemaVersion drift")
    require(isinstance(record.get("contactRoutingId"), str) and ROUTING_ID.fullmatch(record["contactRoutingId"]), "contactRoutingId invalid")
    environment = record.get("environmentClass")
    require(environment in contract.get("allowedEnvironmentClasses", []), "environmentClass invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source), "sourceCommitSha invalid")
    require(git("cat-file", "-e", source + "^{commit}") == "", "source commit does not exist")
    require(source_is_ancestor(source), "sourceCommitSha must be an ancestor of current HEAD")
    env_digest = record.get("environmentIdentityDigest")
    require(isinstance(env_digest, str) and DIGEST.fullmatch(env_digest), "environmentIdentityDigest invalid")

    stack_id = record.get("observabilityStackId")
    require(isinstance(stack_id, str) and stack_id, "observabilityStackId required")
    stack = observability_stack(stack_id)
    require(stack.get("environmentClass") == environment, "contact routing environment class must match observability stack")
    require(stack.get("environmentIdentityDigest") == env_digest, "contact routing environment identity must match observability stack")
    require(stack.get("sourceCommitSha") == source, "contact routing source commit must match observability stack")

    generation_id = record.get("environmentGenerationId")
    if environment == "PRODUCTION_EQUIVALENT":
        require(isinstance(generation_id, str) and generation_id, "production-equivalent routing requires environmentGenerationId")
        generation_exists(generation_id)
        require(stack.get("environmentGenerationId") == generation_id, "contact routing generation must match observability stack")
        require(record.get("productionEvidence") is False, "production-equivalent contact routing cannot be production evidence")
    else:
        require(generation_id is None, "production contact routing must not borrow a production-equivalent generation id")
        require(confirmation == PRODUCTION_CONFIRMATION, f"production contact routing requires confirmation: {PRODUCTION_CONFIRMATION}")
        require(record.get("productionEvidence") is True, "production contact routing must explicitly classify production evidence")

    bindings = record.get("contactBindings")
    require(isinstance(bindings, list), "contactBindings must be a list")
    required_classes = set(contract.get("requiredContactClasses", []))
    seen_classes: set[str] = set()
    owners: set[str] = set()
    for index, binding in enumerate(bindings):
        require(isinstance(binding, dict) and set(binding) == {"contactClass", "ownerRef", "destinationIdentityDigest", "escalationTargetIdentityDigest"}, f"contactBindings[{index}] field drift")
        contact_class = binding.get("contactClass")
        owner = binding.get("ownerRef")
        destination = binding.get("destinationIdentityDigest")
        escalation = binding.get("escalationTargetIdentityDigest")
        require(contact_class in required_classes and contact_class not in seen_classes, f"contactBindings[{index}].contactClass invalid/duplicate")
        require(isinstance(owner, str) and OWNER_REF.fullmatch(owner), f"contactBindings[{index}].ownerRef invalid")
        require(owner not in owners, "each required contact class must have a distinct operational owner")
        require(isinstance(destination, str) and DIGEST.fullmatch(destination), f"contactBindings[{index}].destinationIdentityDigest invalid")
        require(isinstance(escalation, str) and DIGEST.fullmatch(escalation), f"contactBindings[{index}].escalationTargetIdentityDigest invalid")
        seen_classes.add(contact_class)
        owners.add(owner)
    require(seen_classes == required_classes, f"required contact classes incomplete: {sorted(required_classes - seen_classes)}")

    for field in REF_FIELDS:
        refs(record.get(field), field, source)
    validate_independent_reviews(record, source, contract)

    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be a list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"unresolvedFindings[{index}] field drift")
        require(isinstance(finding.get("findingId"), str) and finding["findingId"], f"unresolvedFindings[{index}].findingId invalid")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "Critical/High findings block contact routing admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}].status invalid")
    require(record.get("evidenceComplete") is True, "evidenceComplete must be true")
    require(record.get("productionReady") is False, "contact routing evidence cannot make application productionReady")

    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in (
        "http://", "https://", "mailto:", "tel:", "@", "+81", "authorization: bearer",
        "password", "private_key", "access_key", "phone", "email", "account_id", "session_id",
    ):
        require(forbidden not in serialized, f"record contains forbidden contact or credential material: {forbidden}")


def validate_registry_for_append(registry: dict[str, Any], *, validate_rows: bool = True) -> None:
    require(registry.get("schemaVersion") == "memory-os-incident-contact-routing-admission-registry.v1",
            "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    routings = registry.get("routings")
    require(isinstance(routings, list) and all(isinstance(item, dict) for item in routings),
            "registry routings invalid")

    ids: set[str] = set()
    identities: set[str] = set()
    pe = 0
    prod = 0
    for index, record in enumerate(routings):
        if validate_rows:
            confirmation = PRODUCTION_CONFIRMATION if record.get("environmentClass") == "PRODUCTION" else ""
            try:
                validate_record(record, confirmation)
            except Exception as exc:
                raise Fail(f"routings[{index}] invalid: {exc}") from exc
        routing_id = record.get("contactRoutingId")
        identity = record.get("environmentIdentityDigest")
        require(isinstance(routing_id, str) and routing_id not in ids,
                f"duplicate/invalid contactRoutingId at routings[{index}]")
        require(isinstance(identity, str) and identity not in identities,
                f"duplicate/invalid environment identity at routings[{index}]")
        ids.add(routing_id)
        identities.add(identity)
        pe += 1 if record.get("environmentClass") == "PRODUCTION_EQUIVALENT" else 0
        prod += 1 if record.get("environmentClass") == "PRODUCTION" else 0

    expected_counts = {
        "admittedRoutingCount": len(routings),
        "productionEquivalentRoutingCount": pe,
        "productionRoutingCount": prod,
    }
    for field, expected in expected_counts.items():
        value = registry.get(field)
        require(type(value) is int and value == expected,
                f"{field} drift")
    require(registry.get("productionReady") is False,
            "registry cannot make application productionReady")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".incident-contact-routing.", suffix=".tmp", dir=REGISTRY.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, REGISTRY)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def commit_registry_candidate(original_registry: dict[str, Any], candidate_registry: dict[str, Any]) -> None:
    validate_registry_for_append(candidate_registry)
    atomic_write(candidate_registry)
    try:
        validate_registry_for_append(load(REGISTRY))
    except Exception:
        atomic_write(original_registry)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    record_path = Path(args.record).resolve()
    try:
        record_path.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise Fail("input record must be outside repository")
    require(git("status", "--porcelain") == "", "working tree must be clean")
    record = load(record_path)
    validate_record(record, args.confirm)

    try:
        lock_fd = os.open(LOCK, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise Fail("incident contact routing registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["contactRoutingId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        original_registry = load(REGISTRY)
        validate_registry_for_append(original_registry)
        registry = json.loads(json.dumps(original_registry))
        routings = registry["routings"]
        require(all(item.get("contactRoutingId") != record["contactRoutingId"] for item in routings), "contactRoutingId already registered")
        require(all(item.get("environmentIdentityDigest") != record["environmentIdentityDigest"] for item in routings), "environment identity already has contact routing admission")
        routings.append(record)
        registry["admittedRoutingCount"] = len(routings)
        registry["productionEquivalentRoutingCount"] = sum(1 for item in routings if item.get("environmentClass") == "PRODUCTION_EQUIVALENT")
        registry["productionRoutingCount"] = sum(1 for item in routings if item.get("environmentClass") == "PRODUCTION")
        registry["productionReady"] = False
        commit_registry_candidate(original_registry, registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    print(f"Registered incident contact routing evidence: {record['contactRoutingId']}")
    print("Application production readiness remains false.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"INCIDENT CONTACT ROUTING REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
