#!/usr/bin/env python3
"""Prove OPS-P0-007 status hygiene fails closed on authority mutations."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-operability-status-hygiene.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
INVENTORY = ROOT / "contracts/operations/operability-admission-inventory.v1.json"


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
    spec = importlib.util.spec_from_file_location("memory_os_operability_status_hygiene_negative_target", VALIDATOR)
    require(spec is not None and spec.loader is not None, f"cannot load {VALIDATOR}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except Exception:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def area(value: dict[str, Any], area_id: str) -> dict[str, Any]:
    areas = value.get("areas")
    require(isinstance(areas, list), "areas missing")
    match = next((item for item in areas if isinstance(item, dict) and item.get("id") == area_id), None)
    require(isinstance(match, dict), f"{area_id} missing")
    return match


def main() -> int:
    for path in (VALIDATOR, STATUS, INVENTORY):
        require(path.is_file(), f"negative foundation missing: {path}")

    canonical_status = load(STATUS)
    canonical_inventory = load(INVENTORY)
    validator = load_validator()

    with tempfile.TemporaryDirectory(prefix="memory-os-operability-status-hygiene-negative-") as tmp:
        tmp_path = Path(tmp)
        status_path = tmp_path / "status.json"
        inventory_path = tmp_path / "inventory.json"

        def validate(status: dict[str, Any], inventory: dict[str, Any]) -> None:
            write_json(status_path, status)
            write_json(inventory_path, inventory)
            validator.STATUS = status_path
            validator.INVENTORY = inventory_path
            validator.main()

        validate(copy.deepcopy(canonical_status), copy.deepcopy(canonical_inventory))
        print("PASS baseline: canonical status and inventory preserve backup/restore authority separation")

        promoted = copy.deepcopy(canonical_inventory)
        promoted["humanProductionPromotionAuthorized"] = True
        expect_rejected(
            "top-level inventory cannot manufacture production promotion",
            lambda: validate(copy.deepcopy(canonical_status), promoted),
        )

        reviewed = copy.deepcopy(canonical_inventory)
        area(reviewed, "OPS-P0-007")["humanProductionPromotionReviewCompleted"] = True
        expect_rejected(
            "OPS-P0-007 inventory cannot manufacture human promotion review",
            lambda: validate(copy.deepcopy(canonical_status), reviewed),
        )

        semantic_overflow = copy.deepcopy(canonical_inventory)
        counts = area(semantic_overflow, "OPS-P0-007")["dependencyCounts"]
        counts["preflightEligibleEnvironmentGenerations"] = counts["environmentGenerations"] + 1
        expect_rejected(
            "semantic preflight eligibility cannot exceed registered generation inventory",
            lambda: validate(copy.deepcopy(canonical_status), semantic_overflow),
        )

        authority_text_removed = copy.deepcopy(canonical_status)
        evidence = area(authority_text_removed, "OPS-P0-007")["existingEvidence"]
        area(authority_text_removed, "OPS-P0-007")["existingEvidence"] = [
            item for item in evidence
            if not (isinstance(item, str) and "registered generation inventory alone" in item and "restore-planning authority" in item)
        ]
        expect_rejected(
            "canonical status cannot imply registered generation inventory creates restore authority",
            lambda: validate(authority_text_removed, copy.deepcopy(canonical_inventory)),
        )

        promotion_text_removed = copy.deepcopy(canonical_status)
        evidence = area(promotion_text_removed, "OPS-P0-007")["existingEvidence"]
        area(promotion_text_removed, "OPS-P0-007")["existingEvidence"] = [
            item for item in evidence
            if not (isinstance(item, str) and "human production-promotion review" in item and "separate non-automatic decision" in item)
        ]
        expect_rejected(
            "canonical status cannot collapse candidate review into human production promotion",
            lambda: validate(promotion_text_removed, copy.deepcopy(canonical_inventory)),
        )

    print("Memory OS operability status hygiene negative suite PASS")
    print("registered inventory alone creates restore-planning authority: false")
    print("candidate evidence creates human production promotion: false")
    print("canonical files mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY STATUS HYGIENE NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
