#!/usr/bin/env python3
"""Negative suite for restore preflight / semantic-generation consistency authority."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency.py"
HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
ELIGIBILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-production-equivalent-environment-eligibility.py"
OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"
DRILL_WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"
PREFLIGHT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
ELIGIBILITY = ROOT / "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_REQUESTS = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"
DRILL_VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-drill-request.py"
SUBSTITUTE_SCRIPT = ROOT / "scripts/validate-memory-os-operability.py"


class Fail(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Fail(f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Fail(f"cannot load module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_bytes() -> dict[str, bytes]:
    return {
        "PREFLIGHT": PREFLIGHT.read_bytes(),
        "ELIGIBILITY": ELIGIBILITY.read_bytes(),
        "OBJECTIVES": OBJECTIVES.read_bytes(),
        "DRILL_REQUESTS": DRILL_REQUESTS.read_bytes(),
    }


def assert_canonical_unchanged(before: dict[str, bytes], label: str) -> None:
    for field, path in (
        ("PREFLIGHT", PREFLIGHT),
        ("ELIGIBILITY", ELIGIBILITY),
        ("OBJECTIVES", OBJECTIVES),
        ("DRILL_REQUESTS", DRILL_REQUESTS),
    ):
        if path.read_bytes() != before[field]:
            raise Fail(f"canonical {field} mutated while rejecting {label}")


def expect_semantic_rejection(
    validator,
    helper,
    eligibility_validator,
    objectives_writer,
    drill_writer,
    baseline: dict[str, dict[str, Any]],
    name: str,
    mutate: Callable[[dict[str, dict[str, Any]]], None],
) -> None:
    state = copy.deepcopy(baseline)
    mutate(state)

    class FixtureDrillValidator:
        class Fail(RuntimeError):
            pass

        @staticmethod
        def main() -> int:
            return 0

    try:
        validator.validate_state(
            state["preflight"],
            state["eligibility"],
            state["objectives"],
            state["drill"],
            helper=helper,
            eligibility_validator=eligibility_validator,
            objectives_writer=objectives_writer,
            drill_writer=drill_writer,
            drill_validator=FixtureDrillValidator,
        )
    except validator.Fail:
        pass
    else:
        raise Fail(f"negative case unexpectedly accepted: {name}")


def expect_authority_rejection(validator, field: str, substitute: Path) -> None:
    before = canonical_bytes()
    original = getattr(validator, field)
    setattr(validator, field, substitute)
    try:
        try:
            validator.main()
        except validator.Fail:
            pass
        else:
            raise Fail(f"authority substitution unexpectedly accepted: {field}")
        assert_canonical_unchanged(before, field)
    finally:
        setattr(validator, field, original)


def expect_helper_rejection(validator, field: str, replacement: Any) -> None:
    before = canonical_bytes()
    original = getattr(validator, field)
    setattr(validator, field, replacement)
    try:
        try:
            validator.main()
        except validator.Fail:
            pass
        else:
            raise Fail(f"execution helper substitution unexpectedly accepted: {field}")
        assert_canonical_unchanged(before, field)
    finally:
        setattr(validator, field, original)


def main() -> int:
    validator = load_module(VALIDATOR, "memory_os_preflight_consistency_negative_target")
    helper = load_module(HELPER, "memory_os_preflight_consistency_negative_helper")
    eligibility_validator = load_module(ELIGIBILITY_VALIDATOR, "memory_os_preflight_consistency_negative_eligibility")
    objectives_writer = load_module(OBJECTIVES_WRITER, "memory_os_preflight_consistency_negative_objectives")
    drill_writer = load_module(DRILL_WRITER, "memory_os_preflight_consistency_negative_drill_writer")
    strict = helper.derive()
    strict_pair_count = strict.get("eligibleDirectedPairCount")
    if not isinstance(strict_pair_count, int) or isinstance(strict_pair_count, bool) or strict_pair_count < 0:
        raise Fail("canonical strict pair count invalid before negative suite")

    baseline = {
        "preflight": load_json(PREFLIGHT),
        "eligibility": load_json(ELIGIBILITY),
        "objectives": load_json(OBJECTIVES),
        "drill": load_json(DRILL_REQUESTS),
    }

    cases: list[tuple[str, Callable[[dict[str, dict[str, Any]]], None]]] = [
        ("boolean preflight pair count", lambda state: state["preflight"]["currentState"].__setitem__("eligibleDirectedSourceTargetPairCount", True)),
        ("preflight pair count exceeds strict semantic authority", lambda state: state["preflight"]["currentState"].__setitem__("eligibleDirectedSourceTargetPairCount", strict_pair_count + 1)),
        ("preflight production readiness promotion", lambda state: state["preflight"]["currentState"].__setitem__("productionReady", True)),
        ("preflight production decision promotion", lambda state: state["preflight"]["currentState"].__setitem__("productionDecision", "GO")),
        ("eligibility production decision promotion", lambda state: state["eligibility"]["currentBoundary"].__setitem__("productionDecision", "GO")),
        ("boolean approved objective count", lambda state: state["objectives"].__setitem__("approvedObjectiveCount", True)),
        ("objective schema drift", lambda state: state["objectives"].__setitem__("schemaVersion", "memory-os-recovery-objectives-registry.corrupt")),
        ("objective append-only disabled", lambda state: state["objectives"].__setitem__("appendOnly", False)),
        ("objective production evidence promotion", lambda state: state["objectives"].__setitem__("productionEvidence", True)),
        ("objective production readiness promotion", lambda state: state["objectives"].__setitem__("productionReady", True)),
        ("boolean registered request count", lambda state: state["drill"].__setitem__("registeredRequestCount", True)),
        ("boolean current executable request count", lambda state: state["drill"].__setitem__("currentExecutableRequestCount", True)),
        ("drill schema drift", lambda state: state["drill"].__setitem__("schemaVersion", "memory-os-backup-restore-drill-request-registry.corrupt")),
        ("drill registry class drift", lambda state: state["drill"].__setitem__("registryClass", "CORRUPT")),
        ("drill append-only disabled", lambda state: state["drill"].__setitem__("appendOnly", False)),
        ("drill production evidence promotion", lambda state: state["drill"].__setitem__("productionEvidence", True)),
        ("drill production readiness promotion", lambda state: state["drill"].__setitem__("productionReady", True)),
    ]
    for name, mutate in cases:
        expect_semantic_rejection(
            validator,
            helper,
            eligibility_validator,
            objectives_writer,
            drill_writer,
            baseline,
            name,
            mutate,
        )

    authority_cases = (
        ("PREFLIGHT", ELIGIBILITY),
        ("ELIGIBILITY", PREFLIGHT),
        ("OBJECTIVES", DRILL_REQUESTS),
        ("DRILL_REQUESTS", OBJECTIVES),
        ("HELPER", SUBSTITUTE_SCRIPT),
        ("ELIGIBILITY_VALIDATOR", SUBSTITUTE_SCRIPT),
        ("OBJECTIVES_WRITER", SUBSTITUTE_SCRIPT),
        ("DRILL_WRITER", SUBSTITUTE_SCRIPT),
        ("DRILL_VALIDATOR", SUBSTITUTE_SCRIPT),
        ("VALIDATOR", SUBSTITUTE_SCRIPT),
    )
    for field, substitute in authority_cases:
        expect_authority_rejection(validator, field, substitute)

    helper_cases = (
        ("require", lambda condition, message: None),
        ("require_exact_repo_file", lambda path, expected, field: path),
        ("enforce_runtime_authorities", lambda: None),
        ("display_path", lambda path: str(path)),
        ("load", lambda path: {}),
        ("load_module", lambda path, expected, name, field: object()),
        ("validate_state", lambda *args, **kwargs: 0),
        ("enforce_execution_identity", lambda: None),
    )
    for field, replacement in helper_cases:
        expect_helper_rejection(validator, field, replacement)

    print("Memory OS restore preflight generation-eligibility consistency negative PASS")
    print(f"semantic authority corruption cases: {len(cases)}")
    print(f"direct data/executable substitution cases: {len(authority_cases)}")
    print(f"direct execution helper substitution cases: {len(helper_cases)}")
    print("canonical semantic eligibility validator substitution accepted: false")
    print("canonical drill request full admission validator substitution accepted: false")
    print("semantic fixtures bypass runtime authority: false")
    print("semantic fixtures use pure state validation only: true")
    print("canonical authority mutated: false")
    print("production evidence created: false")
    print("production decision changed: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RESTORE PREFLIGHT GENERATION ELIGIBILITY CONSISTENCY NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
