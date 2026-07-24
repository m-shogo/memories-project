#!/usr/bin/env python3
"""Validate the memory provenance and interpretation invariants.

The memory-domain principles already existed as prose in docs/formal-invariants.md
and docs/trust-and-provenance.md. Prose gates nothing: an implementation can
contradict every line of it and the whole test suite still passes. This script
turns the invariant set into something that can fail.

It does two independent things:

  1. Structural: the invariant set validates against its schema, every invariant
     names an ancestor it derives from, and every gap and case identifier is
     unique and well-formed.
  2. Semantic: each case in the case set is decided from the invariant set
     alone, and the decision must match the recorded expectation. The decision
     function deliberately knows nothing about tables or columns, because none
     exist yet — it reasons over origin, assertion kind, source reference,
     supersession target and owner, which is the whole of what this checkpoint
     fixes.

Exit status is non-zero on any mismatch, so a future implementation that
weakens one of these decisions fails CI rather than passing quietly.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INVARIANTS = REPO_ROOT / "docs/fixtures/memory-os-security/memory-provenance-invariants.round9.valid.v1.json"
CASES = REPO_ROOT / "docs/fixtures/memory-os-security/memory-provenance-cases.round9.v1.json"
SCHEMA = REPO_ROOT / "docs/schemas/memory-os-security/memory-provenance-invariant-set.v1.schema.json"

# Deny reasons the case set is allowed to use. A case citing anything else is a
# typo or an invented rule, and either way must not pass silently.
DENY_REASONS = {
    "MEM_AI_ORIGIN_CANNOT_BE_RECORD",
    "MEM_ORIGIN_CANNOT_BE_USER_FACT",
    "MEM_SOURCE_REF_REQUIRED",
    "MEM_RECORD_NOT_SUPERSEDABLE",
    "MEM_AI_CANNOT_SUPERSEDE_PERSON",
    "MEM_CROSS_TENANT_LINK",
    "MEM_EVALUATION_FIELD_FORBIDDEN",
    "MEM_DUPLICATE_NOT_INDEPENDENT",
    "MEM_PRESENTATION_POLICY_NOT_BOOLEAN",
    "MEM_PERSONA_RECONSTRUCTION",
}

AI_ORIGINS = {"ai_summary", "ai_inferred"}
PERSON_ASSERTIONS = {"record", "later_interpretation", "correction"}


def decide(item: dict, origins: dict, assertions: dict) -> str | None:
    """Return a deny reason, or None to allow.

    Order matters only for which reason is reported first; every check below is
    independent, and a case that trips two of them is still denied.
    """
    origin = item.get("origin")
    assertion = item.get("assertion")

    # Every origin in the set requires a source reference, including the
    # account holder's own. Without one, an injected item and a captured one
    # are the same thing.
    if origins[origin]["requiresSourceRef"] and not item.get("sourceRef"):
        return "MEM_SOURCE_REF_REQUIRED"

    # An origin that cannot become the account holder's fact cannot be stored
    # under an assertion kind that speaks for them.
    if assertion in PERSON_ASSERTIONS and not origins[origin]["canBecomeUserFact"]:
        return (
            "MEM_AI_ORIGIN_CANNOT_BE_RECORD"
            if origin in AI_ORIGINS
            else "MEM_ORIGIN_CANNOT_BE_USER_FACT"
        )

    supersedes = item.get("supersedes")
    if supersedes:
        if supersedes.get("owner") != item.get("owner"):
            return "MEM_CROSS_TENANT_LINK"
        # A model's output never overrides what a person wrote.
        if origin in AI_ORIGINS and supersedes["targetAssertion"] in PERSON_ASSERTIONS:
            return "MEM_AI_CANNOT_SUPERSEDE_PERSON"
        if not assertions[supersedes["targetAssertion"]]["supersedable"]:
            return "MEM_RECORD_NOT_SUPERSEDABLE"

    if item.get("evaluation"):
        return "MEM_EVALUATION_FIELD_FORBIDDEN"

    # Copies sharing one origin are one piece of evidence.
    claimed = item.get("claimsIndependentEvidence")
    if claimed is not None and claimed > item.get("distinctOrigins", 0):
        return "MEM_DUPLICATE_NOT_INDEPENDENT"

    # Storing is not consent to search, analyse, resurface or display. The one
    # shape known to be wrong is a single boolean.
    if isinstance(item.get("presentationPolicy"), bool):
        return "MEM_PRESENTATION_POLICY_NOT_BOOLEAN"

    if item.get("presentsAsPerson"):
        return "MEM_PERSONA_RECONSTRUCTION"

    return None


def main() -> int:
    invariant_set = json.loads(INVARIANTS.read_text())
    case_set = json.loads(CASES.read_text())
    failures: list[str] = []

    try:
        from jsonschema import Draft202012Validator

        Draft202012Validator(json.loads(SCHEMA.read_text())).validate(invariant_set)
    except ImportError:
        print("jsonschema not installed; structural validation skipped", file=sys.stderr)
        return 2

    origins = {value["value"]: value for value in invariant_set["originAxis"]["values"]}
    assertions = {value["value"]: value for value in invariant_set["assertionAxis"]["values"]}
    invariant_ids = {entry["invariantId"] for entry in invariant_set["invariants"]}

    if len(invariant_ids) != len(invariant_set["invariants"]):
        failures.append("duplicate invariant identifiers")

    # An invariant with no ancestor is a new product decision smuggled in as a
    # restatement. The schema requires the field; this requires it to be real.
    for entry in invariant_set["invariants"]:
        if not all(str(source).strip() for source in entry["derivedFrom"]):
            failures.append(f"{entry['invariantId']}: empty derivedFrom entry")
        # An invariant is either currently violated or its violation is closed,
        # never both: the two states are contradictory and a fixture asserting
        # both would misreport shipped reality.
        if entry.get("currentlyViolatedBy") and entry.get("closedBy"):
            failures.append(f"{entry['invariantId']}: currentlyViolatedBy and closedBy both set")

    seen_cases: set[str] = set()
    for case in case_set["cases"]:
        case_id = case["caseId"]
        if case_id in seen_cases:
            failures.append(f"{case_id}: duplicate case id")
        seen_cases.add(case_id)

        for cited in case["invariants"]:
            if cited not in invariant_ids:
                failures.append(f"{case_id}: cites unknown invariant {cited}")

        expected = case["expect"]
        if expected == "deny":
            reason = case.get("denyReason")
            if reason not in DENY_REASONS:
                failures.append(f"{case_id}: unknown denyReason {reason!r}")

        actual = decide(case["item"], origins, assertions)
        if expected == "allow" and actual is not None:
            failures.append(f"{case_id}: expected allow, denied with {actual}")
        elif expected == "deny" and actual is None:
            failures.append(f"{case_id}: expected deny ({case.get('denyReason')}), allowed")
        elif expected == "deny" and actual != case.get("denyReason"):
            failures.append(
                f"{case_id}: expected deny {case.get('denyReason')}, got {actual}"
            )

    # Every deny reason must be exercised, or the vocabulary is aspirational.
    exercised = {case.get("denyReason") for case in case_set["cases"] if case["expect"] == "deny"}
    for unused in sorted(DENY_REASONS - exercised):
        failures.append(f"deny reason {unused} is never exercised by a case")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}", file=sys.stderr)
        return 1

    allows = sum(1 for case in case_set["cases"] if case["expect"] == "allow")
    denies = len(case_set["cases"]) - allows
    print(f"memory provenance invariants: {len(invariant_ids)}")
    print(f"gaps recorded: {len(invariant_set['originAxis']['gaps'])}")
    print(f"semantic cases: {allows} allow / {denies} deny")
    violated = [
        entry["invariantId"]
        for entry in invariant_set["invariants"]
        if entry.get("currentlyViolatedBy")
    ]
    if violated:
        print(f"invariants violated by shipped code: {', '.join(violated)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
