#!/usr/bin/env python3
"""Prove operability inventory cannot manufacture human production-promotion authority.

The canonical inventory and production status are never mutated. This harness
loads the canonical inventory, writes isolated mutated copies under the
repository, points the real inventory validator at each copy, and requires every
promotion-authority mutation to fail closed. It also composes the canonical
status-hygiene mutation suite so inventory and status cannot diverge on the same
authority boundary.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-operability-admission-inventory.py"
STATUS_HYGIENE_NEGATIVE = ROOT / "scripts/validate-memory-os-operability-status-hygiene-negative.py"
INVENTORY = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
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


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_operability_inventory_promotion_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load operability inventory validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def backup_row(value: dict[str, Any]) -> dict[str, Any]:
    rows = value.get("areas")
    require(isinstance(rows, list), "inventory areas missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == "OPS-P0-007"]
    require(len(matches) == 1, "OPS-P0-007 row must be unique")
    return matches[0]


def expect_rejected(
    validator: Any,
    canonical: dict[str, Any],
    name: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    bad = copy.deepcopy(canonical)
    mutate(bad)
    with tempfile.TemporaryDirectory(prefix=".memory-os-inventory-promotion-negative-", dir=TEMP_PARENT) as tmp:
        path = Path(tmp) / "inventory.json"
        write_json(path, bad)
        original = validator.INVENTORY
        validator.INVENTORY = path
        try:
            validator.main()
        except validator.Fail:
            print(f"PASS reject: {name}")
            return
        finally:
            validator.INVENTORY = original
    raise Fail(f"promotion mutation unexpectedly accepted: {name}")


def main() -> int:
    require(
        VALIDATOR.is_file() and STATUS_HYGIENE_NEGATIVE.is_file() and INVENTORY.is_file() and TEMP_PARENT.is_dir(),
        "inventory promotion negative foundation missing",
    )
    canonical = load(INVENTORY)
    row = backup_row(canonical)
    require(canonical.get("productionDecision") == "NO_GO", "canonical inventory productionDecision drift")
    require(canonical.get("humanProductionPromotionReviewCompleted") is False, "canonical top-level human promotion review drift")
    require(canonical.get("humanProductionPromotionAuthorized") is False, "canonical top-level human promotion authorization drift")
    require(row.get("humanProductionPromotionReviewCompleted") is False, "canonical OPS-P0-007 human promotion review drift")
    require(row.get("humanProductionPromotionAuthorized") is False, "canonical OPS-P0-007 human promotion authorization drift")

    validator = load_validator()

    expect_rejected(
        validator,
        canonical,
        "top-level human promotion review manufactured",
        lambda value: value.__setitem__("humanProductionPromotionReviewCompleted", True),
    )
    expect_rejected(
        validator,
        canonical,
        "top-level human promotion authorization manufactured",
        lambda value: value.__setitem__("humanProductionPromotionAuthorized", True),
    )
    expect_rejected(
        validator,
        canonical,
        "OPS-P0-007 human promotion review manufactured",
        lambda value: backup_row(value).__setitem__("humanProductionPromotionReviewCompleted", True),
    )
    expect_rejected(
        validator,
        canonical,
        "OPS-P0-007 human promotion authorization manufactured",
        lambda value: backup_row(value).__setitem__("humanProductionPromotionAuthorized", True),
    )

    completed = subprocess.run(
        ["python", str(STATUS_HYGIENE_NEGATIVE)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    print(completed.stdout, end="")
    require(completed.returncode == 0, "operability status hygiene negative suite failed")

    print("Memory OS operability inventory production-promotion negative suite PASS")
    print("candidate authority can manufacture human promotion review: false")
    print("candidate authority can manufacture human promotion authorization: false")
    print("status/inventory promotion semantics diverge silently: false")
    print("canonical inventory mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY PROMOTION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
