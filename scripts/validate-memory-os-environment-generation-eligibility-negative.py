#!/usr/bin/env python3
"""Prove fail-closed pair derivation for restore-preflight environment generation eligibility."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_helper():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_eligibility_negative", HELPER)
    require(spec is not None and spec.loader is not None, "cannot load generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeWriter:
    @staticmethod
    def validate_record(row: dict[str, Any]) -> bool:
        value = row.get("syntheticEligible")
        if not isinstance(value, bool):
            raise Fail("syntheticEligible missing")
        return value


def registry(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
        "appendOnly": True,
        "registeredGenerationCount": len(rows),
        "currentGenerationId": rows[-1]["generationId"] if rows else None,
        "generations": rows,
        "productionEvidence": False,
    }


def row(generation_id: str, environment_id: str, eligible: bool, supersedes: str | None = None) -> dict[str, Any]:
    return {
        "generationId": generation_id,
        "environmentId": environment_id,
        "supersedesGenerationId": supersedes,
        "syntheticEligible": eligible,
    }


def derive(helper, rows: list[dict[str, Any]]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="memory-os-generation-eligibility-negative-") as tmp:
        path = Path(tmp) / "registry.json"
        path.write_text(json.dumps(registry(rows), indent=2) + "\n", encoding="utf-8")
        real_loader = helper.load_generation_writer
        helper.load_generation_writer = lambda: FakeWriter()
        try:
            return helper.derive(path)
        finally:
            helper.load_generation_writer = real_loader


def main() -> int:
    require(HELPER.is_file(), "generation eligibility helper missing")
    helper = load_helper()

    empty = derive(helper, [])
    require(empty["eligibleDirectedPairCount"] == 0, "empty registry cannot have restore pair")
    print("PASS: empty registry has zero eligible pairs")

    planned_pair = derive(helper, [
        row("pegen-a-v1", "env-a", False),
        row("pegen-b-v1", "env-b", False),
    ])
    require(planned_pair["registeredGenerationCount"] == 2, "planned fixture registration count drift")
    require(planned_pair["preflightEligibleGenerationCount"] == 0, "planned generations cannot be eligible")
    require(planned_pair["eligibleDirectedPairCount"] == 0, "two registered ineligible generations cannot form restore pair")
    print("PASS: registration alone does not form restore pair")

    one_eligible = derive(helper, [
        row("pegen-a-v1", "env-a", True),
        row("pegen-b-v1", "env-b", False),
    ])
    require(one_eligible["preflightEligibleGenerationCount"] == 1, "single eligible generation count drift")
    require(one_eligible["eligibleDirectedPairCount"] == 0, "one eligible generation cannot form restore pair")
    print("PASS: one eligible generation has zero pairs")

    same_environment = derive(helper, [
        row("pegen-a-v1", "env-a", True),
        row("pegen-a-v2", "env-a", True, "pegen-a-v1"),
    ])
    require(same_environment["preflightEligibleGenerationCount"] == 2, "historical eligible count drift")
    require(same_environment["unsupersededPreflightEligibleGenerationCount"] == 1, "superseded eligible generation must leave current set")
    require(same_environment["distinctPreflightEligibleEnvironmentCount"] == 1, "same environment should count once")
    require(same_environment["eligibleDirectedPairCount"] == 0, "same environment generations cannot form restore pair")
    print("PASS: supersession/same environment cannot form pair")

    two_distinct = derive(helper, [
        row("pegen-a-v1", "env-a", True),
        row("pegen-b-v1", "env-b", True),
    ])
    require(two_distinct["unsupersededPreflightEligibleGenerationCount"] == 2, "two eligible generation count drift")
    require(two_distinct["distinctPreflightEligibleEnvironmentCount"] == 2, "two distinct environment count drift")
    require(two_distinct["eligibleDirectedPairCount"] == 2, "two eligible environments must form two directed pairs")
    print("PASS: two eligible distinct environments form exactly two directed pairs")

    three_distinct = derive(helper, [
        row("pegen-a-v1", "env-a", True),
        row("pegen-b-v1", "env-b", True),
        row("pegen-c-v1", "env-c", True),
    ])
    require(three_distinct["eligibleDirectedPairCount"] == 6, "three eligible environments must form six directed pairs")
    print("PASS: three eligible distinct environments form six directed pairs")

    superseded_one_of_three = derive(helper, [
        row("pegen-a-v1", "env-a", True),
        row("pegen-a-v2", "env-a", True, "pegen-a-v1"),
        row("pegen-b-v1", "env-b", True),
    ])
    require(superseded_one_of_three["preflightEligibleGenerationCount"] == 3, "historical eligible count must preserve superseded row")
    require(superseded_one_of_three["unsupersededPreflightEligibleGenerationCount"] == 2, "current eligible set must exclude superseded row")
    require(superseded_one_of_three["eligibleDirectedPairCount"] == 2, "superseded generation must not add extra restore pairs")
    print("PASS: superseded eligible history does not inflate current pairs")

    print("Memory OS environment generation eligibility negative suite PASS")
    print("registered history discarded: false")
    print("ineligible generation counted as pair: false")
    print("superseded generation counted as current pair: false")
    print("same environment can restore-pair with itself: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION ELIGIBILITY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
