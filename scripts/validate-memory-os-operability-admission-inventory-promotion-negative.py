#!/usr/bin/env python3
"""Prove inventory/status cannot manufacture production-promotion authority.

The canonical inventory and production status are never mutated. This harness
uses repo-local temporary copies and the real validators to prove that candidate
authority, semantic-generation count drift, sustained-soak review authority, or
canonical status wording cannot silently create production authority.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability-admission-inventory.py"
STATUS_VALIDATOR = ROOT / "scripts/validate-memory-os-operability-status-hygiene.py"
INVENTORY = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
STATUS = ROOT / "contracts/operations/production-operability-status.json"
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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def area_row(value: dict[str, Any], area_id: str) -> dict[str, Any]:
    rows = value.get("areas")
    require(isinstance(rows, list), "inventory areas missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == area_id]
    require(len(matches) == 1, f"{area_id} inventory row must be unique")
    return matches[0]


def backup_row(value: dict[str, Any]) -> dict[str, Any]:
    return area_row(value, "OPS-P0-007")


def soak_row(value: dict[str, Any]) -> dict[str, Any]:
    return area_row(value, "OPS-P0-006")


def status_row(value: dict[str, Any]) -> dict[str, Any]:
    rows = value.get("areas")
    require(isinstance(rows, list), "status areas missing")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == "OPS-P0-007"]
    require(len(matches) == 1, "OPS-P0-007 status row must be unique")
    return matches[0]


def expect_inventory_rejected(
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
    raise Fail(f"inventory mutation unexpectedly accepted: {name}")


def expect_status_rejected(
    validator: Any,
    canonical_status: dict[str, Any],
    canonical_inventory: dict[str, Any],
    name: str,
    mutate_status: Callable[[dict[str, Any]], None] | None = None,
    mutate_inventory: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    bad_status = copy.deepcopy(canonical_status)
    bad_inventory = copy.deepcopy(canonical_inventory)
    if mutate_status is not None:
        mutate_status(bad_status)
    if mutate_inventory is not None:
        mutate_inventory(bad_inventory)
    with tempfile.TemporaryDirectory(prefix=".memory-os-status-hygiene-negative-", dir=TEMP_PARENT) as tmp:
        tmp_path = Path(tmp)
        status_path = tmp_path / "status.json"
        inventory_path = tmp_path / "inventory.json"
        write_json(status_path, bad_status)
        write_json(inventory_path, bad_inventory)
        original_status = validator.STATUS
        original_inventory = validator.INVENTORY
        validator.STATUS = status_path
        validator.INVENTORY = inventory_path
        try:
            validator.main()
        except validator.Fail:
            print(f"PASS reject: {name}")
            return
        finally:
            validator.STATUS = original_status
            validator.INVENTORY = original_inventory
    raise Fail(f"status/inventory mutation unexpectedly accepted: {name}")


def remove_registered_inventory_authority(value: dict[str, Any]) -> None:
    row = status_row(value)
    evidence = row.get("existingEvidence")
    require(isinstance(evidence, list), "OPS-P0-007 status existingEvidence missing")
    row["existingEvidence"] = [
        item for item in evidence
        if not (isinstance(item, str) and "registered generation inventory alone" in item and "restore-planning authority" in item)
    ]


def remove_human_promotion_separation(value: dict[str, Any]) -> None:
    row = status_row(value)
    evidence = row.get("existingEvidence")
    require(isinstance(evidence, list), "OPS-P0-007 status existingEvidence missing")
    row["existingEvidence"] = [
        item for item in evidence
        if not (isinstance(item, str) and "human production-promotion review" in item and "separate non-automatic decision" in item)
    ]


def main() -> int:
    require(
        INVENTORY_VALIDATOR.is_file()
        and STATUS_VALIDATOR.is_file()
        and INVENTORY.is_file()
        and STATUS.is_file()
        and TEMP_PARENT.is_dir(),
        "operability promotion negative foundation missing",
    )
    canonical_inventory = load(INVENTORY)
    canonical_status = load(STATUS)
    row = backup_row(canonical_inventory)
    soak = soak_row(canonical_inventory)
    require(canonical_inventory.get("productionDecision") == "NO_GO", "canonical inventory productionDecision drift")
    require(canonical_inventory.get("humanProductionPromotionReviewCompleted") is False, "canonical top-level human promotion review drift")
    require(canonical_inventory.get("humanProductionPromotionAuthorized") is False, "canonical top-level human promotion authorization drift")
    require(row.get("humanProductionPromotionReviewCompleted") is False, "canonical OPS-P0-007 human promotion review drift")
    require(row.get("humanProductionPromotionAuthorized") is False, "canonical OPS-P0-007 human promotion authorization drift")
    require(canonical_inventory.get("approvedLeakStabilityCriteriaCount") == 0, "canonical top-level sustained-soak approved criteria drift")
    require(canonical_inventory.get("passingIndependentSustainedSoakReviewCount") == 0, "canonical top-level sustained-soak independent review drift")
    require(canonical_inventory.get("sustainedSoakLeakProof") is False, "canonical top-level sustained-soak leak proof drift")
    require(soak.get("approvedLeakStabilityCriteriaCount") == 0, "canonical OPS-P0-006 approved criteria drift")
    require(soak.get("passingIndependentReviewCount") == 0, "canonical OPS-P0-006 independent review drift")
    require(soak.get("leakProof") is False, "canonical OPS-P0-006 leak proof drift")

    inventory_validator = load_module(INVENTORY_VALIDATOR, "memory_os_operability_inventory_promotion_negative")
    status_validator = load_module(STATUS_VALIDATOR, "memory_os_operability_status_hygiene_negative")

    inventory_validator.main()
    status_validator.main()
    print("PASS baseline: canonical inventory/status preserve operability authority separation")

    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "top-level sustained-soak approved criteria manufactured",
        lambda value: value.__setitem__("approvedLeakStabilityCriteriaCount", 1),
    )
    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "top-level sustained-soak independent review manufactured",
        lambda value: value.__setitem__("passingIndependentSustainedSoakReviewCount", 1),
    )
    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "top-level sustained-soak leak proof manufactured",
        lambda value: value.__setitem__("sustainedSoakLeakProof", True),
    )
    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "OPS-P0-006 approved criteria manufactured",
        lambda value: soak_row(value).__setitem__("approvedLeakStabilityCriteriaCount", 1),
    )
    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "OPS-P0-006 independent review manufactured",
        lambda value: soak_row(value).__setitem__("passingIndependentReviewCount", 1),
    )
    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "OPS-P0-006 leak proof manufactured",
        lambda value: soak_row(value).__setitem__("leakProof", True),
    )
    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "top-level human promotion review manufactured",
        lambda value: value.__setitem__("humanProductionPromotionReviewCompleted", True),
    )
    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "top-level human promotion authorization manufactured",
        lambda value: value.__setitem__("humanProductionPromotionAuthorized", True),
    )
    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "OPS-P0-007 human promotion review manufactured",
        lambda value: backup_row(value).__setitem__("humanProductionPromotionReviewCompleted", True),
    )
    expect_inventory_rejected(
        inventory_validator,
        canonical_inventory,
        "OPS-P0-007 human promotion authorization manufactured",
        lambda value: backup_row(value).__setitem__("humanProductionPromotionAuthorized", True),
    )

    expect_status_rejected(
        status_validator,
        canonical_status,
        canonical_inventory,
        "status layer rejects top-level production promotion manufacture",
        mutate_inventory=lambda value: value.__setitem__("humanProductionPromotionAuthorized", True),
    )
    expect_status_rejected(
        status_validator,
        canonical_status,
        canonical_inventory,
        "status layer rejects OPS-P0-007 human promotion review manufacture",
        mutate_inventory=lambda value: backup_row(value).__setitem__("humanProductionPromotionReviewCompleted", True),
    )
    expect_status_rejected(
        status_validator,
        canonical_status,
        canonical_inventory,
        "semantic preflight eligibility cannot exceed registered generation inventory",
        mutate_inventory=lambda value: backup_row(value)["dependencyCounts"].__setitem__(
            "preflightEligibleEnvironmentGenerations",
            backup_row(value)["dependencyCounts"]["environmentGenerations"] + 1,
        ),
    )
    expect_status_rejected(
        status_validator,
        canonical_status,
        canonical_inventory,
        "canonical status cannot imply registered inventory creates restore authority",
        mutate_status=remove_registered_inventory_authority,
    )
    expect_status_rejected(
        status_validator,
        canonical_status,
        canonical_inventory,
        "canonical status cannot collapse candidate review into human promotion",
        mutate_status=remove_human_promotion_separation,
    )

    print("Memory OS operability inventory/status production-promotion negative suite PASS")
    print("local sustained-soak evidence can manufacture approved criteria: false")
    print("local sustained-soak evidence can manufacture independent review: false")
    print("local sustained-soak evidence can manufacture leak proof: false")
    print("registered inventory alone creates restore-planning authority: false")
    print("candidate authority can manufacture human promotion review: false")
    print("candidate authority can manufacture human promotion authorization: false")
    print("status/inventory promotion semantics diverge silently: false")
    print("unexpected exception accepted as a valid rejection: false")
    print("canonical inventory/status mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"OPERABILITY INVENTORY/STATUS PROMOTION NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
