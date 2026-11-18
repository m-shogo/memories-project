#!/usr/bin/env python3
"""Isolated negative cases for parser restart matrix result metadata."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-parser-restart-matrix.py"
RESULT = ROOT / "docs/fixtures/memory-os-operability/parser-restart-matrix-results.sample.v1.json"


def main() -> int:
    spec = importlib.util.spec_from_file_location("parser_restart_matrix_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical parser restart validator unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads(RESULT.read_text(encoding="utf-8"))
    module.validate_result(original, original["commitSha"])

    mutations = (
        ("nonzero exit", "exitCode", 1),
        ("boolean exit", "exitCode", False),
        ("string exit", "exitCode", "0"),
        ("negative duration", "durationSeconds", -1),
        ("boolean duration", "durationSeconds", True),
        ("string duration", "durationSeconds", "1"),
        ("NaN duration", "durationSeconds", float("nan")),
        ("infinite duration", "durationSeconds", float("inf")),
    )
    for label, field, value in mutations:
        invalid = copy.deepcopy(original)
        invalid["failureClasses"][0][field] = value
        try:
            module.validate_result(invalid, original["commitSha"])
        except module.ValidationFailure:
            continue
        raise AssertionError(f"canonical validator accepted {label}")
    print(f"Parser restart matrix negative validation PASS ({len(mutations)} mutations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
