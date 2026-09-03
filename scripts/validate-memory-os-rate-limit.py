#!/usr/bin/env python3
"""Fail-closed validator for the Memory OS rate-limit policy contract.

It checks the contract's internal consistency, its agreement with the Go
implementation (route classes, failure modes, observability event codes), that
every public unauthenticated route has an enabled fail-closed policy, and that
OPS-P0-005 is not marked READY without distributed-enforcement, store-failure
and load evidence. Every negative fixture case must be rejected by the same
policy-set checker, so a hole in the checker is itself a failure.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DEFAULT_REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = DEFAULT_REPO / "contracts/operations/rate-limit-policy-contract.v1.json"
DEFAULT_NEGATIVE = DEFAULT_REPO / "docs/fixtures/memory-os-operability/rate-limit-policies.negative.v1.json"
DEFAULT_STATUS = DEFAULT_REPO / "contracts/operations/production-operability-status.json"
DEFAULT_ENFORCE_GO = DEFAULT_REPO / "services/import-api/internal/ratelimit/enforce.go"
DEFAULT_OBSLOG_CODES = DEFAULT_REPO / "services/import-api/internal/obslog/codes.go"
DEFAULT_MAX_CAPACITY = 1_000_000
DEFAULT_MAX_REFILL = 1_000_000

REPO = DEFAULT_REPO
CONTRACT = DEFAULT_CONTRACT
NEGATIVE = DEFAULT_NEGATIVE
STATUS = DEFAULT_STATUS
ENFORCE_GO = DEFAULT_ENFORCE_GO
OBSLOG_CODES = DEFAULT_OBSLOG_CODES

MAX_CAPACITY = DEFAULT_MAX_CAPACITY
MAX_REFILL = DEFAULT_MAX_REFILL


class Fail(RuntimeError):
    pass


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path}: {exc}") from exc


def go_consts(source: str, go_type: str) -> set[str]:
    return set(re.findall(rf'{go_type}\s*=\s*"([^"]+)"', source))


def check_policy_set(
    policies: list,
    contract: dict,
    inventory: list,
    _max_capacity: int = DEFAULT_MAX_CAPACITY,
    _max_refill: int = DEFAULT_MAX_REFILL,
) -> list[str]:
    """Return reasons the policy set is invalid (empty = clean)."""
    reasons: list[str] = []
    allowed_dims = set(contract["allowedKeyDimensions"])
    forbidden_dims = set(contract["forbiddenKeyDimensions"])
    classes = set(contract["routeClasses"])
    modes = set(contract["failureModes"])
    inventory_routes = {r["routeTemplate"] for r in inventory}

    seen_ids: set[str] = set()
    enabled_public_routes: set[str] = set()
    for policy in policies:
        pid = policy.get("policyId")
        if not pid:
            reasons.append("policy missing policyId")
        elif pid in seen_ids:
            reasons.append(f"duplicate policy id: {pid}")
        seen_ids.add(pid)

        route = policy.get("routeTemplate")
        if route not in inventory_routes:
            reasons.append(f"unknown route template: {route}")
        if policy.get("routeClass") not in classes:
            reasons.append(f"unknown route class: {policy.get('routeClass')}")
        if "failureMode" not in policy:
            reasons.append(f"{pid}: missing failure mode")
        elif policy["failureMode"] not in modes:
            reasons.append(f"{pid}: unknown failure mode {policy['failureMode']}")
        if "privacyClassification" not in policy:
            reasons.append(f"{pid}: missing privacy classification")

        for dim in policy.get("keyDimensions", []):
            if dim in forbidden_dims:
                reasons.append(f"{pid}: forbidden key dimension {dim}")
            elif dim not in allowed_dims:
                reasons.append(f"{pid}: unknown key dimension {dim}")

        if policy.get("enabled"):
            for guard in ("global", "network"):
                block = policy.get(guard)
                if not isinstance(block, dict):
                    reasons.append(f"{pid}: enabled policy missing {guard} bucket")
                    continue
                cap = block.get("capacity")
                refill = block.get("refillPerSecond")
                if not isinstance(cap, (int, float)) or cap <= 0 or cap > _max_capacity:
                    reasons.append(f"{pid}: {guard} capacity out of range")
                if not isinstance(refill, (int, float)) or refill <= 0 or refill > _max_refill:
                    reasons.append(f"{pid}: {guard} refill out of range")
            if policy.get("routeClass") in ("PUBLIC_UNAUTHENTICATED", "PUBLIC_AUTHENTICATED"):
                if policy.get("failureMode") not in ("fail_closed", "fail_closed_emergency_local"):
                    reasons.append(f"{pid}: public route must fail closed, got {policy.get('failureMode')}")
                enabled_public_routes.add(route)

    for entry in inventory:
        if entry["routeClass"] == "PUBLIC_UNAUTHENTICATED" and entry["routeTemplate"] not in enabled_public_routes:
            reasons.append(f"public unauthenticated route without an enabled policy: {entry['routeTemplate']}")
    return reasons


def canonical_repo_file(
    path: Path,
    expected: Path,
    label: str,
    _expected_repo: Path = DEFAULT_REPO,
) -> Path:
    if path != expected:
        raise Fail(f"{label} authority drift: {path} != {expected}")
    if path.is_symlink():
        raise Fail(f"{label} authority must not be symlink: {path}")
    try:
        resolved = path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise Fail(f"{label} authority missing: {path}") from exc
    try:
        resolved.relative_to(_expected_repo.resolve(strict=True))
    except ValueError as exc:
        raise Fail(f"{label} authority escapes repository: {path}") from exc
    if resolved != expected.resolve(strict=True):
        raise Fail(f"{label} resolved authority drift: {resolved}")
    if not resolved.is_file():
        raise Fail(f"{label} authority is not file: {path}")
    return resolved


def enforce_runtime_authorities(
    _expected_repo: Path = DEFAULT_REPO,
    _expected_authorities: tuple[tuple[Path, str], ...] = (
        (DEFAULT_CONTRACT, "rate-limit contract"),
        (DEFAULT_NEGATIVE, "rate-limit negative fixture"),
        (DEFAULT_STATUS, "production status"),
        (DEFAULT_ENFORCE_GO, "rate-limit Go source"),
        (DEFAULT_OBSLOG_CODES, "observability code source"),
    ),
    _load=load,
    _go_consts=go_consts,
    _check_policy_set=check_policy_set,
    _path_checker=canonical_repo_file,
    _max_capacity: int = DEFAULT_MAX_CAPACITY,
    _max_refill: int = DEFAULT_MAX_REFILL,
) -> None:
    if REPO != _expected_repo or REPO.resolve() != _expected_repo.resolve():
        raise Fail("repository root authority drift")
    current_paths = (CONTRACT, NEGATIVE, STATUS, ENFORCE_GO, OBSLOG_CODES)
    for current, (expected, label) in zip(current_paths, _expected_authorities, strict=True):
        _path_checker(current, expected, label)
    if load is not _load:
        raise Fail("JSON loader execution authority drift")
    if go_consts is not _go_consts:
        raise Fail("Go constant parser execution authority drift")
    if check_policy_set is not _check_policy_set:
        raise Fail("policy-set checker execution authority drift")
    if canonical_repo_file is not _path_checker:
        raise Fail("path checker execution authority drift")
    if MAX_CAPACITY != _max_capacity:
        raise Fail("maximum capacity semantic authority drift")
    if MAX_REFILL != _max_refill:
        raise Fail("maximum refill semantic authority drift")


def _build_main(
    _canonical_runtime_guard=enforce_runtime_authorities,
    _canonical_load=load,
    _canonical_go_consts=go_consts,
    _canonical_check_policy_set=check_policy_set,
    _canonical_runtime_guard_defaults=enforce_runtime_authorities.__defaults__,
    _canonical_policy_checker_defaults=check_policy_set.__defaults__,
):
    def _main(
        _runtime_guard=_canonical_runtime_guard,
        _load=_canonical_load,
        _go_consts=_canonical_go_consts,
        _check_policy_set=_canonical_check_policy_set,
    ) -> int:
        try:
            if enforce_runtime_authorities is not _canonical_runtime_guard or _runtime_guard is not _canonical_runtime_guard:
                raise Fail("runtime guard execution authority drift")
            if load is not _canonical_load or _load is not _canonical_load:
                raise Fail("main JSON loader execution authority drift")
            if go_consts is not _canonical_go_consts or _go_consts is not _canonical_go_consts:
                raise Fail("main Go constant parser execution authority drift")
            if check_policy_set is not _canonical_check_policy_set or _check_policy_set is not _canonical_check_policy_set:
                raise Fail("main policy-set checker execution authority drift")
            if _canonical_runtime_guard.__defaults__ != _canonical_runtime_guard_defaults:
                raise Fail("runtime guard default authority drift")
            if _canonical_check_policy_set.__defaults__ != _canonical_policy_checker_defaults:
                raise Fail("policy-set checker default authority drift")
            _canonical_runtime_guard()
            contract = _canonical_load(CONTRACT)

            enforce_src = ENFORCE_GO.read_text(encoding="utf-8")
            go_classes = _canonical_go_consts(enforce_src, "RouteClass")
            if go_classes != set(contract["routeClasses"]):
                raise Fail(f"route class drift: go={go_classes} contract={set(contract['routeClasses'])}")
            go_modes = _canonical_go_consts(enforce_src, "FailureMode")
            if go_modes != set(contract["failureModes"]):
                raise Fail(f"failure mode drift: go={go_modes} contract={set(contract['failureModes'])}")
            obslog_src = OBSLOG_CODES.read_text(encoding="utf-8")
            rate_codes = {c for c in _canonical_go_consts(obslog_src, "EventCode") if c.startswith("OBS_RATE_LIMIT")}
            if rate_codes != set(contract["observabilityEventCodes"]):
                raise Fail(f"rate-limit event code drift: go={rate_codes} contract={set(contract['observabilityEventCodes'])}")

            rej = contract["rejectionResponse"]
            if rej["httpStatus"] != 429 or rej["publicErrorCode"] != "SEC_RATE_LIMITED":
                raise Fail("rejection response must be 429 SEC_RATE_LIMITED")
            bounds = rej["retryAfterBoundedSeconds"]
            if bounds["min"] < 1 or bounds["max"] > 86400 or bounds["min"] > bounds["max"]:
                raise Fail("Retry-After bounds invalid")
            if rej.get("bodyRevealsInternalState") is not False:
                raise Fail("rejection body must not reveal internal state")

            card = contract["metricCardinality"]
            if set(card["allowedLabels"]) & set(card["forbiddenLabels"]):
                raise Fail("a metric label is both allowed and forbidden")
            for bad in ("request_id", "ip", "account_id", "apple_subject"):
                if bad in card["allowedLabels"]:
                    raise Fail(f"high-cardinality label allowed: {bad}")

            priv = contract["privacy"]
            if priv["rawIpStored"] or priv["rawIpLogged"] or not priv["networkKeyIsKeyedDigest"] \
                    or priv["digestIsDurableIdentifier"] or not priv["trustedProxyBoundaryExplicit"] \
                    or priv["arbitraryForwardedHeaderTrusted"]:
                raise Fail("privacy invariants violated in contract")

            reasons = _canonical_check_policy_set(contract["policies"], contract, contract["routeInventory"])
            if reasons:
                raise Fail(f"shipped policy set invalid: {reasons}")

            negative = _canonical_load(NEGATIVE)
            for case in negative["cases"]:
                inv = case.get("routeInventory", contract["routeInventory"])
                if not _canonical_check_policy_set(case["policies"], contract, inv):
                    raise Fail(f"negative case was not rejected: {case['reason']}")

            status = _canonical_load(STATUS)
            gate = next((a for a in status["areas"] if a.get("id") == "OPS-P0-005"), None)
            if gate is None:
                raise Fail("OPS-P0-005 missing from operability status")
            if gate.get("status") == "READY":
                if not contract["store"]["distributedEnforcementImplemented"]:
                    raise Fail("OPS-P0-005 READY but distributed enforcement is not implemented")
                required = {"load-calibrated limits", "store-failure behavior proof", "distributed enforcement"}
                if any(any(term in m for term in required) for m in gate.get("missingEvidence", [])):
                    raise Fail("OPS-P0-005 READY but load/store-failure/distributed evidence still missing")
            for ref in gate.get("evidenceRefs", []):
                if not (REPO / ref).is_file():
                    raise Fail(f"OPS-P0-005 evidence path does not exist: {ref}")
            for ref in contract["evidenceRefs"]:
                if not (REPO / ref).is_file():
                    raise Fail(f"contract evidence path does not exist: {ref}")

        except Fail as exc:
            print(f"RATE-LIMIT VALIDATION FAILED: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:  # noqa: BLE001
            print(f"RATE-LIMIT VALIDATION FAILED (unexpected): {exc}", file=sys.stderr)
            return 2

        print("Memory OS rate-limit policy validation PASS")
        print(f"policies: {len(contract['policies'])}")
        print(f"negative cases rejected: {len(negative['cases'])}")
        print(f"OPS-P0-005 status: {gate.get('status')}")
        return 0

    return _main


main = _build_main()
del _build_main


if __name__ == "__main__":
    raise SystemExit(main())
