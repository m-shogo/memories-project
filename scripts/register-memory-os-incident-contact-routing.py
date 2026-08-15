#!/usr/bin/env python3
"""Register one reviewed incident-contact routing evidence record."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/incident-contact-routing-admission-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/incident-contact-routing-admission-registry.v1.json"
OBS_REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
LOCK = ROOT / "contracts/operations/.incident-contact-routing.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
ROUTING_ID = re.compile(r"^icr_[a-z0-9][a-z0-9_-]{7,63}$")
OWNER_REF = re.compile(r"^owner_[a-z0-9][a-z0-9_-]{5,63}$")
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
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def git(*args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def refs(value: Any, field: str) -> list[str]:
    require(isinstance(value, list) and value, f"{field} must be non-empty")
    require(all(isinstance(item, str) and item and not Path(item).is_absolute() and ".." not in Path(item).parts for item in value), f"{field} invalid")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for item in value:
        require((ROOT / item).is_file(), f"{field} evidence path missing: {item}")
    return value


def observability_stack(stack_id: str) -> dict[str, Any]:
    registry = load(OBS_REGISTRY)
    rows = registry.get("stacks")
    require(isinstance(rows, list), "observability stack registry missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("stackId") == stack_id]
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
        refs(record.get(field), field)
    for field in ("privacyReviewRef", "operabilityReviewRef"):
        value = record.get(field)
        require(isinstance(value, str) and value and not Path(value).is_absolute() and ".." not in Path(value).parts and (ROOT / value).is_file(), f"{field} invalid")
    require(record["privacyReviewRef"] != record["operabilityReviewRef"], "privacy and operability review records must be distinct")

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
        registry = load(REGISTRY)
        validate_registry_for_append(registry)
        routings = registry["routings"]
        require(all(item.get("contactRoutingId") != record["contactRoutingId"] for item in routings), "contactRoutingId already registered")
        require(all(item.get("environmentIdentityDigest") != record["environmentIdentityDigest"] for item in routings), "environment identity already has contact routing admission")
        routings.append(record)
        registry["admittedRoutingCount"] = len(routings)
        registry["productionEquivalentRoutingCount"] = sum(1 for item in routings if item.get("environmentClass") == "PRODUCTION_EQUIVALENT")
        registry["productionRoutingCount"] = sum(1 for item in routings if item.get("environmentClass") == "PRODUCTION")
        registry["productionReady"] = False
        atomic_write(registry)
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
