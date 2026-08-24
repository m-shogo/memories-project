#!/usr/bin/env python3
"""Prove fail-closed pair derivation for restore-preflight environment generation eligibility."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def expect_rejected(name: str, action: Callable[[], Any], failure_type: type[BaseException]) -> None:
    try:
        action()
    except failure_type:
        print(f"PASS reject: {name}")
        return
    except Exception as exc:
        raise Fail(f"{name} leaked non-domain exception: {type(exc).__name__}: {exc}") from exc
    raise Fail(f"negative case unexpectedly accepted: {name}")


def load_helper():
    spec = importlib.util.spec_from_file_location("memory_os_environment_generation_eligibility_negative", HELPER)
    require(spec is not None and spec.loader is not None, "cannot load generation eligibility helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeWriter:
    Fail = Fail

    @staticmethod
    def validate_record(row: dict[str, Any]) -> bool:
        value = row.get("syntheticEligible")
        if not isinstance(value, bool):
            raise Fail("syntheticEligible missing")
        return value

    @staticmethod
    def validate_registry_for_append(value: dict[str, Any]) -> list[dict[str, Any]]:
        require(
            value.get("schemaVersion") == "memory-os-production-equivalent-environment-generation-registry.v1",
            "registry schema drift",
        )
        require(value.get("registryClass") == "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS", "registry class drift")
        require(value.get("appendOnly") is True, "registry must remain append-only")
        require(value.get("productionEvidence") is False, "registry production evidence boundary drift")
        rows = value.get("generations")
        count = value.get("registeredGenerationCount")
        require(isinstance(rows, list) and all(isinstance(item, dict) for item in rows), "registry generations invalid")
        require(isinstance(count, int) and not isinstance(count, bool) and count == len(rows), "registeredGenerationCount drift")

        ids: set[str] = set()
        prior_by_environment: dict[str, str] = {}
        for index, item in enumerate(rows):
            generation_id = item.get("generationId")
            environment_id = item.get("environmentId")
            require(isinstance(generation_id, str) and generation_id and generation_id not in ids, f"registry generations[{index}] generationId authority invalid")
            require(isinstance(environment_id, str) and environment_id, f"registry generations[{index}] environmentId invalid")
            ids.add(generation_id)
            expected_supersedes = prior_by_environment.get(environment_id)
            require(item.get("supersedesGenerationId") == expected_supersedes, f"supersedes chain drift for environment {environment_id}")
            prior_by_environment[environment_id] = generation_id
            FakeWriter.validate_record(item)

        current_id = value.get("currentGenerationId")
        if count == 0:
            require(current_id is None, "empty generation registry must have null currentGenerationId")
        else:
            require(current_id == rows[-1].get("generationId"), "currentGenerationId must equal latest append-only registry record")
        return rows


def registry(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "memory-os-production-equivalent-environment-generation-registry.v1",
        "registryClass": "PRODUCTION_EQUIVALENT_ENVIRONMENT_GENERATIONS",
        "appendOnly": True,
        "registeredGenerationCount": len(rows),
        "currentGenerationId": rows[-1]["generationId"] if rows else None,
        "generations": rows,
        "productionEvidence": False,
    }


def row(
    generation_id: str,
    environment_id: str,
    eligible: bool,
    supersedes: str | None = None,
    review_ref: str | None = None,
) -> dict[str, Any]:
    return {
        "generationId": generation_id,
        "environmentId": environment_id,
        "supersedesGenerationId": supersedes,
        "syntheticEligible": eligible,
        "syntheticIndependentReviewRef": review_ref or f"{generation_id}.review.json",
    }


def derive(helper, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Use the explicit in-memory fixture API; path-based derivation is canonical-only."""
    return derive_registry(helper, registry(rows))


def derive_registry(helper, value: dict[str, Any]) -> dict[str, Any]:
    real_loader = helper.load_generation_writer
    real_review_ref = helper.independent_review_ref_for_row
    helper.load_generation_writer = lambda: FakeWriter()
    helper.independent_review_ref_for_row = lambda writer, item: item["syntheticIndependentReviewRef"]
    try:
        return helper.derive_registry(value)
    finally:
        helper.load_generation_writer = real_loader
        helper.independent_review_ref_for_row = real_review_ref


