#!/usr/bin/env python3
"""Reconcile append-only human backup/restore promotion review authority."""

from __future__ import annotations

import importlib.util
import json
import math
import os
import subprocess
import sys
import stat
import tempfile
from contextlib import redirect_stderr, redirect_stdout
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
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        raise Fail(f"{field} missing or escapes repository") from None
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


MAX_AUTHORITY_BYTES = 1024 * 1024


def read_text(path: Path) -> str:
    require(isinstance(path, Path) and path.is_absolute(),
            "promotion reconcile authority path unsafe")
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        raise Fail("promotion reconcile authority path unsafe") from None
    require(lexical == resolved and path.is_file() and not path.is_symlink(),
            "promotion reconcile authority path unsafe")
    try:
        with path.open("rb") as source:
            raw = source.read(MAX_AUTHORITY_BYTES + 1)
    except OSError:
        raise Fail("promotion reconcile authority unreadable") from None
    require(len(raw) <= MAX_AUTHORITY_BYTES,
            "promotion reconcile authority size limit exceeded")
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        raise Fail("promotion reconcile authority invalid UTF-8") from None


def write_text(path: Path, text: str) -> None:
    """Replace only reviewed promotion authorities with bounded private-safe bytes."""
    require(isinstance(path, Path) and path.is_absolute(),
            "promotion reconcile write path unsafe")
    try:
        lexical = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (OSError, RuntimeError, ValueError):
        raise Fail("promotion reconcile write path unsafe") from None
    require(lexical == resolved and path.is_file() and not path.is_symlink(),
            "promotion reconcile write path unsafe")
    require(lexical in {CONTRACT_REL, REGISTRY_REL},
            "promotion reconcile write target unreviewed")
    require(isinstance(text, str), "promotion reconcile write payload invalid")
    try:
        payload = text.encode("utf-8")
    except UnicodeError:
        raise Fail("promotion reconcile write payload invalid") from None
    require(len(payload) <= MAX_AUTHORITY_BYTES,
            "promotion reconcile write size limit exceeded")
    temp_name: str | None = None
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent,
        )
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except (OSError, ValueError, TypeError):
        raise Fail("promotion reconcile authority atomic write failed") from None
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                raise Fail("promotion reconcile authority temporary cleanup failed") from None


def load(path: Path) -> dict[str, Any]:
    def unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, "promotion reconcile JSON duplicate key refused")
            result[key] = value
        return result

    def reject_constant(_value: str) -> None:
        raise Fail("promotion reconcile JSON nonfinite number refused")

    def finite_float(value: str) -> float:
        number = float(value)
        require(math.isfinite(number), "promotion reconcile JSON nonfinite number refused")
        return number

    def bounded_int(value: str) -> int:
        require(len(value.lstrip("-")) <= 128, "promotion reconcile JSON integer too large")
        return int(value)

    try:
        value = json.loads(read_text(path), object_pairs_hook=unique_keys,
                           parse_constant=reject_constant, parse_float=finite_float,
                           parse_int=bounded_int)
    except (json.JSONDecodeError, ValueError, OverflowError, RecursionError):
        raise Fail("promotion reconcile JSON unreadable or invalid") from None
    require(isinstance(value, dict), "promotion reconcile JSON root must be object")
    return value


def load_writer():
    """Load only the reviewed writer without forwarding import output or errors."""
    require_exact_repo_file(WRITER, WRITER_REL, "promotion review writer")
    try:
        spec = importlib.util.spec_from_file_location(
            "memory_os_promotion_review_writer_reconcile", WRITER,
        )
        require(spec is not None and spec.loader is not None,
                "promotion review canonical writer import failed")
        module = importlib.util.module_from_spec(spec)
        with open(os.devnull, "w", encoding="utf-8") as sink:
            with redirect_stdout(sink), redirect_stderr(sink):
                spec.loader.exec_module(module)
    except Exception:
        raise Fail("promotion review canonical writer import failed") from None
    return module


def validate_generation_registry(writer: Any, registry: dict[str, Any]) -> tuple[Any, list[dict[str, Any]]]:
    generation_writer = writer.load_generation_writer()
    try:
        rows = generation_writer.validate_registry_for_append(registry)
    except Exception as exc:
        if writer.domain_validation_failure(exc):
            raise Fail("generation recovery evidence registry authority invalid") from None
        raise
    require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "generation recovery evidence registry rows invalid")
    return generation_writer, rows


def run_validator(path: Path, label: str) -> None:
    if path == VALIDATOR and label == "promotion review validator":
        expected = VALIDATOR_REL
    elif path == OPERABILITY_VALIDATOR and label == "aggregate operability validator":
        expected = OPERABILITY_VALIDATOR_REL
    else:
        raise Fail("unreviewed promotion review post-reconcile validator")
    require_exact_repo_file(path, expected, "post-reconcile validator")
    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise Fail(f"post-reconcile {label} unavailable") from None
    require(type(completed.returncode) is int and completed.returncode == 0,
            f"post-reconcile {label} failed without exposing subprocess output")

def restore_authorities(authorities: tuple[tuple[Path, str], ...], reconcile_error: Exception) -> None:
    rollback_incomplete = False
    for path, original_text in authorities:
        try:
            write_text(path, original_text)
        except Exception:
            rollback_incomplete = True
    if rollback_incomplete:
        raise Fail(
            f"promotion review reconcile transaction failed ({type(reconcile_error).__name__}); rollback incomplete"
        ) from None


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
    except Exception as reconcile_error:
        restore_authorities(
            (
                (REGISTRY, original_registry_text),
                (CONTRACT, original_contract_text),
            ),
            reconcile_error,
        )
        raise Fail(
            f"promotion review reconcile transaction failed ({type(reconcile_error).__name__}); rollback completed"
        ) from None

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
    print("rollback attempts every promotion authority even after an earlier restore failure: true")
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
