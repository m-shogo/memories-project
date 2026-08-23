#!/usr/bin/env python3
"""Append one human-led completed tabletop record after canonical validation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = ROOT
CANONICAL_VALIDATOR = ROOT / "scripts/validate-memory-os-incident-tabletop.py"
CANONICAL_TABLETOP_CONTRACT = ROOT / "contracts/operations/incident-tabletop-record-contract.v1.json"
CANONICAL_INCIDENT_POLICY = ROOT / "contracts/operations/incident-response-contract.v1.json"
CANONICAL_PLAN = ROOT / "docs/fixtures/memory-os-operability/incident-tabletop-plan.v1.json"
CANONICAL_LEDGER = ROOT / "docs/evidence/incident-tabletops"
TABLETOP_CONTRACT = CANONICAL_TABLETOP_CONTRACT
INCIDENT_POLICY = CANONICAL_INCIDENT_POLICY
PLAN = CANONICAL_PLAN
LEDGER = CANONICAL_LEDGER
ACTOR = re.compile(r"^actor_[a-z0-9][a-z0-9_-]{5,63}$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")


class WriterFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WriterFailure(message)


def canonical_repo_file(path: Path, field: str) -> Path:
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise WriterFailure(f"{field} missing or escapes repository") from exc
    require(relative.parts and ".." not in relative.parts, f"{field} must be repository-contained")
    require(relative == resolved and path.is_file(), f"{field} must resolve to its canonical repository file")
    return path


def require_actual_cli_authorities() -> None:
    """Pin the actual append entrypoint while preserving helper-level fixture tests."""
    require(ROOT == CANONICAL_ROOT, "human tabletop writer root authority must remain canonical")
    authorities = (
        (CANONICAL_VALIDATOR, ROOT / "scripts/validate-memory-os-incident-tabletop.py", "human tabletop validator"),
        (TABLETOP_CONTRACT, CANONICAL_TABLETOP_CONTRACT, "human tabletop contract"),
        (INCIDENT_POLICY, CANONICAL_INCIDENT_POLICY, "incident response policy"),
        (PLAN, CANONICAL_PLAN, "human tabletop plan"),
    )
    for path, canonical, field in authorities:
        require(path == canonical, f"{field} must remain canonical for CLI registration")
        canonical_repo_file(path, field)
    require(LEDGER == CANONICAL_LEDGER, "human tabletop ledger authority must remain canonical for CLI registration")
    try:
        relative = LEDGER.relative_to(ROOT)
        resolved = LEDGER.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise WriterFailure("human tabletop ledger missing or escapes repository") from exc
    require(relative == resolved and LEDGER.is_dir(),
            "human tabletop ledger must resolve to its canonical repository directory")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_validator() -> ModuleType:
    require_actual_cli_authorities()
    spec = importlib.util.spec_from_file_location("memory_os_incident_tabletop", CANONICAL_VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load canonical tabletop validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def commit_exists(sha: str) -> bool:
    completed = subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return completed.returncode == 0


def source_is_ancestor(sha: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def validate_human_record(record: dict[str, Any]) -> str:
    source_sha = record.get("sourceCommitSha")
    require(isinstance(source_sha, str) and SHA40.fullmatch(source_sha) and commit_exists(source_sha), "sourceCommitSha must bind repository history")
    require(source_is_ancestor(source_sha), "sourceCommitSha must be an ancestor of current HEAD")
    require(record.get("status") == "COMPLETED", "only COMPLETED tabletop records may be registered")
    require(record.get("productionEvidence") is False, "tabletop completion cannot be production evidence")

    contract = load(TABLETOP_CONTRACT)
    policy = load(INCIDENT_POLICY)
    plan = load(PLAN)
    plans = {item.get("scenarioId"): item for item in plan.get("exercises", []) if isinstance(item, dict)}
    scenario_id = record.get("scenarioId")
    require(isinstance(scenario_id, str) and scenario_id in plans, "scenarioId is not in the canonical plan")
    planned = plans[scenario_id]
    for field in ("exerciseId", "scenarioId", "plannedSeverity", "objective", "scope", "plannedInjects", "assumptions", "safetyConstraints"):
        require(record.get(field) == planned.get(field), f"completed record changed planned field: {field}")

    canonical = load_validator()
    canonical.validate_completed(record, str(record.get("exerciseId")), contract)

    assignments = record.get("commandRoleAssignments")
    require(isinstance(assignments, list) and assignments, "commandRoleAssignments required")
    known_roles = {item.get("id") for item in policy.get("roles", []) if isinstance(item, dict)}
    role_to_actor: dict[str, str] = {}
    for item in assignments:
        require(isinstance(item, dict) and set(item) == {"role", "actorRef"}, "command role assignment field drift")
        role = item.get("role")
        actor = item.get("actorRef")
        require(role in known_roles and role not in role_to_actor, "command role invalid or duplicated")
        require(isinstance(actor, str) and ACTOR.fullmatch(actor), "command role actorRef invalid")
        role_to_actor[role] = actor
    required_roles = {"INCIDENT_COMMANDER", "OPERATIONS_LEAD", "SYSTEM_OWNER", "SCRIBE"}
    if record.get("plannedSeverity") == "SEV0":
        required_roles.add("SECURITY_PRIVACY_LEAD")
    require(required_roles <= set(role_to_actor), f"required command roles missing: {sorted(required_roles - set(role_to_actor))}")

    closure = record.get("closureApprovals")
    require(isinstance(closure, list) and closure, "closureApprovals required")
    severity = next(item for item in policy["severityLevels"] if item.get("id") == record.get("plannedSeverity"))
    required_closure = set(severity.get("closureApproval", []))
    approved: set[str] = set()
    used_actors: set[str] = set()
    for item in closure:
        require(isinstance(item, dict) and set(item) == {"role", "actorRef", "approvedAt"}, "closure approval field drift")
        role = item.get("role")
        actor = item.get("actorRef")
        require(role in required_closure and role not in approved, "closure role invalid or duplicated")
        require(role_to_actor.get(role) == actor and actor not in used_actors, "closure approver does not match assigned role")
        canonical.parse_time(item.get("approvedAt"), f"closureApprovals.{role}.approvedAt")
        approved.add(role)
        used_actors.add(actor)
    require(approved == required_closure, "severity-specific closure approvals incomplete")
    return scenario_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    require_actual_cli_authorities()
    record_path = Path(args.record).resolve()
    if not args.validate_only:
        try:
            record_path.relative_to(ROOT)
        except ValueError:
            pass
        else:
            raise WriterFailure("input record must be outside the repository")
    record = load(record_path)
    scenario_id = validate_human_record(record)
    if args.validate_only:
        print(f"Validated human tabletop completion: {scenario_id}")
        return 0

    target = LEDGER / f"{scenario_id}.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(target, flags, 0o644)
    except FileExistsError as exc:
        raise WriterFailure(f"scenario already has accepted completion: {scenario_id}") from exc
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        raise
    print(f"Registered human tabletop completion: {scenario_id}")
    print("This is human tabletop evidence only; production recovery evidence remains false.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WriterFailure as exc:
        print(f"HUMAN TABLETOP REGISTRATION FAILED: {exc}")
        raise SystemExit(1)
