#!/usr/bin/env python3
"""Reconcile review-independence counters for eligible environment generations."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/operations/production-equivalent-environment-review-independence-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
HELPER_REL = Path("scripts/memory_os_environment_generation_eligibility.py")
VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-review-independence.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def canonical_helper_path() -> Path:
    expected = ROOT / HELPER_REL
    require(HELPER == expected, "generation eligibility helper executable authority drift")
    try:
        resolved = HELPER.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise Fail("generation eligibility helper missing or escapes repository") from exc
    require(resolved == HELPER_REL and HELPER.is_file(), "generation eligibility helper must be canonical repository file")
    return HELPER


def load_helper():
    path = canonical_helper_path()
    spec = importlib.util.spec_from_file_location("memory_os_generation_eligibility_review_reconcile", path)
    require(spec is not None and spec.loader is not None, "cannot load generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    try:
        original_contract_text = CONTRACT.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Fail(f"cannot read {CONTRACT.relative_to(ROOT)}: {exc}") from exc
    contract = load(CONTRACT)
    helper = load_helper()
    state = helper.derive(GEN_REGISTRY)
    eligible_count = state["preflightEligibleGenerationCount"]
    boundary = contract.get("currentBoundary")
    require(isinstance(boundary, dict), "review independence currentBoundary missing")
    boundary["preflightEligibleGenerationCount"] = eligible_count
    boundary["independentlyReviewedEligibleGenerationCount"] = eligible_count
    boundary["reviewReuseViolationCount"] = 0
    boundary["productionEvidence"] = False
    boundary["productionReady"] = False
    boundary["productionDecision"] = "NO_GO"
    try:
        CONTRACT.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        completed = subprocess.run([sys.executable, str(VALIDATOR)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        require(completed.returncode == 0, f"post-reconcile review independence validator failed:\n{completed.stdout[-8000:]}{completed.stderr[-8000:]}")
    except Exception:
        try:
            CONTRACT.write_text(original_contract_text, encoding="utf-8")
        except OSError as restore_exc:
            raise Fail(f"review independence contract rollback failed: {restore_exc}") from restore_exc
        raise
    print("Memory OS production-equivalent environment review independence reconciliation PASS")
    print(f"eligible/reviewed generations: {eligible_count}/{eligible_count}")
    print("review reuse violations: 0")
    print("failed post-validation leaves review-independence authority mutation behind: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"PRODUCTION-EQUIVALENT ENVIRONMENT REVIEW INDEPENDENCE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
