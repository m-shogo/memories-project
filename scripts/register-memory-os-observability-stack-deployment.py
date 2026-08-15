#!/usr/bin/env python3
"""Register one integrated observability-stack deployment evidence record."""

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
CONTRACT = ROOT / "contracts/operations/observability-stack-deployment-contract.v1.json"
REGISTRY = ROOT / "contracts/operations/observability-stack-deployment-registry.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
LOCK = ROOT / "contracts/operations/.observability-stack-deployment.lock"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
STACK_ID = re.compile(r"^obsstack_[a-z0-9][a-z0-9_-]{7,63}$")
PRODUCTION_CONFIRMATION = "REGISTER PRODUCTION OBSERVABILITY STACK EVIDENCE"
REF_FIELDS = (
    "infrastructureAsCodeRefs", "structuredLogEvidenceRefs", "metricsEvidenceRefs",
    "accessAuditEvidenceRefs", "pagingEvidenceRefs", "retentionDeletionEvidenceRefs",
)
DIGEST_FIELDS = (
    "environmentIdentityDigest", "structuredLogBackendIdentityDigest",
    "metricsBackendIdentityDigest", "accessAuditSinkIdentityDigest",
    "pagingDestinationIdentityDigest",
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
    require(not path.is_symlink(), f"{field} evidence cannot be a symlink: {item}")
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


def evidence_refs(value: Any, field: str, source: str) -> list[str]:
    require(isinstance(value, list) and value, f"{field} must be non-empty")
    require(all(isinstance(item, str) for item in value), f"{field} invalid")
    require(len(value) == len(set(value)), f"{field} contains duplicates")
    for item in value:
        source_bound_ref(item, source, field)
    return value


def validate_record(record: dict[str, Any], confirmation: str) -> None:
    contract = load(CONTRACT)
    required = set(contract.get("requiredRecordFields", []))
    require(set(record) == required, f"record field set drift: {sorted(set(record) ^ required)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"), "record schemaVersion drift")
    require(isinstance(record.get("stackId"), str) and STACK_ID.fullmatch(record["stackId"]), "stackId invalid")
    environment = record.get("environmentClass")
    require(environment in contract.get("allowedEnvironmentClasses", []), "environmentClass invalid")
    source = record.get("sourceCommitSha")
    require(isinstance(source, str) and SHA40.fullmatch(source), "sourceCommitSha invalid")
    require(git("cat-file", "-e", source + "^{commit}") == "", "source commit does not exist")
    require(source_is_ancestor(source), "sourceCommitSha must be an ancestor of current HEAD")
    for field in DIGEST_FIELDS:
        require(isinstance(record.get(field), str) and DIGEST.fullmatch(record[field]), f"{field} must be SHA-256 digest")
    for field in REF_FIELDS:
        evidence_refs(record.get(field), field, source)
    for field in ("securityReviewRef", "operabilityReviewRef"):
        value = record.get(field)
        require(isinstance(value, str), f"{field} invalid")
        source_bound_ref(value, source, field)
    require(record["securityReviewRef"] != record["operabilityReviewRef"],
            "security and operability review evidence must be distinct")
    findings = record.get("unresolvedFindings")
    require(isinstance(findings, list), "unresolvedFindings must be a list")
    for index, finding in enumerate(findings):
        require(isinstance(finding, dict) and set(finding) == {"findingId", "severity", "status"}, f"unresolvedFindings[{index}] field drift")
        require(isinstance(finding.get("findingId"), str) and finding["findingId"], f"unresolvedFindings[{index}].findingId invalid")
        require(finding.get("severity") in {"LOW", "MEDIUM"}, "Critical/High findings block observability admission")
        require(finding.get("status") in {"OPEN", "ACCEPTED_WITH_OWNER"}, f"unresolvedFindings[{index}].status invalid")
    require(record.get("evidenceComplete") is True, "evidenceComplete must be true")
    require(record.get("productionReady") is False, "observability stack evidence cannot make application productionReady")
    generation = record.get("environmentGenerationId")
    if environment == "PRODUCTION_EQUIVALENT":
        require(isinstance(generation, str) and generation, "production-equivalent stack requires environmentGenerationId")
        generations = load(GEN_REGISTRY)
        rows = generations.get("generations")
        require(isinstance(rows, list) and any(isinstance(row, dict) and row.get("generationId") == generation for row in rows), "environmentGenerationId is not registered")
        require(record.get("productionEvidence") is False, "production-equivalent stack cannot be production evidence")
    else:
        require(generation is None, "production stack must not borrow a production-equivalent generation id")
        require(confirmation == PRODUCTION_CONFIRMATION, f"production record requires confirmation: {PRODUCTION_CONFIRMATION}")
        require(record.get("productionEvidence") is True, "production stack record must explicitly classify itself as production evidence")
    serialized = json.dumps(record, ensure_ascii=False).lower()
    for forbidden in ("http://", "https://", "postgres://", "postgresql://", "@", "password", "private_key", "access_key", "bearer "):
        require(forbidden not in serialized, f"record contains forbidden material: {forbidden}")


