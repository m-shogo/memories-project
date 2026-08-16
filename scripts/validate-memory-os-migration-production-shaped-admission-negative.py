#!/usr/bin/env python3
"""Focused fail-closed negatives for production-shaped migration admission."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from memory_os_migration_production_admission_ledger import (
    LedgerBindingFailure,
    require_registered_production_equivalent_rehearsal,
    validate_canonical_ledger,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/migration-production-shaped-admission-registry.v1.json"
MIGRATION_LEDGER = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
RELEASES = ROOT / "contracts/operations/release-baseline-registry.v1.json"
GENERATIONS = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
CONTRACT = ROOT / "contracts/operations/migration-production-shaped-admission-contract.v1.json"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
WRITER = ROOT / "scripts/register-memory-os-migration-production-shaped-admission.py"
RECONCILER = ROOT / "scripts/reconcile-memory-os-migration-production-shaped-admission.py"
REVIEW_NEGATIVE_REF = "docs/evidence/migration-production-shaped-admission/independent-reviews/.negative-review-history.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_migration_production_admission_writer_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load migration admission writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def expect_rejected(writer: ModuleType, name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    registry = load_json(REGISTRY)
    corrupt = copy.deepcopy(registry)
    mutate(corrupt)
    try:
        writer.validate_registry_for_append(corrupt)
    except Exception:
        return
    raise Fail(f"writer accepted corrupt registry: {name}")


def expect_reconcile_rejected_without_mutation(name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    original = {path: path.read_bytes() for path in (REGISTRY, CONTRACT, LIFECYCLE, STATUS)}
    registry = load_json(REGISTRY)
    mutate(registry)
    REGISTRY.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, f"reconciler auto-healed corrupt registry: {name}")
        for path in (CONTRACT, LIFECYCLE, STATUS):
            require(path.read_bytes() == original[path], f"reconciler mutated {path.relative_to(ROOT)} after rejecting {name}")
    finally:
        for path, data in original.items():
            path.write_bytes(data)


def expect_upstream_reconcile_rejected_without_mutation(path: Path, name: str) -> None:
    original = {item: item.read_bytes() for item in (path, CONTRACT, LIFECYCLE, STATUS)}
    corrupt = load_json(path)
    corrupt["unexpectedAuthority"] = True
    path.write_text(json.dumps(corrupt, indent=2) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, str(RECONCILER)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        require(completed.returncode != 0, f"reconciler accepted corrupt upstream authority: {name}")
        for derived in (CONTRACT, LIFECYCLE, STATUS):
            require(derived.read_bytes() == original[derived], f"reconciler mutated {derived.relative_to(ROOT)} after rejecting {name}")
    finally:
        for item, data in original.items():
            item.write_bytes(data)


def expect_noncanonical_ledger_rows_rejected() -> None:
    ledger = load_json(MIGRATION_LEDGER)
    rows = ledger.get("records")
    require(isinstance(rows, list) and rows, "migration ledger fixture missing")
    local = next((row for row in rows if isinstance(row, dict) and row.get("environmentClass") == "LOCAL_POSTGRES_REHEARSAL"), None)
    require(isinstance(local, dict), "local migration ledger fixture missing")
    try:
        require_registered_production_equivalent_rehearsal(
            migration_run_id=local["migrationRunId"],
            source_commit_sha=local["sourceCommitSha"],
            environment_generation_id="pegen_nonexistent_negative",
        )
    except LedgerBindingFailure:
        pass
    else:
        raise Fail("local canonical migration rehearsal was accepted as production-equivalent admission authority")
    try:
        require_registered_production_equivalent_rehearsal(
            migration_run_id="mig_20991231_noncanonical_negative",
            source_commit_sha="0" * 40,
            environment_generation_id="pegen_nonexistent_negative",
        )
    except LedgerBindingFailure:
        return
    raise Fail("unregistered migrationRunId was accepted as canonical admission authority")


def expect_canonical_writer_delegation() -> None:
    original = MIGRATION_LEDGER.read_bytes()
    corrupt = load_json(MIGRATION_LEDGER)
    corrupt["unexpectedAuthority"] = True
    MIGRATION_LEDGER.write_text(json.dumps(corrupt, indent=2) + "\n", encoding="utf-8")
    try:
        try:
            validate_canonical_ledger()
        except LedgerBindingFailure:
            return
        raise Fail("production admission helper accepted migration ledger field drift outside canonical writer authority")
    finally:
        MIGRATION_LEDGER.write_bytes(original)


def expect_release_registry_delegation(writer: ModuleType) -> None:
    original = RELEASES.read_bytes()
    corrupt = load_json(RELEASES)
    corrupt["unexpectedAuthority"] = True
    RELEASES.write_text(json.dumps(corrupt, indent=2) + "\n", encoding="utf-8")
    try:
        try:
            writer.approved_release("rel_missing_negative")
        except Exception as exc:
            require("release baseline registry invalid" in str(exc), "direct writer did not fail through canonical release registry authority")
            return
        raise Fail("direct migration writer accepted corrupt release baseline registry")
    finally:
        RELEASES.write_bytes(original)


def expect_generic_review_refs_rejected(writer: ModuleType) -> None:
    record = {
        "admissionId": "mpa_review_negative",
        "migrationRunId": "mig_review_negative",
        "environmentGenerationId": "pegen_review_negative",
        "sourceCommitSha": "0" * 40,
        "predecessorReleaseId": "rel_review_predecessor",
        "successorReleaseId": "rel_review_successor",
        "securityReviewRef": "contracts/operations/production-operability-status.json",
        "operabilityReviewRef": "contracts/operations/migration-production-shaped-admission-contract.v1.json",
    }
    try:
        writer.validate_independent_reviews(record)
    except Exception:
        return
    raise Fail("generic repository JSON files were accepted as migration independent-review authority")


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def expect_mutated_review_history_rejected(writer: ModuleType) -> None:
    original_head = run_git("rev-parse", "HEAD").stdout.strip()
    require(len(original_head) == 40, "cannot resolve original HEAD for review history negative")
    path = ROOT / REVIEW_NEGATIVE_REF
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text('{"negative":"creation"}\n', encoding="utf-8")
        require(run_git("add", "-f", "--", REVIEW_NEGATIVE_REF).returncode == 0, "cannot stage review history creation fixture")
        require(
            run_git("-c", "user.name=memory-os-negative", "-c", "user.email=negative@example.invalid", "commit", "-m", "test: create review history fixture").returncode == 0,
            "cannot commit review history creation fixture",
        )
        path.write_text('{"negative":"mutated"}\n', encoding="utf-8")
        require(run_git("add", "-f", "--", REVIEW_NEGATIVE_REF).returncode == 0, "cannot stage mutated review history fixture")
        require(
            run_git("-c", "user.name=memory-os-negative", "-c", "user.email=negative@example.invalid", "commit", "-m", "test: mutate review history fixture").returncode == 0,
            "cannot commit mutated review history fixture",
        )
        try:
            writer.canonical_review_path(REVIEW_NEGATIVE_REF, "securityReviewRef")
        except Exception as exc:
            require("creation commit" in str(exc), "mutated review history was rejected for an unrelated reason")
            return
        raise Fail("review evidence changed after its creation commit was accepted")
    finally:
        run_git("reset", "--hard", original_head)
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def main() -> int:
    writer = load_writer()
    cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("schema drift", lambda value: value.__setitem__("schemaVersion", "invalid")),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("boolean count", lambda value: value.__setitem__("admittedRehearsalCount", True)),
        ("count drift", lambda value: value.__setitem__("admittedRehearsalCount", 1)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("production readiness promotion", lambda value: value.__setitem__("productionReady", True)),
        ("unknown registry field", lambda value: value.__setitem__("unexpected", True)),
    ]
    for name, mutate in cases:
        expect_rejected(writer, name, mutate)
        expect_reconcile_rejected_without_mutation(name, mutate)
    expect_upstream_reconcile_rejected_without_mutation(RELEASES, "release baseline registry drift")
    expect_upstream_reconcile_rejected_without_mutation(GENERATIONS, "environment generation registry drift")
    expect_noncanonical_ledger_rows_rejected()
    expect_canonical_writer_delegation()
    expect_release_registry_delegation(writer)
    expect_generic_review_refs_rejected(writer)
    expect_mutated_review_history_rejected(writer)
    print("PASS: migration production-shaped admission registry, upstream, ledger, release, and independent-review authority drift are rejected")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"MIGRATION PRODUCTION-SHAPED NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
