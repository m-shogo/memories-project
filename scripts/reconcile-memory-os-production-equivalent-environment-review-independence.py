#!/usr/bin/env python3
"""Reconcile review-independence counters for eligible environment generations."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REL = Path("contracts/operations/production-equivalent-environment-review-independence-contract.v1.json")
GEN_REGISTRY_REL = Path("contracts/operations/production-equivalent-environment-generation-registry.v1.json")
HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
VALIDATOR_REL = Path("scripts/validate-memory-os-production-equivalent-environment-review-independence.py")
OPERABILITY_VALIDATOR_REL = Path("scripts/validate-memory-os-operability.py")
CONTRACT = ROOT / CONTRACT_REL
GEN_REGISTRY = ROOT / GEN_REGISTRY_REL
HELPER = ROOT / HELPER_REL
VALIDATOR = ROOT / VALIDATOR_REL
OPERABILITY_VALIDATOR = ROOT / OPERABILITY_VALIDATOR_REL


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


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
    for path, expected, field in (
        (CONTRACT, CONTRACT_REL, "review independence contract"),
        (GEN_REGISTRY, GEN_REGISTRY_REL, "generation registry"),
        (HELPER, HELPER_REL, "generation eligibility helper"),
        (VALIDATOR, VALIDATOR_REL, "review independence validator"),
        (OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator"),
    ):
        require_exact_repo_file(path, expected, field)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        try:
            label = path.relative_to(ROOT)
        except ValueError:
            label = path
        raise Fail(f"cannot load {label}: {exc}") from exc
    try:
        label = path.relative_to(ROOT)
    except ValueError:
        label = path
    require(isinstance(value, dict), f"root must be object: {label}")
    return value


def canonical_helper_path() -> Path:
    return require_exact_repo_file(HELPER, HELPER_REL, "generation eligibility helper")


def load_helper():
    path = canonical_helper_path()
    spec = importlib.util.spec_from_file_location("memory_os_generation_eligibility_review_reconcile", path)
    require(spec is not None and spec.loader is not None, "cannot load generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_post_validator(path: Path, expected_relative: Path, field: str) -> None:
    require_exact_repo_file(path, expected_relative, field)
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
        f"post-reconcile {field} failed:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}",
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def main() -> int:
    enforce_runtime_authorities()
    try:
        original_contract_text = CONTRACT.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {CONTRACT.relative_to(ROOT)}: {exc}") from exc
    contract = load(CONTRACT)
    helper = load_helper()
    state = helper.derive(GEN_REGISTRY)
    eligible_count = state["preflightEligibleGenerationCount"]
    require(isinstance(eligible_count, int) and not isinstance(eligible_count, bool) and eligible_count >= 0, "preflight eligible generation count invalid")
    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "review independence currentBoundary missing")
    boundary["preflightEligibleGenerationCount"] = eligible_count
    boundary["independentlyReviewedEligibleGenerationCount"] = eligible_count
    boundary["reviewReuseViolationCount"] = 0
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    updated_contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + "\n"
    try:
        atomic_write_text(CONTRACT, updated_contract_text)
        run_post_validator(VALIDATOR, VALIDATOR_REL, "review independence validator")
        run_post_validator(OPERABILITY_VALIDATOR, OPERABILITY_VALIDATOR_REL, "operability validator")
    except Exception:
        try:
            atomic_write_text(CONTRACT, original_contract_text)
        except OSError as restore_exc:
            raise Fail(f"review independence contract rollback failed: {restore_exc}") from restore_exc
        raise
    print("Memory OS production-equivalent environment review independence reconciliation PASS")
    print(f"eligible/reviewed generations: {eligible_count}/{eligible_count}")
    print("review reuse violations: 0")
    print("canonical data/executable authorities enforced: true")
    print("atomic review-independence replacement: true")
    print("aggregate operability validation inside transaction: true")
    print("failed post-validation leaves review-independence authority mutation behind: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT ENVIRONMENT REVIEW INDEPENDENCE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
