#!/usr/bin/env python3
"""Reject malformed synthetic chaos drill metadata without changing evidence."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-chaos-failure-drills-v2.py"
FIXTURE = ROOT / "docs/fixtures/memory-os-operability/chaos-failure-drill-results.v2.sample.json"


def main() -> int:
    spec = importlib.util.spec_from_file_location("chaos_v2_metadata_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical chaos v2 validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads(FIXTURE.read_text(encoding="utf-8"))
    module.validate_result(original, None)
    mutations = (
        ("nonzero exit", "exitCode", 1),
        ("boolean exit", "exitCode", False),
        ("string exit", "exitCode", "0"),
        ("negative duration", "durationSeconds", -1),
        ("boolean duration", "durationSeconds", False),
        ("string duration", "durationSeconds", "1"),
        ("NaN duration", "durationSeconds", float("nan")),
        ("infinite duration", "durationSeconds", float("inf")),
    )
    for name, field, value in mutations:
        candidate = copy.deepcopy(original)
        item = next(s for s in candidate["scenarios"] if s["scenarioId"] == "api-graceful-interruption-drain")
        item[field] = value
        try:
            module.validate_result(candidate, None)
        except module.ValidationFailure:
            continue
        raise RuntimeError(f"canonical chaos v2 validator accepted {name}")
    assertion_mutations = (
        ("false zero", "durablePreviewRowsDuringOutage", False),
        ("true one", "durablePreviewRowsAfterRecovery", True),
        ("float one", "rejectedRecordsAfterRecovery", 1.0),
        ("string two", "acceptedRecordsAfterRecovery", "2"),
        ("negative count", "spoolEntriesDuringOutage", -1),
    )
    for name, field, value in assertion_mutations:
        candidate = copy.deepcopy(original)
        item = next(s for s in candidate["scenarios"] if s["scenarioId"] == "object-store-outage-and-recovery")
        item["assertions"][field] = value
        try:
            module.validate_result(candidate, None)
        except module.ValidationFailure:
            continue
        raise RuntimeError(f"canonical chaos v2 validator accepted {name}")
    if (ROOT / "contracts/operations/production-operability-status.json").is_file():
        status = json.loads((ROOT / "contracts/operations/production-operability-status.json").read_text(encoding="utf-8"))
        if status.get("productionDecision") != "NO_GO":
            raise RuntimeError("production authority drift")
    print(f"PASS: chaos v2 metadata negatives ({len(mutations) + len(assertion_mutations)} mutations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
