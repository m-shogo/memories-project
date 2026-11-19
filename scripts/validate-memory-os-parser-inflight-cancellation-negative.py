#!/usr/bin/env python3
"""Negative mutations for exact-source parser in-flight cancellation result evidence."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-parser-inflight-cancellation.py"
RESULT = ROOT / "docs/fixtures/memory-os-operability/parser-inflight-cancellation-results.sample.v1.json"


def main() -> int:
    spec = importlib.util.spec_from_file_location("parser_inflight_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical parser in-flight validator unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = json.loads(RESULT.read_text(encoding="utf-8"))
    module.validate_result(original, original["commitSha"])

    mutations = (
        ("boolean false exit", ("exitCode",), False),
        ("boolean true exit", ("exitCode",), True),
        ("string exit", ("exitCode",), "0"),
        ("nonzero exit", ("exitCode",), 1),
        ("boolean latency", ("assertions", "cancellationLatencyMilliseconds"), False),
        ("negative latency", ("assertions", "cancellationLatencyMilliseconds"), -1),
        ("latency at limit", ("assertions", "cancellationLatencyMilliseconds"), 1000),
        ("NaN latency", ("assertions", "cancellationLatencyMilliseconds"), float("nan")),
        ("infinite latency", ("assertions", "cancellationLatencyMilliseconds"), float("inf")),
        ("string latency", ("assertions", "cancellationLatencyMilliseconds"), "0"),
        ("boolean wall clock", ("assertions", "configuredWallClockMilliseconds"), True),
        ("float wall clock", ("assertions", "configuredWallClockMilliseconds"), 10000.0),
        ("string wall clock", ("assertions", "configuredWallClockMilliseconds"), "10000"),
    )
    for label, path, value in mutations:
        invalid = copy.deepcopy(original)
        target = invalid
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        try:
            module.validate_result(invalid, original["commitSha"])
        except module.ValidationFailure:
            continue
        raise AssertionError(f"canonical validator accepted {label}")
    print(f"Parser in-flight cancellation negative validation PASS ({len(mutations)} mutations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
