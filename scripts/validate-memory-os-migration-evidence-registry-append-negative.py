#!/usr/bin/env python3
"""Fail-closed corruption negatives for the append-only migration rehearsal ledger."""

from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/migration-evidence-registry-contract.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
GEN_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-migration-rehearsal-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"
LOCAL_ARTIFACT_VALIDATOR = ROOT / "scripts/validate-memory-os-local-migration-recovery-artifact.py"
LOCAL_ARTIFACT_RECONCILER = ROOT / "scripts/reconcile-memory-os-local-migration-recovery-artifact.py"
LOCAL_ARTIFACT_CONTRACT = ROOT / "contracts/operations/local-migration-recovery-artifact-contract.v1.json"
RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-evidence-registry.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_migration_rehearsal_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load migration rehearsal writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(callable(getattr(module, "require_actual_cli_authorities", None)), "migration rehearsal CLI authority guard missing")
    return module


def expect_cli_authority_substitution_rejected(writer: ModuleType) -> None:
    main_source = inspect.getsource(writer.main)
    guard_index = main_source.find("require_actual_cli_authorities()")
    parser_index = main_source.find("argparse.ArgumentParser()")
    require(guard_index >= 0 and parser_index >= 0 and guard_index < parser_index,
            "migration rehearsal CLI authority guard must run before argument parsing")
    originals = {path: path.read_bytes() for path in (CONTRACT, REGISTRY, LIFECYCLE, STATUS)}
    substitutions = (
        ("CONTRACT", STATUS),
        ("REGISTRY", STATUS),
        ("LIFECYCLE", STATUS),
        ("GEN_REGISTRY", STATUS),
        ("GEN_WRITER", STATUS),
        ("LOCK", ROOT / "contracts/operations/.migration-evidence-registry-negative.lock"),
    )
    for name, substitute in substitutions:
        original = getattr(writer, name)
        setattr(writer, name, substitute)
        try:
            try:
                writer.require_actual_cli_authorities()
            except Exception as exc:
                require("substitution rejected" in str(exc), f"migration rehearsal CLI {name} substitution rejected for unrelated reason: {exc}")
            else:
                raise Fail(f"migration rehearsal CLI accepted {name} authority substitution")
        finally:
            setattr(writer, name, original)
    for path, original in originals.items():
        require(path.read_bytes() == original, f"migration rehearsal CLI authority substitution mutated {path.relative_to(ROOT)}")


