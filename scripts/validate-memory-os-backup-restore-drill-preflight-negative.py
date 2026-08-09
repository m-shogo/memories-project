#!/usr/bin/env python3
"""Prove restore drill preflight rejects stale or unexpected authority-state fields."""

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
TEMP_PARENT = ROOT / "contracts/operations"


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


def main() -> int:
    require(VALIDATOR.is_file() and CONTRACT.is_file() and TEMP_PARENT.is_dir(), "preflight negative foundation missing")
    validator = load_validator()
    canonical = load(CONTRACT)
    current_state = canonical.get("currentState")
    readiness = canonical.get("readiness")
    require(isinstance(current_state, dict) and set(current_state) == validator.STATE_FIELDS, "canonical preflight currentState is not exact")
    require(isinstance(readiness, dict) and set(readiness) == validator.READINESS_FIELDS, "canonical preflight readiness is not exact")
    print("PASS baseline: canonical preflight authority field sets are exact")

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
        "unexpected future readiness field",
        lambda value: value["readiness"].__setitem__("unexpectedReadinessAlias", False),
    )

    print("Memory OS restore drill preflight negative authority-shape suite PASS")
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
