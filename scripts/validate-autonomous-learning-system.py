#!/usr/bin/env python3
"""Fail-closed validator for the autonomous improvement/learning contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CONTRACT = Path("contracts/operations/autonomous-learning-system.json")
LEARNING = Path("docs/operations/AUTONOMOUS-OPS-LEARNING.md")
VALIDATOR = Path("scripts/validate-autonomous-learning-system.py")
NEGATIVE_VALIDATOR = Path("scripts/validate-autonomous-learning-system-negative.py")
CI_ENTRYPOINT = Path("scripts/validate-memory-os-entry-docs.py")
EXPECTED_LOOP = [
    "observe", "diagnose", "search_prior_knowledge", "change", "validate",
    "persist_learning", "verify_authority", "continue",
]
FAILURE_FIELDS = {"symptom", "evidence", "rootCauseOrUnknown", "failedApproach", "correction", "recurrenceGuard", "retryCondition"}
SUCCESS_FIELDS = {"outcome", "evidence", "whySafe", "reusableMechanism", "protectedAuthorityCheck"}
TRUE_RULES = {
    "searchBeforeChange", "sameFailedApproachRequiresChangedPrecondition",
    "preferExecutableGuard", "verifyProtectedAuthorityAfterChange",
    "scopedBlockerDoesNotStopIndependentWork", "unchangedBlockerIsNotRetried",
    "historyIsAppendOnly", "learningIsNeverProductionEvidence",
    "learningCannotPromoteReadiness", "ciReachabilityRequired",
}


class ValidationFailure(RuntimeError):
    pass


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing authority: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationFailure(f"root must be an object: {path}")
    return value


def exact_string_set(value: Any, expected: set[str], field: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValidationFailure(f"{field} must be a string list")
    if len(value) != len(set(value)):
        raise ValidationFailure(f"{field} contains duplicates")
    if set(value) != expected:
        raise ValidationFailure(f"{field} changed: {value!r}")


def validate(repo_root: Path) -> None:
    contract = load_object(repo_root / CONTRACT)
    if contract.get("schemaVersion") != "autonomous-learning-system.0.1":
        raise ValidationFailure("unsupported schemaVersion")
    if contract.get("loop") != EXPECTED_LOOP:
        raise ValidationFailure("closed-loop execution order changed")
    exact_string_set(contract.get("requiredFailureFields"), FAILURE_FIELDS, "requiredFailureFields")
    exact_string_set(contract.get("requiredSuccessFields"), SUCCESS_FIELDS, "requiredSuccessFields")

    rules = contract.get("rules")
    if not isinstance(rules, dict):
        raise ValidationFailure("rules must be an object")
    for rule in TRUE_RULES:
        if rules.get(rule) is not True:
            raise ValidationFailure(f"mandatory learning rule must remain true: {rule}")

    protected = contract.get("protectedInvariants")
    if not isinstance(protected, dict):
        raise ValidationFailure("protectedInvariants must be an object")
    if protected.get("productionDecisionDefault") != "NO_GO":
        raise ValidationFailure("learning must not weaken the NO_GO default")
    if protected.get("opsP0007EvidenceMustBeReal") is not True:
        raise ValidationFailure("OPS-P0-007 real-evidence boundary must remain true")
    if protected.get("humanPromotionReviewIsSeparate") is not True:
        raise ValidationFailure("human promotion review must remain separate")
    if contract.get("authority") != LEARNING.as_posix():
        raise ValidationFailure("learning authority path changed")
    if contract.get("validator") != VALIDATOR.as_posix():
        raise ValidationFailure("executable learning guard binding changed")
    if contract.get("negativeValidator") != NEGATIVE_VALIDATOR.as_posix():
        raise ValidationFailure("negative learning guard binding changed")
    if contract.get("ciEntrypoint") != CI_ENTRYPOINT.as_posix():
        raise ValidationFailure("learning CI entrypoint binding changed")
    if not (repo_root / VALIDATOR).is_file():
        raise ValidationFailure("bound executable learning guard is missing")
    if not (repo_root / NEGATIVE_VALIDATOR).is_file():
        raise ValidationFailure("bound negative learning guard is missing")
    try:
        ci_entrypoint = (repo_root / CI_ENTRYPOINT).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure(f"bound learning CI entrypoint is missing: {CI_ENTRYPOINT}") from exc
    for guard in (VALIDATOR.as_posix(), NEGATIVE_VALIDATOR.as_posix()):
        if guard not in ci_entrypoint:
            raise ValidationFailure(f"learning CI entrypoint does not invoke bound guard: {guard}")

    try:
        learning = (repo_root / LEARNING).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing learning authority: {LEARNING}") from exc
    for phrase in (
        "not production evidence",
        "Do not repeatedly retry an unchanged permission failure",
        "Repeating a known failed approach without changed preconditions is a regression",
        "Prefer executable guards over prose",
        "Human production-promotion review is a separate non-automatic decision",
    ):
        if phrase not in learning:
            raise ValidationFailure(f"learning authority lost invariant: {phrase}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        validate(args.repo_root.resolve())
    except ValidationFailure as exc:
        print(f"AUTONOMOUS LEARNING VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"AUTONOMOUS LEARNING VALIDATION FAILED WITH UNEXPECTED ERROR: {exc}", file=sys.stderr)
        return 2
    print("Autonomous improvement/learning contract validation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