def main() -> int:
    require(HELPER.is_file(), "generation eligibility helper missing")
    helper = load_helper()
    require(helper.canonical_repo_file(helper.GEN_WRITER, "generation writer") == helper.GEN_WRITER, "canonical generation writer rejected")

    repo_substitute = ROOT / "scripts/validate-memory-os-operability.py"
    require(repo_substitute.is_file(), "repo-contained writer substitute missing")
    original_writer = helper.GEN_WRITER
    try:
        helper.GEN_WRITER = repo_substitute
        expect_rejected("semantic generation writer repo-contained substitution", helper.load_generation_writer, helper.Fail)
    finally:
        helper.GEN_WRITER = original_writer

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-writer-outside-") as outside_tmp:
        outside_writer = Path(outside_tmp) / "outside-generation-writer.py"
        outside_writer.write_text("VALUE = 1\n", encoding="utf-8")
        escaped_link = ROOT / ".tmp-generation-eligibility-writer-escape.py"
        loop_link = ROOT / ".tmp-generation-eligibility-writer-loop.py"
        original_writer = helper.GEN_WRITER
        try:
            helper.GEN_WRITER = outside_writer
            expect_rejected("semantic generation writer absolute path escapes repository", helper.load_generation_writer, helper.Fail)
            escaped_link.symlink_to(outside_writer)
            helper.GEN_WRITER = escaped_link
            expect_rejected("semantic generation writer symlink escapes repository", helper.load_generation_writer, helper.Fail)
            loop_link.symlink_to(loop_link.name)
            helper.GEN_WRITER = loop_link
            expect_rejected("semantic generation writer symlink loop", helper.load_generation_writer, helper.Fail)
        finally:
            helper.GEN_WRITER = original_writer
            for path in (escaped_link, loop_link):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass

    with tempfile.TemporaryDirectory(prefix="memory-os-generation-eligibility-path-negative-") as tmp:
        alternate = Path(tmp) / "registry.json"
        alternate.write_text("{}\n", encoding="utf-8")
        expect_rejected(
            "noncanonical generation registry path",
            lambda: helper.derive(alternate),
            helper.Fail,
        )
        expect_rejected(
            "missing noncanonical generation registry path",
            lambda: helper.derive(Path(tmp) / "missing.json"),
            helper.Fail,
        )

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

    reused_review = registry([
        row("pegen-a-v1", "env-a", True, review_ref="shared-environment-review.json"),
        row("pegen-b-v1", "env-b", True, review_ref="shared-environment-review.json"),
    ])
    expect_rejected(
        "eligible generations reuse environment independent review evidence",
        lambda: derive_registry(helper, reused_review),
        helper.Fail,
    )

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

    class_drift = registry([])
    class_drift["registryClass"] = "UNRELATED_GENERATION_REGISTRY"
    expect_rejected(
        "generation registry class drift",
        lambda: derive_registry(helper, class_drift),
        helper.Fail,
    )

    cross_environment = registry([
        row("pegen-a-v1", "env-a", True),
        row("pegen-b-v1", "env-b", True, "pegen-a-v1"),
    ])
    expect_rejected(
        "cross-environment generation supersedes",
        lambda: derive_registry(helper, cross_environment),
        helper.Fail,
    )

    skipped_predecessor = registry([
        row("pegen-a-v1", "env-a", True),
        row("pegen-a-v2", "env-a", True, "pegen-missing"),
    ])
    expect_rejected(
        "same-environment generation skips canonical predecessor",
        lambda: derive_registry(helper, skipped_predecessor),
        helper.Fail,
    )

    current_pointer_drift = registry([
        row("pegen-a-v1", "env-a", True),
        row("pegen-b-v1", "env-b", True),
    ])
    current_pointer_drift["currentGenerationId"] = "pegen-a-v1"
    expect_rejected(
        "current generation pointer is not latest append-only row",
        lambda: derive_registry(helper, current_pointer_drift),
        helper.Fail,
    )

    empty_pointer_drift = registry([])
    empty_pointer_drift["currentGenerationId"] = "pegen-a-v1"
    expect_rejected(
        "empty registry has non-null current generation",
        lambda: derive_registry(helper, empty_pointer_drift),
        helper.Fail,
    )

    boolean_count = registry([
        row("pegen-a-v1", "env-a", True),
    ])
    boolean_count["registeredGenerationCount"] = True
    expect_rejected(
        "boolean registered generation count",
        lambda: derive_registry(helper, boolean_count),
        helper.Fail,
    )

    print("Memory OS environment generation eligibility negative suite PASS")
    print("registered history discarded: false")
    print("ineligible generation counted as pair: false")
    print("superseded generation counted as current pair: false")
    print("same environment can restore-pair with itself: false")
    print("eligible environment independent review reuse accepted: false")
    print("generation registry class drift accepted: false")
    print("cross-environment supersedes accepted: false")
    print("same-environment predecessor skip accepted: false")
    print("current generation pointer drift accepted: false")
    print("boolean registered generation counts accepted: false")
    print("noncanonical path-based registry derivation accepted: false")
    print("generation writer repo-contained substitution accepted: false")
    print("generation writer import escape accepted: false")
    print("generation writer symlink loop accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"ENVIRONMENT GENERATION ELIGIBILITY NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
