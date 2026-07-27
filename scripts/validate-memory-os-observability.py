#!/usr/bin/env python3
"""Fail-closed validator for the Memory OS observability event contract.

It checks four things and exits non-zero on any of them:

  1. The contract itself is internally consistent: required/optional fields are
     disjoint, enums are non-empty and unique, no stable event code is
     duplicated, and no forbidden field name collides with an allowed one.
  2. The Go implementation and the contract have not drifted. The event codes,
     severities, outcomes, failure classes and components declared in
     internal/obslog are extracted from source and compared to the contract; a
     code in one but not the other fails.
  3. The valid fixture only uses declared fields, enums and codes; the negative
     fixture's every case is actually rejected by the same rules (a negative
     case that would pass is a hole in the guarantee).
  4. The operability status keeps OPS-P0-003 honest: it may not be READY while
     retention and alert routing are unconfigured in the contract, and its
     evidenceRefs must exist.

The forbidden-field check is both an exact-name list and a substring list, so a
new field like refreshTokenDigest or userEmail is rejected even though it was
never named explicitly.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "contracts/operations/observability-event-contract.v1.json"
VALID_FIXTURE = REPO / "docs/fixtures/memory-os-operability/observability-events.valid.v1.json"
NEGATIVE_FIXTURE = REPO / "docs/fixtures/memory-os-operability/observability-events.negative.v1.json"
STATUS = REPO / "contracts/operations/production-operability-status.json"
OBSLOG_CODES = REPO / "services/import-api/internal/obslog/codes.go"
OBSLOG_EVENT = REPO / "services/import-api/internal/obslog/event.go"


class Fail(RuntimeError):
    pass


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path}: {exc}") from exc


def go_string_consts(source: str, go_type: str) -> set[str]:
    """Extract the string literal values of consts typed as go_type."""
    values: set[str] = set()
    for match in re.finditer(rf'{go_type}\s*=\s*"([^"]+)"', source):
        values.add(match.group(1))
    return values


def check_event_fields(event: dict, contract: dict) -> list[str]:
    """Return a list of reasons the event violates the contract (empty = clean)."""
    reasons: list[str] = []
    required = set(contract["requiredFields"])
    optional = set(contract["optionalFields"])
    allowed = required | optional
    forbidden_names = {name.lower() for name in contract["forbiddenFieldNames"]}
    forbidden_subs = [sub.lower() for sub in contract["forbiddenFieldSubstrings"]]
    bounds = contract["boundedStringFields"]

    for key in event:
        lowered = key.lower()
        if lowered in forbidden_names:
            reasons.append(f"forbidden field name: {key}")
            continue
        if any(sub in lowered for sub in forbidden_subs):
            reasons.append(f"forbidden field substring: {key}")
            continue
        if key not in allowed:
            reasons.append(f"undeclared field: {key}")

    for field in required:
        if field not in event:
            reasons.append(f"missing required field: {field}")

    if event.get("schemaVersion") != contract["schemaVersion"]:
        reasons.append("wrong schemaVersion")
    if event.get("severity") not in contract["severity"]:
        reasons.append("invalid severity")
    if event.get("outcome") not in contract["outcome"]:
        reasons.append("invalid outcome")
    if "failureClass" in event and event["failureClass"] not in contract["failureClass"]:
        reasons.append("invalid failureClass")
    if event.get("component") not in contract["component"]:
        reasons.append("invalid component")
    if event.get("eventCode") not in contract["eventCodes"]:
        reasons.append("unknown eventCode")
    for field, limit in bounds.items():
        value = event.get(field)
        if isinstance(value, str) and len(value) > limit:
            reasons.append(f"field over bound: {field}")
    return reasons


def main() -> int:
    try:
        contract = load(CONTRACT)

        # 1. Contract internal consistency.
        required = contract["requiredFields"]
        optional = contract["optionalFields"]
        if set(required) & set(optional):
            raise Fail("required and optional fields overlap")
        for name, values in ("severity", contract["severity"]), ("outcome", contract["outcome"]), \
                ("component", contract["component"]), ("failureClass", contract["failureClass"]), \
                ("eventCodes", contract["eventCodes"]):
            if len(values) != len(set(values)):
                raise Fail(f"{name} contains duplicates")
            if not values:
                raise Fail(f"{name} is empty")
        if set(contract["forbiddenFieldNames"]) & (set(required) | set(optional)):
            raise Fail("a forbidden field name is also an allowed field")

        # 2. Go implementation / contract drift.
        codes_src = OBSLOG_CODES.read_text(encoding="utf-8")
        event_src = OBSLOG_EVENT.read_text(encoding="utf-8")
        go_codes = go_string_consts(codes_src, "EventCode")
        if go_codes != set(contract["eventCodes"]):
            raise Fail(f"event code drift: go-only={go_codes - set(contract['eventCodes'])} "
                       f"contract-only={set(contract['eventCodes']) - go_codes}")
        for go_type, key in (("Severity", "severity"), ("Outcome", "outcome"),
                             ("Component", "component"), ("FailureClass", "failureClass")):
            go_values = {v for v in go_string_consts(event_src, go_type) if v}
            if go_values != set(contract[key]):
                raise Fail(f"{key} drift between obslog and contract: "
                           f"go-only={go_values - set(contract[key])} "
                           f"contract-only={set(contract[key]) - go_values}")
        schema_match = re.search(r'SchemaVersion\s*=\s*"([^"]+)"', event_src)
        if not schema_match or schema_match.group(1) != contract["schemaVersion"]:
            raise Fail("schemaVersion drift between obslog and contract")

        # 3. Fixtures.
        valid = load(VALID_FIXTURE)
        for event in valid["events"]:
            reasons = check_event_fields(event, contract)
            if reasons:
                raise Fail(f"valid fixture event rejected: {reasons}")
        negative = load(NEGATIVE_FIXTURE)
        for case in negative["cases"]:
            reasons = check_event_fields(case["event"], contract)
            if not reasons:
                raise Fail(f"negative case was not rejected: {case['reason']}")

        # 4. OPS-P0-003 readiness honesty.
        status = load(STATUS)
        obs = next((a for a in status["areas"] if a.get("id") == "OPS-P0-003"), None)
        if obs is None:
            raise Fail("OPS-P0-003 missing from operability status")
        retention_defined = contract["retention"]["policyDefined"]
        routing_configured = contract["alertRouting"]["routingConfigured"]
        if obs.get("status") == "READY" and not (retention_defined and routing_configured):
            raise Fail("OPS-P0-003 cannot be READY while retention or alert routing is unconfigured")
        for ref in obs.get("evidenceRefs", []):
            if not (REPO / ref).is_file():
                raise Fail(f"OPS-P0-003 evidence path does not exist: {ref}")

    except Fail as exc:
        print(f"OBSERVABILITY VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"OBSERVABILITY VALIDATION FAILED (unexpected): {exc}", file=sys.stderr)
        return 2

    print("Memory OS observability contract validation PASS")
    print(f"event codes: {len(contract['eventCodes'])}")
    print(f"valid fixture events: {len(valid['events'])}")
    print(f"negative cases rejected: {len(negative['cases'])}")
    print(f"OPS-P0-003 status: {obs.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
