#!/usr/bin/env python3
"""Offline logical validator for Memory OS PostgreSQL tenant RLS contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CONTRACT_PATH = Path(
    "docs/fixtures/memory-os-security/"
    "postgresql-tenant-rls-contract.round9.valid.v1.json"
)
CASE_SET_PATH = Path(
    "docs/fixtures/memory-os-security/"
    "postgresql-rls-cases.round9.v1.json"
)

RUNTIME_ROLES = {
    "memory_api_runtime",
    "memory_worker_runtime",
    "memory_deletion_runtime",
}
IMMUTABLE_AFTER_INSERT = {
    "import_preview",
    "apply_confirmation",
    "import_report",
}


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure(f"expected JSON object: {path}")
    return value


def index_unique(items: list[dict[str, Any]], field: str, label: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item[field]
        if key in output:
            raise ValidationFailure(f"duplicate {label}: {key}")
        output[key] = item
    return output


def validate_contract(contract: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    roles = index_unique(contract["roles"], "role", "role")
    profiles = index_unique(contract["policyProfiles"], "profileId", "policy profile")
    tables = index_unique(contract["tables"], "table", "table")

    for role_name, role in roles.items():
        if role.get("bypassRls") is not False:
            raise ValidationFailure(f"role may bypass RLS: {role_name}")
        if role_name in RUNTIME_ROLES:
            if role.get("login") is not False or role.get("inherit") is not False:
                raise ValidationFailure(
                    f"privilege role must be NOLOGIN NOINHERIT: {role_name}"
                )
            if role.get("ownsUserTables") is not False:
                raise ValidationFailure(f"runtime role owns user tables: {role_name}")

    migration_owner = roles.get("memory_migration_owner")
    if not migration_owner or migration_owner.get("ownsUserTables") is not True:
        raise ValidationFailure("memory_migration_owner must own user tables")

    for table_name, table in tables.items():
        if table.get("rlsEnabled") is not True or table.get("forceRls") is not True:
            raise ValidationFailure(f"RLS and FORCE RLS required: {table_name}")
        if table.get("runtimeRoleOwnsTable") is not False:
            raise ValidationFailure(f"runtime table ownership forbidden: {table_name}")
        profile_id = table["policyProfileId"]
        if profile_id not in profiles:
            raise ValidationFailure(
                f"table references missing policy profile: {table_name} -> {profile_id}"
            )
        profile = profiles[profile_id]
        for command in ("select", "insert", "update", "delete"):
            role_field = f"{command}Roles"
            unknown = set(profile[role_field]) - RUNTIME_ROLES
            if unknown:
                raise ValidationFailure(
                    f"unknown runtime role in {profile_id}.{role_field}: {sorted(unknown)}"
                )

        delete_roles = set(profile["deleteRoles"])
        if delete_roles != {"memory_deletion_runtime"}:
            raise ValidationFailure(
                f"only deletion runtime may delete {table_name}: {sorted(delete_roles)}"
            )
        if table_name in IMMUTABLE_AFTER_INSERT and profile["updateRoles"]:
            raise ValidationFailure(
                f"immutable security object exposes UPDATE: {table_name}"
            )

    rules = contract["globalRules"]
    required_true = {
        "denyByDefault",
        "runtimeBypassRlsForbidden",
        "runtimeTableOwnershipForbidden",
        "loginCredentialsSeparatedFromPrivilegeRoles",
    }
    required_false = {
        "clientSetsSessionContext",
        "ownerMutationAllowed",
        "epochDowngradeAllowed",
        "rawSqlWithoutScopedTransactionAllowed",
    }
    for field in required_true:
        if rules.get(field) is not True:
            raise ValidationFailure(f"global rule must be true: {field}")
    for field in required_false:
        if rules.get(field) is not False:
            raise ValidationFailure(f"global rule must be false: {field}")

    return tables, profiles


def decide(
    case: dict[str, Any],
    tables: dict[str, dict[str, Any]],
    profiles: dict[str, dict[str, Any]],
) -> tuple[str, str]:
    table = tables.get(case["table"])
    if table is None:
        return "deny", "SEC_RLS_ROLE_NOT_ALLOWED"
    profile = profiles[table["policyProfileId"]]
    command = case["command"]
    role_field = f"{command}Roles"

    if not case["sessionContextPresent"]:
        return "deny", "SEC_RLS_SESSION_CONTEXT_MISSING"
    if case["runtimeRole"] not in profile[role_field]:
        return "deny", "SEC_RLS_ROLE_NOT_ALLOWED"
    if case["sessionAccountId"] != case["rowOwnerAccountId"]:
        return "deny", "SEC_RLS_OWNER_MISMATCH"
    if case["sessionEpoch"] != case["rowEpoch"]:
        return "deny", "SEC_RLS_EPOCH_MISMATCH"

    if command == "update":
        proposed_owner = case.get("proposedOwnerAccountId", case["rowOwnerAccountId"])
        proposed_epoch = case.get("proposedEpoch", case["rowEpoch"])
        if proposed_owner != case["rowOwnerAccountId"]:
            return "deny", "SEC_RLS_OWNER_MUTATION_FORBIDDEN"
        if proposed_epoch < case["rowEpoch"]:
            return "deny", "SEC_RLS_EPOCH_DOWNGRADE_FORBIDDEN"

    if command in {"insert", "update"}:
        proposed_owner = case.get("proposedOwnerAccountId")
        proposed_epoch = case.get("proposedEpoch")
        if (
            proposed_owner != case["sessionAccountId"]
            or proposed_epoch != case["sessionEpoch"]
        ):
            return "deny", "SEC_RLS_WITH_CHECK_FAILED"

    return "allow", "SEC_AUTHORIZED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args()
    root = args.repo_root.resolve()

    try:
        contract = load_json(root / CONTRACT_PATH)
        case_set = load_json(root / CASE_SET_PATH)
        if case_set["contractRef"] != CONTRACT_PATH.as_posix():
            raise ValidationFailure("RLS case set points to a different contract")
        tables, profiles = validate_contract(contract)

        allow_count = 0
        deny_count = 0
        seen_case_ids: set[str] = set()
        for case in case_set["cases"]:
            case_id = case["caseId"]
            if case_id in seen_case_ids:
                raise ValidationFailure(f"duplicate RLS case ID: {case_id}")
            seen_case_ids.add(case_id)
            actual = decide(case, tables, profiles)
            expected = (case["expectedDecision"], case["expectedIssueCode"])
            if actual != expected:
                raise ValidationFailure(
                    f"RLS case mismatch {case_id}: expected={expected} actual={actual}"
                )
            if actual[0] == "allow":
                allow_count += 1
            else:
                deny_count += 1
    except ValidationFailure as exc:
        print(f"POSTGRESQL RLS CONTRACT VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(
            f"POSTGRESQL RLS CONTRACT VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}",
            file=sys.stderr,
        )
        return 2

    print("Memory OS PostgreSQL RLS contract validation PASS")
    print(f"tables: {len(tables)}")
    print(f"policy profiles: {len(profiles)}")
    print(f"cases: {allow_count + deny_count}")
    print(f"allow: {allow_count}")
    print(f"deny: {deny_count}")
    print("deny by default: enabled")
    print("runtime privilege roles: NOLOGIN NOINHERIT NOBYPASSRLS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