def validate_registry_for_append(registry: dict[str, Any], *, validate_rows: bool = True) -> None:
    require(registry.get("schemaVersion") == "memory-os-observability-stack-deployment-registry.v1",
            "registry schema drift")
    require(registry.get("appendOnly") is True, "registry must remain append-only")
    stacks = registry.get("stacks")
    require(isinstance(stacks, list) and all(isinstance(item, dict) for item in stacks),
            "registry stacks invalid")

    ids: set[str] = set()
    identities: set[str] = set()
    pe = 0
    prod = 0
    for index, record in enumerate(stacks):
        if validate_rows:
            confirmation = PRODUCTION_CONFIRMATION if record.get("environmentClass") == "PRODUCTION" else ""
            try:
                validate_record(record, confirmation)
            except Exception as exc:
                raise Fail(f"stacks[{index}] invalid: {exc}") from exc
        stack_id = record.get("stackId")
        identity = record.get("environmentIdentityDigest")
        require(isinstance(stack_id, str) and stack_id not in ids,
                f"duplicate/invalid stackId at stacks[{index}]")
        require(isinstance(identity, str) and identity not in identities,
                f"duplicate/invalid environment identity at stacks[{index}]")
        ids.add(stack_id)
        identities.add(identity)
        pe += 1 if record.get("environmentClass") == "PRODUCTION_EQUIVALENT" else 0
        prod += 1 if record.get("environmentClass") == "PRODUCTION" else 0

    expected_counts = {
        "admittedStackCount": len(stacks),
        "productionEquivalentStackCount": pe,
        "productionStackCount": prod,
    }
    for field, expected in expected_counts.items():
        value = registry.get(field)
        require(type(value) is int and value == expected, f"{field} drift")
    require(registry.get("productionReady") is False,
            "stack registry cannot make application productionReady")


def atomic_write(value: dict[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=".observability-stack.", suffix=".tmp", dir=REGISTRY.parent)
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
        raise Fail("observability stack registry lock already exists") from exc
    try:
        os.write(lock_fd, (record["stackId"] + "\n").encode("ascii"))
        os.fsync(lock_fd)
        registry = load(REGISTRY)
        validate_registry_for_append(registry)
        stacks = registry["stacks"]
        require(all(item.get("stackId") != record["stackId"] for item in stacks), "stackId already registered")
        require(all(item.get("environmentIdentityDigest") != record["environmentIdentityDigest"] for item in stacks), "environment identity already registered")
        stacks.append(record)
        registry["admittedStackCount"] = len(stacks)
        registry["productionEquivalentStackCount"] = sum(1 for item in stacks if item.get("environmentClass") == "PRODUCTION_EQUIVALENT")
        registry["productionStackCount"] = sum(1 for item in stacks if item.get("environmentClass") == "PRODUCTION")
        registry["productionReady"] = False
        atomic_write(registry)
    finally:
        os.close(lock_fd)
        try:
            LOCK.unlink()
        except FileNotFoundError:
            pass
    print(f"Registered observability stack evidence: {record['stackId']}")
    print("Application production readiness remains false.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OBSERVABILITY STACK REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
