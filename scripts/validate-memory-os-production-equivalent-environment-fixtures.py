#!/usr/bin/env python3
"""Exercise the production-equivalent environment schema with positive and negative fixtures."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "contracts/operations/production-equivalent-environment-record.v1.schema.json"
VALID = ROOT / "docs/fixtures/memory-os-operability/production-equivalent-environment-record.planned.valid.v1.json"
INVALID_EQUIVALENCE = ROOT / "docs/fixtures/memory-os-operability/production-equivalent-environment-record.unsafe-equivalence.invalid.v1.json"
INVALID_DELTA = ROOT / "docs/fixtures/memory-os-operability/production-equivalent-environment-record.unreviewed-material-delta.invalid.v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def expect_invalid(validator: jsonschema.Draft202012Validator, path: Path, label: str) -> None:
    errors = list(validator.iter_errors(load(path)))
    if not errors:
        raise SystemExit(f"unsafe fixture unexpectedly accepted: {label}")
    print(f"{label}: rejected as required ({len(errors)} schema errors)")


def main() -> int:
    schema = load(SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)

    valid = load(VALID)
    errors = list(validator.iter_errors(valid))
    if errors:
        for error in errors[:10]:
            print(f"VALID FIXTURE ERROR: {error.message}", file=sys.stderr)
        raise SystemExit("safe PLANNED environment fixture was rejected")
    boundary = valid.get("evidenceBoundary", {})
    if boundary.get("productionEquivalentDependencies") is not False or boundary.get("productionReady") is not False:
        raise SystemExit("safe fixture must remain non-equivalent and non-ready")
    print("safe PLANNED fixture: accepted")

    expect_invalid(validator, INVALID_EQUIVALENCE, "unsafe equivalence promotion")
    expect_invalid(validator, INVALID_DELTA, "unreviewed accepted MATERIAL delta")

    print("Memory OS production-equivalent environment fixture validation PASS")
    print("production-equivalent promotion without evidence: rejected")
    print("accepted MATERIAL delta without independent review: rejected")
    print("production evidence: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
