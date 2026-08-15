#!/usr/bin/env python3
"""Negative suite for restore preflight / semantic-generation consistency authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-preflight-generation-eligibility-consistency.py"
HELPER = ROOT / "scripts/memory_os_environment_generation_eligibility.py"
PREFLIGHT = ROOT / "contracts/operations/backup-restore-drill-preflight-contract.v1.json"
ELIGIBILITY = ROOT / "contracts/operations/production-equivalent-environment-eligibility-contract.v1.json"
OBJECTIVES = ROOT / "contracts/operations/recovery-objectives-registry.v1.json"
DRILL_REQUESTS = ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json"


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


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def expect_rejection(
    validator,
    baseline: dict[str, dict[str, Any]],
    name: str,
    mutate: Callable[[dict[str, dict[str, Any]]], None],
) -> None:
    with tempfile.TemporaryDirectory(prefix="memory-os-preflight-consistency-negative-") as temp_dir:
        temp = Path(temp_dir)
        state = copy.deepcopy(baseline)
        mutate(state)

        paths = {
            "preflight": temp / "preflight.json",
            "eligibility": temp / "eligibility.json",
            "objectives": temp / "objectives.json",
            "drill": temp / "drill.json",
        }
        for key, path in paths.items():
            write_json(path, state[key])

        original = (
            validator.PREFLIGHT,
            validator.ELIGIBILITY,
            validator.OBJECTIVES,
            validator.DRILL_REQUESTS,
        )
        validator.PREFLIGHT = paths["preflight"]
        validator.ELIGIBILITY = paths["eligibility"]
        validator.OBJECTIVES = paths["objectives"]
        validator.DRILL_REQUESTS = paths["drill"]
        try:
            try:
                validator.main()
            except validator.Fail:
                pass
            else:
                raise Fail(f"negative case unexpectedly accepted: {name}")
        finally:
            (
                validator.PREFLIGHT,
                validator.ELIGIBILITY,
                validator.OBJECTIVES,
                validator.DRILL_REQUESTS,
            ) = original


def main() -> int:
    validator = load_module(VALIDATOR, "memory_os_preflight_consistency_negative_target")
    helper = load_module(HELPER, "memory_os_preflight_consistency_negative_helper")
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
        (
            "boolean preflight pair count",
            lambda state: state["preflight"]["currentState"].__setitem__("eligibleDirectedSourceTargetPairCount", True),
        ),
        (
            "preflight pair count exceeds strict semantic authority",
            lambda state: state["preflight"]["currentState"].__setitem__("eligibleDirectedSourceTargetPairCount", strict_pair_count + 1),
        ),
        (
            "preflight production readiness promotion",
            lambda state: state["preflight"]["currentState"].__setitem__("productionReady", True),
        ),
        (
            "preflight production decision promotion",
            lambda state: state["preflight"]["currentState"].__setitem__("productionDecision", "GO"),
        ),
        (
            "eligibility production decision promotion",
            lambda state: state["eligibility"]["currentBoundary"].__setitem__("productionDecision", "GO"),
        ),
        (
            "boolean approved objective count",
            lambda state: state["objectives"].__setitem__("approvedObjectiveCount", True),
        ),
        (
            "boolean current executable request count",
            lambda state: state["drill"].__setitem__("currentExecutableRequestCount", True),
        ),
    ]

    for name, mutate in cases:
        expect_rejection(validator, baseline, name, mutate)

    print("Memory OS restore preflight generation-eligibility consistency negative PASS")
    print(f"negative cases: {len(cases)}")
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
