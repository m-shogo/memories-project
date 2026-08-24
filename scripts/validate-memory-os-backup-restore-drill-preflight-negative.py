#!/usr/bin/env python3
"""Prove restore drill preflight rejects stale or semantically weakened authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-preflight.py"
CONTRACT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_REGISTRY = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
TEMP_PARENT = ROOT / "contracts/operations"
NEGATIVE_REF = "scripts/validate-memory-os-backup-restore-drill-preflight-negative.py"
SEMANTIC_HELPER_REF = "scripts/memory_os_environment_generation_eligibility.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"root must be object: {path}")
    return value


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_preflight_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load preflight validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(validator: Any, canonical: dict[str, Any], name: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    bad = copy.deepcopy(canonical)
    mutate(bad)
    with tempfile.TemporaryDirectory(prefix=".memory-os-preflight-negative-", dir=TEMP_PARENT) as tmp:
        path = Path(tmp) / "contract.json"
        path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
        original = validator.CONTRACT
        validator.CONTRACT = path
        try:
            validator.main()
        except validator.Fail:
            print(f"PASS reject: {name}")
            return
        finally:
            validator.CONTRACT = original
    raise Fail(f"negative case unexpectedly accepted: {name}")


def expect_path_rejected(validator: Any, name: str, path: Path) -> None:
    try:
        validator.load(path)
    except validator.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"escaped path unexpectedly accepted: {name}")


def expect_state_rejected(
    validator: Any,
    generations: dict[str, Any],
    objectives: dict[str, Any],
    drill_registry: dict[str, Any],
    name: str,
    mutate: Callable[[dict[str, Any], dict[str, Any], dict[str, Any]], None],
) -> None:
    bad_generations = copy.deepcopy(generations)
    bad_objectives = copy.deepcopy(objectives)
    bad_drill_registry = copy.deepcopy(drill_registry)
    mutate(bad_generations, bad_objectives, bad_drill_registry)
    try:
        validator.derive_state(bad_generations, bad_objectives, bad_drill_registry)
    except validator.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative state case unexpectedly accepted: {name}")


def expect_helper_authority_substitution_rejected(
    validator: Any,
    generations: dict[str, Any],
    objectives: dict[str, Any],
    drill_registry: dict[str, Any],
) -> None:
    original = validator.ELIGIBILITY_HELPER
    validator.ELIGIBILITY_HELPER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
    try:
        validator.derive_state(copy.deepcopy(generations), copy.deepcopy(objectives), copy.deepcopy(drill_registry))
    except validator.Fail as exc:
        require("eligibility authority" in str(exc), "runtime semantic helper substitution rejected for unexpected reason")
        print("PASS reject: runtime semantic eligibility helper substitution")
        return
    finally:
        validator.ELIGIBILITY_HELPER = original
    raise Fail("runtime semantic eligibility helper substitution unexpectedly accepted")


def expect_unexpected_helper_exception_preserved(
    validator: Any,
    generations: dict[str, Any],
    objectives: dict[str, Any],
    drill_registry: dict[str, Any],
) -> None:
    class BrokenHelper:
        class Fail(RuntimeError):
            pass

        @staticmethod
        def derive_registry(_registry: dict[str, Any]) -> dict[str, Any]:
            raise TypeError("synthetic unexpected semantic helper failure")

    original = validator.load_eligibility_helper
    validator.load_eligibility_helper = lambda: BrokenHelper
    try:
        validator.derive_state(copy.deepcopy(generations), copy.deepcopy(objectives), copy.deepcopy(drill_registry))
    except TypeError as exc:
        require(str(exc) == "synthetic unexpected semantic helper failure", "unexpected helper exception identity drift")
        print("PASS preserve: unexpected semantic helper TypeError")
        return
    except validator.Fail as exc:
        raise Fail(f"unexpected helper exception was normalized as domain rejection: {exc}") from exc
    finally:
        validator.load_eligibility_helper = original
    raise Fail("unexpected helper exception was silently accepted")


def main() -> int:
    require(
        VALIDATOR.is_file()
        and CONTRACT.is_file()
        and GEN_REGISTRY.is_file()
        and OBJECTIVES.is_file()
        and DRILL_REGISTRY.is_file()
        and TEMP_PARENT.is_dir(),
        "preflight negative foundation missing",
    )
    validator = load_validator()
    canonical = load(CONTRACT)
    generations = load(GEN_REGISTRY)
    objectives = load(OBJECTIVES)
    drill_registry = load(DRILL_REGISTRY)
    require(canonical.get("negativeAdmissionValidator") == NEGATIVE_REF, "preflight contract negativeAdmissionValidator drift")
    require((ROOT / NEGATIVE_REF).is_file(), "preflight negativeAdmissionValidator artifact missing")
    require(canonical.get("semanticEligibilityHelper") == SEMANTIC_HELPER_REF, "preflight semanticEligibilityHelper drift")
    require((ROOT / SEMANTIC_HELPER_REF).is_file(), "preflight semanticEligibilityHelper artifact missing")
    current_state = canonical.get("currentState")
    readiness = canonical.get("readiness")
    require(isinstance(current_state, dict) and set(current_state) == validator.STATE_FIELDS, "canonical preflight currentState is not exact")
    require(isinstance(readiness, dict) and set(readiness) == validator.READINESS_FIELDS, "canonical preflight readiness is not exact")
    print("PASS baseline: canonical preflight negative authority and field sets are exact")

    expect_path_rejected(
        validator,
        "preflight contract path escapes repository root",
        Path(tempfile.gettempdir()) / "memory-os-preflight-outside-root.json",
    )
    expect_rejected(
        validator,
        canonical,
        "semantic eligibility helper authority drift",
        lambda value: value.__setitem__("semanticEligibilityHelper", "scripts/register-memory-os-production-equivalent-environment-generation.py"),
    )
    expect_rejected(
        validator,
        canonical,
        "legacy distinct unsuperseded environment alias",
        lambda value: value["currentState"].__setitem__("distinctUnsupersededEnvironmentCount", 0),
    )
    expect_rejected(
        validator,
        canonical,
        "legacy two-generation readiness alias",
        lambda value: value["readiness"].__setitem__("twoDistinctUnsupersededEnvironmentGenerationsAvailable", False),
    )
    expect_rejected(
        validator,
        canonical,
        "unexpected future currentState field",
        lambda value: value["currentState"].__setitem__("unexpectedAuthorityAlias", False),
    )
    expect_rejected(
        validator,
        canonical,
        "boolean canonical registered generation count",
        lambda value: value["currentState"].__setitem__("registeredGenerationCount", False),
    )
    expect_rejected(
        validator,
        canonical,
        "boolean canonical approved objective count",
        lambda value: value["currentState"].__setitem__("approvedRecoveryObjectiveCount", False),
    )
    expect_rejected(
        validator,
        canonical,
        "unexpected future readiness field",
        lambda value: value["readiness"].__setitem__("unexpectedReadinessAlias", False),
    )
    expect_rejected(
        validator,
        canonical,
        "generation blocker without semantic preflight eligibility",
        lambda value: value["blockingPrerequisiteSemantics"][validator.GEN_BLOCKER].__setitem__("requiresSemanticPreflightEligibility", False),
    )
    expect_rejected(
        validator,
        canonical,
        "generation blocker without distinct environment binding",
        lambda value: value["blockingPrerequisiteSemantics"][validator.GEN_BLOCKER].__setitem__("requiresDistinctEnvironmentId", False),
    )
    expect_rejected(
        validator,
        canonical,
        "generation blocker weakened to one generation",
        lambda value: value["blockingPrerequisiteSemantics"][validator.GEN_BLOCKER].__setitem__("minimumEnvironmentGenerationCount", 1),
    )
    expect_rejected(
        validator,
        canonical,
        "objective blocker without current approved objective binding",
        lambda value: value["blockingPrerequisiteSemantics"][validator.OBJECTIVE_BLOCKER].__setitem__("requiresCurrentApprovedRecoveryObjective", False),
    )
    expect_state_rejected(
        validator,
        generations,
        objectives,
        drill_registry,
        "generation registry schema drift",
        lambda g, _o, _d: g.__setitem__("schemaVersion", "memory-os-production-equivalent-environment-generation-registry.v0"),
    )
    expect_state_rejected(
        validator,
        generations,
        objectives,
        drill_registry,
        "boolean approved recovery objective count",
        lambda _g, o, _d: o.__setitem__("approvedObjectiveCount", False),
    )
    expect_state_rejected(
        validator,
        generations,
        objectives,
        drill_registry,
        "boolean registered drill request count",
        lambda _g, _o, d: d.__setitem__("registeredRequestCount", False),
    )
    expect_state_rejected(
        validator,
        generations,
        objectives,
        drill_registry,
        "boolean current executable drill request count",
        lambda _g, _o, d: d.__setitem__("currentExecutableRequestCount", False),
    )
    expect_helper_authority_substitution_rejected(validator, generations, objectives, drill_registry)
    expect_unexpected_helper_exception_preserved(validator, generations, objectives, drill_registry)

    print("Memory OS restore drill preflight negative authority-shape suite PASS")
    print("escaped artifact path accepted: false")
    print("negative validator contract binding: true")
    print("shared semantic eligibility helper contract binding: true")
    print("runtime semantic eligibility helper substitution accepted: false")
    print("generation registry schema drift accepted: false")
    print("stable blocker ids require semantic preflight gates: true")
    print("registered generation count alone satisfies blocker: false")
    print("boolean registry/current-state counts accepted: false")
    print("unexpected semantic helper exceptions normalized as domain rejection: false")
    print("stale state aliases accepted: false")
    print("unexpected readiness aliases accepted: false")
    print("canonical authority mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE DRILL PREFLIGHT NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