def expect_writer_rejected(writer: ModuleType, contract: dict[str, Any], name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    corrupt = copy.deepcopy(load_json(REGISTRY))
    mutate(corrupt)
    try:
        writer.validate_registry_for_append(corrupt, contract)
    except Exception:
        return
    raise Fail(f"writer accepted corrupt migration ledger: {name}")


def expect_contract_authority_rejected(writer: ModuleType, name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    corrupt = copy.deepcopy(load_json(CONTRACT))
    mutate(corrupt)
    try:
        writer.validate_registry_for_append(load_json(REGISTRY), corrupt)
    except Exception:
        return
    raise Fail(f"writer accepted corrupt migration contract authority: {name}")


def expect_transactional_append_rollback(writer: ModuleType, contract: dict[str, Any]) -> None:
    original = REGISTRY.read_bytes()
    previous = load_json(REGISTRY)
    corrupt = copy.deepcopy(previous)
    corrupt["unexpected"] = True
    try:
        try:
            writer.write_registry_transactionally(corrupt, previous, contract)
        except Exception:
            require(REGISTRY.read_bytes() == original, "migration registry bytes changed after rejected post-append validation")
            return
        raise Fail("transactional migration append accepted a registry that fails canonical validation")
    finally:
        REGISTRY.write_bytes(original)


def expect_reconcile_rejected_without_mutation(name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    originals = {path: path.read_bytes() for path in (REGISTRY, CONTRACT, LIFECYCLE, STATUS)}
    corrupt = load_json(REGISTRY)
    mutate(corrupt)
    REGISTRY.write_text(json.dumps(corrupt, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, f"reconciler auto-healed corrupt migration ledger: {name}")
        for path in (CONTRACT, LIFECYCLE, STATUS):
            require(path.read_bytes() == originals[path], f"reconciler mutated {path.relative_to(ROOT)} after rejecting {name}")
    finally:
        for path, data in originals.items():
            path.write_bytes(data)


def expect_local_artifact_reconcile_rejected_on_corrupt_registry() -> None:
    registry = load_json(REGISTRY)
    records = registry.get("records")
    require(isinstance(records, list) and records and isinstance(records[-1], dict), "migration ledger needs one canonical record for local reconcile negative")
    run_id = records[-1].get("migrationRunId")
    require(isinstance(run_id, str) and run_id, "latest migration run id missing")
    original_registry = REGISTRY.read_bytes()
    original_contract = LOCAL_ARTIFACT_CONTRACT.read_bytes()
    corrupt = copy.deepcopy(registry)
    corrupt["rehearsalEvidenceCount"] = True
    REGISTRY.write_text(json.dumps(corrupt, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(LOCAL_ARTIFACT_RECONCILER), "--run-id", run_id],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, "local artifact reconciler accepted corrupt migration registry")
        require(LOCAL_ARTIFACT_CONTRACT.read_bytes() == original_contract,
                "local artifact reconciler mutated contract after rejecting corrupt migration registry")
    finally:
        REGISTRY.write_bytes(original_registry)
        LOCAL_ARTIFACT_CONTRACT.write_bytes(original_contract)


def expect_status_rejected_without_partial_writes() -> None:
    originals = {path: path.read_bytes() for path in (CONTRACT, LIFECYCLE, STATUS)}
    corrupt = load_json(STATUS)
    corrupt["productionDecision"] = "GO"
    STATUS.write_text(json.dumps(corrupt, indent=2) + "\n", encoding="utf-8")
    corrupted_status = STATUS.read_bytes()
    try:
        completed = subprocess.run(
            [sys.executable, str(RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, "reconciler accepted productionDecision=GO")
        require(CONTRACT.read_bytes() == originals[CONTRACT], "reconciler partially mutated migration contract before rejecting status")
        require(LIFECYCLE.read_bytes() == originals[LIFECYCLE], "reconciler partially mutated migration lifecycle before rejecting status")
        require(STATUS.read_bytes() == corrupted_status, "reconciler mutated corrupt status while rejecting it")
    finally:
        for path, data in originals.items():
            path.write_bytes(data)


def expect_append_lock_contract_rejected(writer: ModuleType) -> None:
    corrupt_contract = load_json(CONTRACT)
    corrupt_contract["appendLockPath"] = "contracts/operations/.migration-evidence-registry-alternate.lock"
    try:
        writer.validate_registry_for_append(load_json(REGISTRY), corrupt_contract)
    except Exception as exc:
        require("append lock" in str(exc).lower(), f"writer rejected alternate append lock for wrong reason: {exc}")
    else:
        raise Fail("writer accepted alternate migration append lock authority")

    original = CONTRACT.read_bytes()
    CONTRACT.write_text(json.dumps(corrupt_contract, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, "validator accepted alternate migration append lock authority")
        require("append lock" in completed.stdout.lower(), f"alternate append lock was rejected for wrong reason: {completed.stdout[-1200:]}")
    finally:
        CONTRACT.write_bytes(original)


def make_side_commit() -> str:
    tree = subprocess.run(
        ["git", "rev-parse", "HEAD^{tree}"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(tree.returncode == 0 and tree.stdout.strip(), "cannot resolve HEAD tree for lineage negative")
    completed = subprocess.run(
        [
            "git",
            "-c", "user.name=memory-os-negative",
            "-c", "user.email=memory-os-negative@example.invalid",
            "commit-tree", tree.stdout.strip(), "-p", "HEAD",
        ],
        cwd=ROOT,
        input="migration evidence lineage negative\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(completed.returncode == 0 and completed.stdout.strip(), "cannot create detached lineage negative commit")
    return completed.stdout.strip()


def expect_record_lineage_rejected(writer: ModuleType, contract: dict[str, Any]) -> None:
    registry = load_json(REGISTRY)
    records = registry.get("records")
    require(isinstance(records, list) and records and isinstance(records[0], dict), "migration ledger needs one canonical record for lineage negative")
    record = copy.deepcopy(records[0])
    record["sourceCommitSha"] = make_side_commit()
    required = contract.get("requiredRecordFields")
    require(isinstance(required, list), "requiredRecordFields missing")
    try:
        writer.validate_record(record, set(required), contract)
    except Exception as exc:
        require("ancestor" in str(exc), f"non-ancestor source was rejected for the wrong reason: {exc}")
        return
    raise Fail("writer accepted non-ancestor migration sourceCommitSha")


def expect_local_artifact_lineage_rejected() -> None:
    registry = load_json(REGISTRY)
    records = registry.get("records")
    require(isinstance(records, list) and records and isinstance(records[0], dict), "migration ledger needs one canonical record for local artifact lineage negative")
    evidence_ref = records[0].get("recoveryPointRestoreEvidenceRef")
    require(isinstance(evidence_ref, str) and evidence_ref, "canonical record missing recoveryPointRestoreEvidenceRef")
    result = load_json(ROOT / evidence_ref)
    result["commitSha"] = make_side_commit()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8", delete=False) as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
        temp_path = Path(handle.name)
    try:
        completed = subprocess.run(
            [sys.executable, str(LOCAL_ARTIFACT_VALIDATOR), "--path", str(temp_path), "--require-result"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, "local recovery artifact validator accepted non-ancestor commitSha")
        require("ancestor" in completed.stdout.lower(), f"local artifact lineage was rejected for wrong reason: {completed.stdout[-1200:]}")
    finally:
        temp_path.unlink(missing_ok=True)


def expect_recovery_evidence_mutation_rejected(writer: ModuleType, contract: dict[str, Any]) -> None:
    registry = load_json(REGISTRY)
    records = registry.get("records")
    require(isinstance(records, list) and records and isinstance(records[0], dict), "migration ledger needs one canonical record for evidence mutation negative")
    record = copy.deepcopy(records[0])
    evidence_ref = record.get("recoveryPointRestoreEvidenceRef")
    require(isinstance(evidence_ref, str) and evidence_ref, "canonical record missing recoveryPointRestoreEvidenceRef")
    evidence_path = ROOT / evidence_ref
    original = evidence_path.read_bytes()
    required = contract.get("requiredRecordFields")
    require(isinstance(required, list), "requiredRecordFields missing")
    try:
        evidence_path.write_bytes(original + b"\n")
        try:
            writer.validate_record(record, set(required), contract)
        except Exception:
            return
        raise Fail("writer accepted post-commit mutation of per-run recovery evidence")
    finally:
        evidence_path.write_bytes(original)


def expect_restore_capability_symlink_rejected(writer: ModuleType, contract: dict[str, Any]) -> None:
    registry = load_json(REGISTRY)
    records = registry.get("records")
    record = next(
        (copy.deepcopy(item) for item in records if isinstance(item, dict) and item.get("environmentClass") == "LOCAL_POSTGRES_REHEARSAL"),
        None,
    )
    require(isinstance(record, dict), "migration ledger needs one local record for restore capability symlink negative")
    authorities = contract.get("restoreCapabilityAuthorities")
    require(isinstance(authorities, dict), "restore capability authorities missing")
    authority = authorities.get("LOCAL_POSTGRES_REHEARSAL")
    require(isinstance(authority, dict), "local restore capability authority missing")
    evidence_ref = authority.get("evidenceRef")
    require(isinstance(evidence_ref, str) and evidence_ref, "local restore capability evidenceRef missing")
    evidence_path = ROOT / evidence_ref
    original = evidence_path.read_bytes()
    required = contract.get("requiredRecordFields")
    require(isinstance(required, list), "requiredRecordFields missing")
    with tempfile.TemporaryDirectory(prefix="memory-os-migration-restore-capability-negative-") as tmp:
        external = Path(tmp) / evidence_path.name
        external.write_bytes(original)
        evidence_path.unlink()
        evidence_path.symlink_to(external)
        try:
            try:
                writer.validate_record(record, set(required), contract)
            except Exception as exc:
                require("symlink" in str(exc).lower() or "repository" in str(exc).lower(),
                        f"restore capability symlink was rejected for unrelated reason: {exc}")
                return
            raise Fail("writer accepted symlinked restore capability evidence")
        finally:
            evidence_path.unlink(missing_ok=True)
            evidence_path.write_bytes(original)


def main() -> int:
    writer = load_writer()
    expect_cli_authority_substitution_rejected(writer)
    contract = load_json(CONTRACT)
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        ("registry class drift", lambda value: value.__setitem__("registryClass", "PRODUCTION_MIGRATION_EVIDENCE")),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("boolean rehearsal count", lambda value: value.__setitem__("rehearsalEvidenceCount", True)),
        ("rehearsal count drift", lambda value: value.__setitem__("rehearsalEvidenceCount", len(value.get("records", [])) + 1)),
        ("passing count drift", lambda value: value.__setitem__("passingRehearsalCount", 0)),
        ("production-equivalent count drift", lambda value: value.__setitem__("productionEquivalentRehearsalCount", 1)),
        ("latest pointer drift", lambda value: value.__setitem__("latestRehearsalRunId", "mig_20991231_invalid")),
        ("unknown registry field", lambda value: value.__setitem__("unexpected", True)),
    ]
    for name, mutate in cases:
        expect_writer_rejected(writer, contract, name, mutate)
        expect_reconcile_rejected_without_mutation(name, mutate)

    contract_cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("contract schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        ("lifecycle authority drift", lambda value: value.__setitem__("migrationLifecycleContract", "README.md")),
        ("registry authority drift", lambda value: value.__setitem__("registryPath", "contracts/operations/production-operability-status.json")),
        ("writer authority drift", lambda value: value.__setitem__("writer", "scripts/validate-memory-os-migration-evidence-registry.py")),
        ("contract append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
        ("production registration enabled", lambda value: value.__setitem__("productionEnvironmentRegistrationImplemented", True)),
        ("environment class authority drift", lambda value: value.__setitem__("allowedEnvironmentClasses", ["LOCAL_POSTGRES_REHEARSAL"])),
        (
            "append rollback authority disabled",
            lambda value: value["registrationRules"].__setitem__("appendMustRevalidateCanonicalRegistryAndRollbackOnFailure", False),
        ),
    ]
    for name, mutate in contract_cases:
        expect_contract_authority_rejected(writer, name, mutate)

    expect_transactional_append_rollback(writer, contract)
    expect_status_rejected_without_partial_writes()
    expect_append_lock_contract_rejected(writer)
    expect_record_lineage_rejected(writer, contract)
    expect_local_artifact_lineage_rejected()
    expect_local_artifact_reconcile_rejected_on_corrupt_registry()
    expect_recovery_evidence_mutation_rejected(writer, contract)
    expect_restore_capability_symlink_rejected(writer, contract)
    print("PASS: migration rehearsal CLI authority, ledger/contract corruption, transactional append rollback, reconcile partial writes, local reconcile corruption rejection, append-lock drift, registry/local-artifact source-lineage drift, recovery-evidence mutation and restore-capability symlink escape are rejected")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION EVIDENCE APPEND NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)