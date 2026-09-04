#!/usr/bin/env python3
"""Reconcile append-only human backup/restore promotion review authority."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from memory_os_backup_restore_blockers import require_canonical_gaps

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/backup-restore-promotion-review-contract.v1.json")
REGISTRY_REL = Path("contracts/operations/backup-restore-promotion-review-registry.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/backup-restore-generation-evidence-registry.v1.json")
WRITER_REL = Path("scripts/register-memory-os-backup-restore-promotion-review.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-backup-restore-promotion-review.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
STATUS_REL = Path("contracts/operations/production-operability-status.json")
CONTRACT = ROOT / CONTRACT_REL
REGISTRY = ROOT / REGISTRY_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
WRITER = ROOT / WRITER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL
STATUS = ROOT / STATUS_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def repo_relative(path: Path) -> Path:
    try:
        return path.resolve(strict=False).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"authority path escapes repository: {path}") from exc


def require_exact_repo_file(path: Path, expected_relative: Path, field: str) -> Path:
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail(f"{field} missing or escapes repository") from exc
    require(
        lexical == expected_relative and resolved == expected_relative and path.is_file(),
        f"{field} authority drift",
    )
    return path


def enforce_runtime_authorities() -> None:
    require_exact_repo_file(CONTRACT, CONTRACT_REL, "promotion review contract")
    require_exact_repo_file(REGISTRY, REGISTRY_REL, "promotion review registry")
    require_exact_repo_file(GEN_REGISTRY, GEN_REGISTRY_REL, "generation evidence registry")
    require_exact_repo_file(WRITER, WRITER_REL, "promotion review writer")
    require_exact_repo_file(VALIDATOR, VALIDATOR_REL, "promotion review validator")
    require_exact_repo_file(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    require_exact_repo_file(STATUS, STATUS_REL, "production operability status")


def read_text(path: Path) -> str:
    relative = repo_relative(path)
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {relative}: {exc}") from exc


def write_text(path: Path, text: str) -> None:
    relative = repo_relative(path)
    require(path.parent.is_dir(), f"authority parent missing: {relative.parent}")
    temp_name: str | None = None
    try:
        mode = path.stat().st_mode & 0o777 if path.exists() else None
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        if mode is not None:
            os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except OSError as exc:
        raise Fail(f"cannot atomically write {relative}: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                pass


def load(path: Path) -> dict[str, Any]:
    relative = repo_relative(path)
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise Fail(f"cannot load {relative}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {relative}")
    return value


def load_writer():
    require_exact_repo_file(WRITER, WRITER_REL, "promotion review writer")
    spec = importlib.util.spec_from_file_location("memory_os_promotion_review_writer_reconcile", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load canonical promotion review writer")
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (FileNotFoundError, OSError) as exc:
        raise Fail(f"cannot load {WRITER_REL}: {exc}") from exc
    return module


def validate_generation_registry(writer: Any, registry: dict[str, Any]) -> tuple[Any, list[dict[str, Any]]]:
    generation_writer = writer.load_generation_writer()
    try:
        rows = generation_writer.validate_registry_for_append(registry)
    except Exception as exc:
        if writer.domain_validation_failure(exc):
            raise Fail(f"generation recovery evidence registry authority invalid: {exc}") from exc
        raise
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation recovery evidence registry rows invalid")
    return generation_writer, rows


def run_validator(path: Path, label: str) -> None:
    relative = repo_relative(path)
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        completed.returncode == 0,
        f"post-reconcile {label} failed ({relative}):\n{completed.stdout[-9000:]}{completed.stderr[-9000:]}",
    )


def main() -> int:
    enforce_runtime_authorities()
    original_contract_text = read_text(CONTRACT)
    original_registry_text = read_text(REGISTRY)
    contract = load(CONTRACT)
    registry = load(REGISTRY)
    generation = load(GEN_REGISTRY)
    status = load(STATUS)
    writer = load_writer()

    generation_writer, generation_rows = validate_generation_registry(writer, generation)
    candidate_count = sum(1 for row in generation_rows if generation_writer.candidate(row))
    require(generation.get("productionEquivalentRecoveryCandidateCount") == candidate_count, "recovery candidate aggregate drift")

    rows, expected_current = writer.reconcile_current_decision(registry)
    count = registry.get("registeredReviewCount")
    go_count = registry.get("goRecommendationCount")
    no_go_count = registry.get("noGoCount")
    defer_count = registry.get("deferCount")
    latest_id = registry.get("latestDecisionId")
    current_id = registry.get("currentDecisionId")
    require(expected_current == current_id, "promotion review current authority reconcile drift")
    if candidate_count == 0:
        require(current_id is None, "zero final recovery candidates must revoke current promotion authority")
    if current_id is not None:
        require(current_id == latest_id, "only latest historical review may remain current")

    require(status.get("productionDecision") == "NO_GO", "global production decision must remain NO_GO")
    ops7 = next((row for row in status.get("areas", []) if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(ops7, dict), "OPS-P0-007 status missing")
    require(ops7.get("status") == "PARTIAL_FOUNDATIONS_ONLY" and ops7.get("blocking") is True, "OPS-P0-007 must remain blocking foundation-only")
    require_canonical_gaps(ops7.get("missingEvidence"), Fail)

    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "promotion review currentBoundary missing")
    boundary["registeredReviewCount"] = count
    boundary["goRecommendationCount"] = go_count
    boundary["noGoCount"] = no_go_count
    boundary["deferCount"] = defer_count
    boundary["latestDecisionId"] = latest_id
    boundary["currentDecisionId"] = current_id
    boundary["productionTrafficChanged"] = False
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"

    registry_text = json.dumps(registry, indent=2, ensure_ascii=False) + "\n"
    contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    try:
        write_text(REGISTRY, registry_text)
        write_text(CONTRACT, contract_text)
        run_validator(VALIDATOR, "promotion review validator")
        run_validator(OPERABILITY_VALIDATOR, "aggregate operability validator")
    except Exception:
        write_text(REGISTRY, original_registry_text)
        write_text(CONTRACT, original_contract_text)
        raise

    print("Memory OS backup/restore promotion review reconciliation PASS")
    print(f"final recovery candidates: {candidate_count}")
    print(f"registered historical promotion reviews: {count}")
    print(f"GO/NO_GO/DEFER: {go_count}/{no_go_count}/{defer_count}")
    print(f"latest historical decision: {latest_id}")
    print(f"current promotion authority decision: {current_id}")
    print("generation candidate authority re-derived before promotion reconcile: true")
    print("historical review rows retained: true")
    print("current authority may only be revoked automatically: true")
    print("promotion registry/contract writes use atomic same-directory replace: true")
    print("failed post-validation leaves promotion registry/contract mutation behind: false")
    print("aggregate operability validated inside transaction: true")
    print("canonical OPS-P0-007 blockers preserved: 6")
    print("automatic human promotion authorization created: false")
    print("production traffic changed: false")
    print("production ready: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE PROMOTION REVIEW RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
