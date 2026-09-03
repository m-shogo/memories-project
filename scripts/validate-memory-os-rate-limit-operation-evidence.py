#!/usr/bin/env python3
"""Fail-closed validator for append-only rate-limit operation evidence."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/rate-limit-operation-evidence-contract.v1.json"
OPERATIONS_PATH = ROOT / "contracts/operations/rate-limit-operations-contract.v1.json"
POLICY_PATH = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
LEDGER_PATH = ROOT / "docs/evidence/rate-limit-operations"
TEMPLATE_PATH = ROOT / "docs/fixtures/memory-os-operability/rate-limit-operation-record.template.v1.json"
REQUIRED_RECORD_FIELDS = {
    "schemaVersion", "operationId", "incidentReference", "sourceCommitSha",
    "environment", "operator", "reviewer", "previousMode", "newMode",
    "proxyMode", "affectedPolicyIds", "startedAt", "expiresAt",
    "activationReason", "lifecycle", "productionConfirmation",
    "verificationResults", "restoredAt", "openRisks", "evidenceRefs",
    "evidenceDigestsByRef",
}
SAFE_RISK_RE = re.compile(r"^[a-z0-9][a-z0-9_:-]{2,127}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REPO_REF_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
IPV4_RE = re.compile(r"(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://|postgres(?:ql)?://|s3://", re.IGNORECASE)
SECRET_WORD_RE = re.compile(
    r"(?:password|passwd|secret|private[_ -]?key|access[_ -]?key|bearer|authorization|token)",
    re.IGNORECASE,
)
IDENTITY_WORD_RE = re.compile(
    r"(?:account[_ -]?id|session[_ -]?id|request[_ -]?id|apple[_ -]?subject|network[_ -]?digest|ip[_ -]?address)",
    re.IGNORECASE,
)


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def require_source_ancestor(source_sha: str, _run=subprocess.run) -> None:
    if subprocess.run is not _run:
        raise ValidationFailure("source ancestry execution transport drift")
    completed = _run(
        ["git", "merge-base", "--is-ancestor", source_sha, "HEAD"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    require(completed.returncode == 0,
            "sourceCommitSha must be an ancestor of current HEAD")


def git_bytes(*args: str, _run=subprocess.run) -> bytes:
    if subprocess.run is not _run:
        raise ValidationFailure("git evidence execution transport drift")
    completed = _run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode == 0, f"git {' '.join(args)} failed")
    return completed.stdout


def canonical_evidence_path(ref: str, field: str) -> Path:
    candidate = ROOT / ref
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(ROOT.resolve())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise ValidationFailure(f"{field} evidence path invalid: {ref}") from exc
    require(resolved.is_file(), f"{field} evidence path missing: {ref}")
    current = ROOT
    for part in Path(ref).parts:
        current = current / part
        require(not current.is_symlink(),
                f"{field} evidence path cannot traverse symlink: {ref}")
    git_bytes("ls-files", "--error-unmatch", "--", ref)
    require(git_bytes("show", f"HEAD:{ref}") == resolved.read_bytes(),
            f"{field} evidence must match committed HEAD bytes: {ref}")
    return resolved


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def parse_rfc3339(value: Any, field: str) -> dt.datetime:
    require(isinstance(value, str) and value.endswith("Z"),
            f"{field} must be an RFC3339 UTC timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationFailure(f"{field} is not a valid timestamp") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0),
            f"{field} must be UTC")
    return parsed


def validate_repo_refs(value: Any, field: str, *, require_existing: bool) -> list[str]:
    require(isinstance(value, list), f"{field} must be a list")
    require(all(isinstance(item, str) and item for item in value),
            f"{field} contains an invalid reference")
    require(len(value) == len(set(value)), f"{field} contains duplicate references")
    for ref in value:
        require(REPO_REF_RE.fullmatch(ref) is not None,
                f"{field} contains a non-repository reference: {ref}")
        require(not ref.startswith("/") and ".." not in Path(ref).parts,
                f"{field} contains path traversal: {ref}")
        if require_existing:
            canonical_evidence_path(ref, field)
    return value


def all_evidence_refs(record: dict[str, Any]) -> list[str]:
    refs: set[str] = set()
    top_level = record.get("evidenceRefs")
    if isinstance(top_level, list):
        refs.update(ref for ref in top_level if isinstance(ref, str) and ref)
    verification = record.get("verificationResults")
    if isinstance(verification, list):
        for item in verification:
            if not isinstance(item, dict):
                continue
            values = item.get("evidenceRefs")
            if isinstance(values, list):
                refs.update(ref for ref in values if isinstance(ref, str) and ref)
    return sorted(refs)


def expected_evidence_digests(record: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for ref in all_evidence_refs(record):
        path = canonical_evidence_path(ref, "evidenceDigestsByRef")
        result[ref] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def iter_string_values(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, str):
        result.append(value)
    elif isinstance(value, list):
        for item in value:
            result.extend(iter_string_values(item))
    elif isinstance(value, dict):
        for item in value.values():
            result.extend(iter_string_values(item))
    return result


def load_contract_context() -> tuple[dict[str, Any], set[str]]:
    contract = load_json(CONTRACT_PATH)
    policy = load_json(POLICY_PATH)
    policy_items = policy.get("policies")
    require(isinstance(policy_items, list) and policy_items,
            "primary rate-limit policies must be a non-empty list")
    policy_ids = {
        item.get("policyId") for item in policy_items
        if isinstance(item, dict) and isinstance(item.get("policyId"), str)
    }
    require(len(policy_ids) == len(policy_items),
            "primary rate-limit policy IDs are invalid or duplicated")
    return contract, policy_ids


def validate_record(record: dict[str, Any], contract: dict[str, Any],
                    policy_ids: set[str], *, template: bool = False,
                    writer_input: bool = False) -> None:
    require(set(record) == REQUIRED_RECORD_FIELDS,
            f"record field set drift: {sorted(set(record) ^ REQUIRED_RECORD_FIELDS)}")
    require(record.get("schemaVersion") == contract.get("recordSchemaVersion"),
            "record schemaVersion drift")
    rules = contract.get("record")
    require(isinstance(rules, dict), "record rules must be an object")

    if template:
        require(record.get("operationId") == "RLOP-YYYYMMDDTHHMMSSZ-replace",
                "template operationId drift")
        require(record.get("sourceCommitSha") == "0" * 40,
                "template sourceCommitSha drift")
        require(record.get("lifecycle") == "PLANNED",
                "template lifecycle drift")
        require(record.get("evidenceDigestsByRef") == {},
                "template evidenceDigestsByRef must be empty")
        return

    operation_id = record.get("operationId")
    require(isinstance(operation_id, str) and
            re.fullmatch(rules["operationIdPattern"], operation_id) is not None,
            "operationId does not match the contract pattern")
    incident = record.get("incidentReference")
    require(isinstance(incident, str) and
            re.fullmatch(rules["incidentReferencePattern"], incident) is not None,
            "incidentReference does not match the contract pattern")
    source_sha = record.get("sourceCommitSha")
    require(isinstance(source_sha, str) and SHA_RE.fullmatch(source_sha) is not None and
            source_sha != "0" * 40,
            "sourceCommitSha must be a non-placeholder full SHA")
    require_source_ancestor(source_sha)

    require(record.get("environment") in set(rules["environmentValues"]),
            "environment is not allowed")
    operator = record.get("operator")
    reviewer = record.get("reviewer")
    actor_pattern = rules["actorPattern"]
    require(isinstance(operator, str) and re.fullmatch(actor_pattern, operator) is not None,
            "operator handle is invalid")
    require(isinstance(reviewer, str) and re.fullmatch(actor_pattern, reviewer) is not None,
            "reviewer handle is invalid")
    require(operator != reviewer, "operator and reviewer must differ")

    modes = set(rules["modeValues"])
    require(record.get("previousMode") in modes, "previousMode is not allowed")
    require(record.get("newMode") in modes, "newMode is not allowed")
    require(record.get("previousMode") != record.get("newMode"),
            "operation must change mode")
    require(record.get("proxyMode") in set(rules["proxyModeValues"]),
            "proxyMode is not allowed")
    require(record.get("activationReason") in set(rules["activationReasonValues"]),
            "activationReason is not allowed")
    lifecycle = record.get("lifecycle")
    require(lifecycle in set(rules["lifecycleValues"]), "lifecycle is not allowed")

    affected = record.get("affectedPolicyIds")
    require(isinstance(affected, list) and affected,
            "affectedPolicyIds must be a non-empty list")
    require(all(isinstance(item, str) for item in affected),
            "affectedPolicyIds contains invalid values")
    require(len(affected) == len(set(affected)),
            "affectedPolicyIds contains duplicates")
    unknown_policies = set(affected) - policy_ids
    require(not unknown_policies,
            f"affectedPolicyIds references unknown policies: {sorted(unknown_policies)}")

    started = parse_rfc3339(record.get("startedAt"), "startedAt")
    expires = parse_rfc3339(record.get("expiresAt"), "expiresAt")
    require(expires > started, "expiresAt must be after startedAt")
    duration = expires - started
    require(duration <= dt.timedelta(minutes=rules["maximumEmergencyDurationMinutes"]),
            "operation exceeds the maximum emergency duration")

    production_confirmation = record.get("productionConfirmation")
    if record.get("environment") == "PRODUCTION":
        require(production_confirmation ==
                "I CONFIRM RATE LIMIT OPERATION IN PRODUCTION",
                "production operation confirmation is missing")
    else:
        require(production_confirmation is None,
                "non-production record must not contain production confirmation")

    verification = record.get("verificationResults")
    require(isinstance(verification, list), "verificationResults must be a list")
    required_checks = set(rules["requiredVerificationChecks"])
    by_check: dict[str, dict[str, Any]] = {}
    for item in verification:
        require(isinstance(item, dict) and set(item) ==
                {"checkId", "result", "evidenceRefs"},
                "verification result field set drift")
        check_id = item.get("checkId")
        require(check_id in required_checks, f"unknown verification check: {check_id}")
        require(check_id not in by_check, f"duplicate verification check: {check_id}")
        require(item.get("result") in set(rules["verificationResultValues"]),
                f"invalid verification result: {check_id}")
        refs = item.get("evidenceRefs")
        validate_repo_refs(
            refs,
            f"verificationResults.{check_id}.evidenceRefs",
            require_existing=bool(refs),
        )
        if item.get("result") == "PASS":
            require(refs,
                    f"PASS verification requires evidenceRefs: {check_id}")
        by_check[check_id] = item
    require(set(by_check) == required_checks,
            f"verification check set drift: {sorted(set(by_check) ^ required_checks)}")

    restored_at = record.get("restoredAt")
    open_risks = record.get("openRisks")
    require(isinstance(open_risks, list) and
            all(isinstance(item, str) and SAFE_RISK_RE.fullmatch(item)
                for item in open_risks),
            "openRisks must contain only bounded risk identifiers")
    require(len(open_risks) == len(set(open_risks)), "openRisks contains duplicates")

    results = [item["result"] for item in by_check.values()]
    if lifecycle == "PLANNED":
        require(all(result == "NOT_RUN" for result in results),
                "PLANNED record may not claim verification results")
        require(restored_at is None, "PLANNED record cannot have restoredAt")
    elif lifecycle == "ACTIVE":
        require(restored_at is None, "ACTIVE record cannot have restoredAt")
        require("FAIL" not in results, "ACTIVE record with failed verification must be FAILED")
    elif lifecycle == "RESTORED":
        require(all(result == "PASS" for result in results),
                "RESTORED requires every verification check to PASS")
        restored = parse_rfc3339(restored_at, "restoredAt")
        require(restored >= started, "restoredAt precedes startedAt")
        require(not open_risks, "RESTORED record cannot retain open risks")
    elif lifecycle == "FAILED":
        require("FAIL" in results, "FAILED record requires a failed verification check")
        require(open_risks, "FAILED record requires at least one open risk")
        if restored_at is not None:
            parse_rfc3339(restored_at, "restoredAt")

    validate_repo_refs(record.get("evidenceRefs"), "evidenceRefs",
                       require_existing=True)

    digests = record.get("evidenceDigestsByRef")
    require(isinstance(digests, dict), "evidenceDigestsByRef must be an object")
    if writer_input:
        require(digests == {}, "writer input evidenceDigestsByRef must be empty")
    else:
        expected_digests = expected_evidence_digests(record)
        require(set(digests) == set(expected_digests),
                "evidenceDigestsByRef reference set drift")
        require(all(isinstance(value, str) and SHA256_RE.fullmatch(value)
                    for value in digests.values()),
                "evidenceDigestsByRef contains an invalid SHA-256 digest")
        require(digests == expected_digests,
                "evidenceDigestsByRef does not match current evidence bytes")

    values = iter_string_values(record)
    for value in values:
        require(URL_RE.search(value) is None, "record contains a raw URL")
        require(EMAIL_RE.search(value) is None, "record contains an email address")
        require(IPV4_RE.search(value) is None, "record contains a raw IPv4 address")
        if value not in required_checks and value not in rules["activationReasonValues"]:
            require(SECRET_WORD_RE.search(value) is None,
                    "record contains secret/token-like free text")
            require(IDENTITY_WORD_RE.search(value) is None,
                    "record contains identity-like free text")


def require_runtime_authorities(
    _root: Path = ROOT,
    _paths: tuple[tuple[str, Path, bool], ...] = (
        ("CONTRACT_PATH", CONTRACT_PATH, False),
        ("OPERATIONS_PATH", OPERATIONS_PATH, False),
        ("POLICY_PATH", POLICY_PATH, False),
        ("STATUS_PATH", STATUS_PATH, False),
        ("LEDGER_PATH", LEDGER_PATH, True),
        ("TEMPLATE_PATH", TEMPLATE_PATH, False),
    ),
    _record_fields: tuple[str, ...] = tuple(sorted(REQUIRED_RECORD_FIELDS)),
    _regex_semantics: tuple[tuple[str, int], ...] = tuple(
        (pattern.pattern, pattern.flags)
        for pattern in (
            SAFE_RISK_RE, SHA_RE, SHA256_RE, REPO_REF_RE, IPV4_RE,
            EMAIL_RE, URL_RE, SECRET_WORD_RE, IDENTITY_WORD_RE,
        )
    ),
    _helpers: tuple[tuple[str, object], ...] = (
        ("require", require),
        ("require_source_ancestor", require_source_ancestor),
        ("git_bytes", git_bytes),
        ("canonical_evidence_path", canonical_evidence_path),
        ("load_json", load_json),
        ("parse_rfc3339", parse_rfc3339),
        ("validate_repo_refs", validate_repo_refs),
        ("all_evidence_refs", all_evidence_refs),
        ("expected_evidence_digests", expected_evidence_digests),
        ("iter_string_values", iter_string_values),
        ("load_contract_context", load_contract_context),
        ("validate_record", validate_record),
    ),
) -> None:
    if ROOT != _root or ROOT.resolve() != _root.resolve():
        raise ValidationFailure("operation evidence validator repository root authority drift")
    root = _root.resolve()
    for label, canonical, is_directory in _paths:
        current = globals().get(label)
        if current != canonical:
            raise ValidationFailure(f"operation evidence validator {label} authority drift")
        if current.is_symlink():
            raise ValidationFailure(f"operation evidence validator {label} cannot be a symlink")
        try:
            resolved = current.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ValidationFailure(f"operation evidence validator {label} missing") from exc
        if not resolved.is_relative_to(root):
            raise ValidationFailure(f"operation evidence validator {label} escapes repository")
        if is_directory:
            if not current.is_dir():
                raise ValidationFailure(f"operation evidence validator {label} must be a directory")
        elif not current.is_file():
            raise ValidationFailure(f"operation evidence validator {label} must be a file")
    if tuple(sorted(REQUIRED_RECORD_FIELDS)) != _record_fields:
        raise ValidationFailure("operation evidence required record field semantics drift")
    current_regex_semantics = tuple(
        (pattern.pattern, pattern.flags)
        for pattern in (
            SAFE_RISK_RE, SHA_RE, SHA256_RE, REPO_REF_RE, IPV4_RE,
            EMAIL_RE, URL_RE, SECRET_WORD_RE, IDENTITY_WORD_RE,
        )
    )
    if current_regex_semantics != _regex_semantics:
        raise ValidationFailure("operation evidence regex semantic authority drift")
    for name, canonical in _helpers:
        if globals().get(name) is not canonical:
            raise ValidationFailure(f"operation evidence validator {name} execution authority drift")


def _build_main(
    _canonical_guard=require_runtime_authorities,
    _canonical_guard_defaults=require_runtime_authorities.__defaults__,
):
    def _main() -> int:
        if require_runtime_authorities is not _canonical_guard:
            raise ValidationFailure("operation evidence validator runtime guard authority drift")
        if _canonical_guard.__defaults__ != _canonical_guard_defaults:
            raise ValidationFailure("operation evidence validator runtime guard default authority drift")
        _canonical_guard()
        contract, policy_ids = load_contract_context()
        require(contract.get("schemaVersion") ==
                "memory-os-rate-limit-operation-evidence.v1",
                "operation evidence contract schemaVersion drift")
        require(contract.get("recordSchemaVersion") ==
                "memory-os-rate-limit-operation-record.v2",
                "operation record schemaVersion drift")
        expected_paths = {
            "sourceOperationsContract": "contracts/operations/rate-limit-operations-contract.v1.json",
            "sourcePolicyContract": "contracts/operations/rate-limit-policy-contract.v1.json",
            "ledgerDirectory": "docs/evidence/rate-limit-operations",
            "template": "docs/fixtures/memory-os-operability/rate-limit-operation-record.template.v1.json",
            "writer": "scripts/create-memory-os-rate-limit-operation-evidence.py",
            "validator": "scripts/validate-memory-os-rate-limit-operation-evidence.py",
        }
        for field, expected in expected_paths.items():
            require(contract.get(field) == expected, f"{field} path drift")

        rules = contract.get("record")
        require(isinstance(rules, dict), "record rules must be an object")
        require("UNLIMITED_OR_FAIL_OPEN" not in set(rules.get("modeValues", [])),
                "evidence contract permits forbidden fail-open mode")
        require("ARBITRARY_FORWARDED_HEADERS" not in
                set(rules.get("proxyModeValues", [])),
                "evidence contract permits arbitrary forwarded headers")
        require(rules.get("maximumEmergencyDurationMinutes") == 60,
                "maximum emergency duration drift")
        for flag in (
            "fullSourceCommitShaRequired", "sourceCommitMustBeAncestorOfCurrentHead",
            "operatorReviewerMustDiffer", "productionRequiresConfirmation",
            "restoredRequiresAllChecksPass", "failedRequiresOpenRisk", "appendOnly",
            "writerComputesEvidenceDigests", "evidenceDigestsCoverEveryEvidenceRef",
            "evidenceDigestsUseSha256",
        ):
            require(rules.get(flag) is True, f"record.{flag} must be true")

        privacy = contract.get("privacy")
        require(isinstance(privacy, dict), "privacy must be an object")
        require(privacy.get("classification") == "operational_sensitive_no_secrets",
                "privacy classification drift")
        for flag in (
            "rawIpForbidden", "networkDigestForbidden", "tokenForbidden",
            "accountOrSessionIdentifierForbidden", "requestContentForbidden",
            "rawUrlForbidden", "databaseOrStoreCredentialForbidden",
            "freeFormEvidenceTextForbidden", "evidenceRefsMustBeRepositoryRelative",
            "evidenceRefsMustBeTracked", "evidenceRefsMustBeSymlinkFree",
            "evidenceRefsMustMatchHeadBytes",
        ):
            require(privacy.get(flag) is True, f"privacy.{flag} must be true")

        template = load_json(TEMPLATE_PATH)
        validate_record(template, contract, policy_ids, template=True)

        LEDGER_PATH.mkdir(parents=True, exist_ok=True)
        records = sorted(LEDGER_PATH.glob("*.json"))
        operation_ids: set[str] = set()
        for path in records:
            record = load_json(path)
            validate_record(record, contract, policy_ids)
            operation_id = record["operationId"]
            require(path.name == f"{operation_id}.json",
                    f"ledger filename does not match operationId: {path.name}")
            require(operation_id not in operation_ids,
                    f"duplicate operationId across ledger: {operation_id}")
            operation_ids.add(operation_id)

        readiness = contract.get("readiness")
        require(isinstance(readiness, dict), "readiness must be an object")
        for foundation in (
            "recordContractDefined", "exclusiveWriterImplemented",
            "ledgerValidatorImplemented", "duplicateOperationIdRejected",
            "privacyValidationImplemented",
        ):
            require(readiness.get(foundation) is True,
                    f"readiness.{foundation} must be true")
        for unproven in (
            "productionControlPlaneImplemented", "automaticModeExpiryImplemented",
            "productionEvidenceRecorded", "operatorReviewCompleted", "productionReady",
        ):
            require(readiness.get(unproven) is False,
                    f"unproven operation evidence readiness cannot be true: {unproven}")

        refs = contract.get("evidenceRefs")
        require(isinstance(refs, list) and len(refs) == len(set(refs)),
                "operation evidenceRefs invalid")
        for ref in refs:
            require((ROOT / ref).is_file(), f"evidence path missing: {ref}")

        operations = load_json(OPERATIONS_PATH)
        operations_readiness = operations.get("readiness")
        require(isinstance(operations_readiness, dict),
                "rate-limit operations readiness must be an object")
        require(operations_readiness.get("productionControlPlaneImplemented") is False,
                "ledger cannot imply a production control plane")

        status = load_json(STATUS_PATH)
        require(status.get("productionDecision") == "NO_GO",
                "operation evidence cannot change production decision")
        areas = status.get("areas")
        require(isinstance(areas, list), "status areas must be a list")
        matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-005"]
        require(len(matches) == 1, "OPS-P0-005 must exist exactly once")
        require(matches[0].get("status") != "READY",
                "evidence ledger without control plane/shared store cannot make OPS-P0-005 READY")

        print("Memory OS rate-limit operation evidence validation PASS")
        print(f"registered operation records: {len(records)}")
        print("production control plane: NOT_IMPLEMENTED")
        print("production decision: NO_GO")
        return 0

    return _main


main = _build_main()
del _build_main


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"RATE-LIMIT OPERATION EVIDENCE VALIDATION FAILED: {exc}",
              file=sys.stderr)
        raise SystemExit(1)
