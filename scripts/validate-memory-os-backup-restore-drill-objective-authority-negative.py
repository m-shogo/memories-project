#!/usr/bin/env python3
"""Pin drill-request delegation to the canonical recovery-objective registry authority."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/request-memory-os-backup-restore-drill.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer():
    spec = importlib.util.spec_from_file_location("memory_os_restore_drill_objective_authority_negative", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load drill request writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def expect_rejected(name: str, action: Callable[[], Any], expected: type[Exception]) -> None:
    try:
        action()
    except expected:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def main() -> int:
    writer = load_writer()

    class SharedObjectiveAuthority:
        class Fail(RuntimeError):
            pass

        calls = 0

        @classmethod
        def validate_registry_for_append(cls, registry: dict[str, Any]) -> list[dict[str, Any]]:
            cls.calls += 1
            if registry.get("schemaVersion") != "memory-os-recovery-objectives-registry.v1":
                raise cls.Fail("registry schema drift")
            if registry.get("appendOnly") is not True:
                raise cls.Fail("registry must remain append-only")
            if registry.get("productionEvidence") is not False or registry.get("productionReady") is not False:
                raise cls.Fail("registry production boundary drift")
            rows = registry.get("records")
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                raise cls.Fail("records invalid")
            count = registry.get("approvedObjectiveCount")
            if not isinstance(count, int) or isinstance(count, bool) or count != len(rows):
                raise cls.Fail("approvedObjectiveCount drift")
            previous = None
            ids: set[str] = set()
            for row in rows:
                objective_id = row.get("objectiveId")
                if not isinstance(objective_id, str) or not objective_id or objective_id in ids:
                    raise cls.Fail("objective identity drift")
                ids.add(objective_id)
                if row.get("supersedesObjectiveId") != previous:
                    raise cls.Fail("objective supersession chain drift")
                previous = objective_id
            if registry.get("currentObjectiveId") != previous:
                raise cls.Fail("currentObjectiveId drift")
            return rows

    with tempfile.TemporaryDirectory(prefix="memory-os-drill-objective-authority-negative-") as tmp:
        tmp_path = Path(tmp)
        registry_path = tmp_path / "objectives.json"
        valid = {
            "schemaVersion": "memory-os-recovery-objectives-registry.v1",
            "appendOnly": True,
            "approvedObjectiveCount": 2,
            "currentObjectiveId": "ro_current",
            "records": [
                {
                    "objectiveId": "ro_previous",
                    "supersedesObjectiveId": None,
                    "approvedAt": "2026-08-07T23:20:00Z",
                },
                {
                    "objectiveId": "ro_current",
                    "supersedesObjectiveId": "ro_previous",
                    "approvedAt": "2026-08-07T23:30:00Z",
                },
            ],
            "productionEvidence": False,
            "productionReady": False,
        }
        write_json(registry_path, valid)

        writer.ROOT = tmp_path
        writer.CANONICAL_ROOT = tmp_path
        writer.OBJECTIVES_REGISTRY = registry_path
        writer.CANONICAL_OBJECTIVES_REGISTRY = registry_path
        writer.load_objectives_writer = lambda: SharedObjectiveAuthority

        current = writer.current_objective()
        require(current.get("objectiveId") == "ro_current", "valid shared objective authority did not resolve current objective")
        require(SharedObjectiveAuthority.calls == 1, "drill writer did not delegate current objective validation")
        print("PASS accept: drill writer delegates current objective registry validation")

        corruptions = {
            "objective registry schema drift": lambda value: value.__setitem__("schemaVersion", "legacy-objectives"),
            "objective registry appendOnly false": lambda value: value.__setitem__("appendOnly", False),
            "objective registry boolean count": lambda value: value.__setitem__("approvedObjectiveCount", True),
            "objective registry current pointer drift": lambda value: value.__setitem__("currentObjectiveId", "ro_previous"),
            "objective registry supersession drift": lambda value: value["records"][1].__setitem__("supersedesObjectiveId", None),
            "objective registry productionEvidence promotion": lambda value: value.__setitem__("productionEvidence", True),
            "objective registry productionReady promotion": lambda value: value.__setitem__("productionReady", True),
        }
        for name, mutate in corruptions.items():
            candidate = json.loads(json.dumps(valid))
            mutate(candidate)
            write_json(registry_path, candidate)
            expect_rejected(name, writer.current_objective, writer.Fail)

        write_json(registry_path, valid)
        historical = writer.objective_by_id("ro_previous")
        require(historical.get("objectiveId") == "ro_previous", "historical objective lookup failed after shared registry validation")
        require(SharedObjectiveAuthority.calls >= 9, "historical objective lookup bypassed shared objective authority")
        print("PASS accept: historical objective lookup remains audit-only but registry-valid")

    print("PASS: drill request objective authority delegation negatives")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
