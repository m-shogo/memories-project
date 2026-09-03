#!/usr/bin/env python3
"""Fail-closed validation for the local/CI rate-limit emergency decision drill."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/rate-limit-emergency-drill-contract.v1.json"
OPERATIONS_PATH = ROOT / "contracts/operations/rate-limit-operations-contract.v1.json"
POLICY_PATH = ROOT / "contracts/operations/rate-limit-policy-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/rate-limit-emergency-drill-results.sample.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_TEXT = re.compile(
    r"(?:postgres(?:ql)?://|https?://|bearer\s+|password|passwd|private[_ -]?key|access[_ -]?key|account[_ -]?id|session[_ -]?id|request[_ -]?id|apple[_ -]?subject)",
    re.IGNORECASE,
)


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def require_commit_ancestor(
    commit_sha: str,
    _subprocess_run: Callable[..., Any] = subprocess.run,
) -> None:
    if subprocess.run is not _subprocess_run:
        raise ValidationFailure("emergency drill validator subprocess transport authority drift")
    completed = _subprocess_run(
        ["git", "merge-base", "--is-ancestor", commit_sha, "HEAD"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    require(type(completed.returncode) is int and completed.returncode == 0,
            "result commitSha must be an ancestor of current HEAD")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-commit-sha")
    parser.add_argument("--require-result", action="store_true")
    parser.add_argument("--require-reconciled", action="store_true")
    return parser.parse_args()


def iter_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        strings.append(value)
    elif isinstance(value, list):
        for item in value:
            strings.extend(iter_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(iter_strings(item))
    return strings


def validate_result(
    result: dict[str, Any],
    contract: dict[str, Any],
    expected_sha: str | None,
    _require_commit_ancestor: Callable[[str], None] = require_commit_ancestor,
    _iter_strings: Callable[[Any], list[str]] = iter_strings,
    _sha_re: re.Pattern[str] = SHA_RE,
    _forbidden_text: re.Pattern[str] = FORBIDDEN_TEXT,
) -> None:
    require(require_commit_ancestor is _require_commit_ancestor,
            "emergency drill validator lineage helper authority drift")
    require(iter_strings is _iter_strings,
            "emergency drill validator string traversal authority drift")
    require(SHA_RE is _sha_re,
            "emergency drill validator SHA semantics authority drift")
    require(FORBIDDEN_TEXT is _forbidden_text,
            "emergency drill validator privacy semantics authority drift")
    require(result.get("schemaVersion") == "memory-os-rate-limit-emergency-drill-results.v1",
            "result schemaVersion drift")
    commit_sha = result.get("commitSha")
    require(isinstance(commit_sha, str) and _sha_re.fullmatch(commit_sha) is not None,
            "result commitSha must be a full SHA")
    _require_commit_ancestor(commit_sha)
    if expected_sha is not None:
        require(commit_sha == expected_sha, "result commitSha does not match expected source")
    require(result.get("classification") == "LOCAL_CI_DECISION_MODEL",
            "result classification drift")
    scenario = contract["scenario"]
    require(result.get("scenarioId") == scenario["scenarioId"], "scenarioId drift")
    require(result.get("policyId") == scenario["policyId"], "policyId drift")
    require(result.get("modeSequence") == [
        scenario["initialMode"], scenario["emergencyMode"],
        scenario["expiredMode"], scenario["restoredMode"],
    ], "mode sequence drift")
    checks = result.get("recoveryChecks")
    require(isinstance(checks, dict), "recoveryChecks must be an object")
    require(set(checks) == set(scenario["requiredRecoveryChecks"]),
            "recovery check set drift")
    require(all(value == "PASS" for value in checks.values()),
            "every recovery check must PASS")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "assertions must be an object")
    expected_assertions = contract["requiredAssertions"]
    require(set(assertions) == set(expected_assertions), "assertion set drift")
    for key, expected in expected_assertions.items():
        require(assertions.get(key) is expected, f"assertion failed or drifted: {key}")
    require(result.get("result") == "PASS", "drill result must PASS")
    require(result.get("integrityResult") == "PASS", "drill integrity must PASS")
    require(result.get("limitations") == contract["limitations"], "result limitations drift")
    joined = "\n".join(_iter_strings(result))
    require(_forbidden_text.search(joined) is None, "result contains secret/identity-like text")


_CANONICAL_ROOT = ROOT
_CANONICAL_CONTRACT_PATH = CONTRACT_PATH
_CANONICAL_OPERATIONS_PATH = OPERATIONS_PATH
_CANONICAL_POLICY_PATH = POLICY_PATH
_CANONICAL_RESULT_PATH = RESULT_PATH
_CANONICAL_SUBPROCESS_RUN = subprocess.run
_CANONICAL_REQUIRE = require
_CANONICAL_REQUIRE_COMMIT_ANCESTOR = require_commit_ancestor
_CANONICAL_LOAD = load
_CANONICAL_PARSE_ARGS = parse_args
_CANONICAL_ITER_STRINGS = iter_strings
_CANONICAL_VALIDATE_RESULT = validate_result
_CANONICAL_SHA_RE = SHA_RE
_CANONICAL_FORBIDDEN_TEXT = FORBIDDEN_TEXT


def _require_path_authority(current: Path, canonical: Path, label: str, *, required: bool) -> None:
    if current != canonical:
        raise ValidationFailure(f"emergency drill validator {label} authority drift")
    if current.is_symlink():
        raise ValidationFailure(f"emergency drill validator {label} cannot be a symlink")
    if required and not current.is_file():
        raise ValidationFailure(f"canonical emergency drill validator {label} missing")
    if current.exists():
        try:
            resolved = current.resolve(strict=True)
        except (FileNotFoundError, OSError, RuntimeError) as exc:
            raise ValidationFailure(f"emergency drill validator {label} cannot be resolved") from exc
        if resolved != canonical:
            raise ValidationFailure(f"emergency drill validator {label} escaped canonical path")


_CANONICAL_REQUIRE_PATH_AUTHORITY = _require_path_authority


def enforce_runtime_authorities(
    _root: Path = _CANONICAL_ROOT,
    _contract: Path = _CANONICAL_CONTRACT_PATH,
    _operations: Path = _CANONICAL_OPERATIONS_PATH,
    _policy: Path = _CANONICAL_POLICY_PATH,
    _result: Path = _CANONICAL_RESULT_PATH,
    _subprocess_run: Callable[..., Any] = _CANONICAL_SUBPROCESS_RUN,
    _require: Callable[[bool, str], None] = _CANONICAL_REQUIRE,
    _require_commit_ancestor: Callable[[str], None] = _CANONICAL_REQUIRE_COMMIT_ANCESTOR,
    _load: Callable[[Path], dict[str, Any]] = _CANONICAL_LOAD,
    _parse_args: Callable[[], argparse.Namespace] = _CANONICAL_PARSE_ARGS,
    _iter_strings: Callable[[Any], list[str]] = _CANONICAL_ITER_STRINGS,
    _validate_result: Callable[..., None] = _CANONICAL_VALIDATE_RESULT,
    _path_guard: Callable[..., None] = _CANONICAL_REQUIRE_PATH_AUTHORITY,
    _sha_re: re.Pattern[str] = _CANONICAL_SHA_RE,
    _forbidden_text: re.Pattern[str] = _CANONICAL_FORBIDDEN_TEXT,
) -> None:
    if ROOT != _root or _root != Path(__file__).resolve().parents[1]:
        raise ValidationFailure("emergency drill validator repository authority drift")
    if _require_path_authority is not _path_guard:
        raise ValidationFailure("emergency drill validator path guard execution authority drift")
    _path_guard(CONTRACT_PATH, _contract, "contract", required=True)
    _path_guard(OPERATIONS_PATH, _operations, "operations contract", required=True)
    _path_guard(POLICY_PATH, _policy, "policy contract", required=True)
    _path_guard(RESULT_PATH, _result, "result", required=False)
    helpers = (
        (subprocess.run, _subprocess_run, "subprocess transport"),
        (require, _require, "require"),
        (require_commit_ancestor, _require_commit_ancestor, "lineage helper"),
        (load, _load, "load"),
        (parse_args, _parse_args, "argument parser"),
        (iter_strings, _iter_strings, "string traversal"),
        (validate_result, _validate_result, "result validator"),
        (SHA_RE, _sha_re, "SHA semantics"),
        (FORBIDDEN_TEXT, _forbidden_text, "privacy semantics"),
    )
    for current, canonical, label in helpers:
        if current is not canonical:
            raise ValidationFailure(f"emergency drill validator {label} execution authority drift")


_CANONICAL_ENFORCE_RUNTIME_AUTHORITIES = enforce_runtime_authorities


def main(
    _guard: Callable[[], None] = _CANONICAL_ENFORCE_RUNTIME_AUTHORITIES,
    _parse_args: Callable[[], argparse.Namespace] = _CANONICAL_PARSE_ARGS,
    _load: Callable[[Path], dict[str, Any]] = _CANONICAL_LOAD,
    _validate_result: Callable[..., None] = _CANONICAL_VALIDATE_RESULT,
) -> int:
    if enforce_runtime_authorities is not _guard:
        raise ValidationFailure("emergency drill validator runtime guard execution authority drift")
    if parse_args is not _parse_args:
        raise ValidationFailure("emergency drill validator argument parser execution authority drift")
    if load is not _load:
        raise ValidationFailure("emergency drill validator load execution authority drift")
    if validate_result is not _validate_result:
        raise ValidationFailure("emergency drill validator result validator execution authority drift")
    _guard()
    args = _parse_args()
    contract = _load(CONTRACT_PATH)
    operations = _load(OPERATIONS_PATH)
    policy = _load(POLICY_PATH)
    require(contract.get("schemaVersion") == "memory-os-rate-limit-emergency-drill.v1",
            "contract schemaVersion drift")
    require(contract.get("sourceCommitMustBeAncestorOfCurrentHead") is True,
            "source commit lineage authority drift")
    expected_paths = {
        "sourceOperationsContract": "contracts/operations/rate-limit-operations-contract.v1.json",
        "sourcePolicyContract": "contracts/operations/rate-limit-policy-contract.v1.json",
        "sourceEvidenceContract": "contracts/operations/rate-limit-operation-evidence-contract.v1.json",
        "runner": "scripts/run-memory-os-rate-limit-emergency-drill.py",
        "validator": "scripts/validate-memory-os-rate-limit-emergency-drill.py",
        "resultPath": "docs/fixtures/memory-os-operability/rate-limit-emergency-drill-results.sample.v1.json",
    }
    for field, expected in expected_paths.items():
        require(contract.get(field) == expected, f"{field} path drift")
    require(contract.get("classification") == "LOCAL_CI_DECISION_MODEL",
            "classification drift")

    scenario = contract.get("scenario")
    require(isinstance(scenario, dict), "scenario must be an object")
    require(scenario.get("policyId") == "apple-exchange", "drill policy drift")
    require(scenario.get("requiredPolicyFailureMode") == "fail_closed_emergency_local",
            "required policy failure mode drift")
    require(scenario.get("initialMode") == "NORMAL_CONFIGURED", "initial mode drift")
    require(scenario.get("emergencyMode") == "STRICT_LOCAL_EMERGENCY", "emergency mode drift")
    require(scenario.get("expiredMode") == "ROUTE_FAIL_CLOSED", "expired mode must fail closed")
    require(scenario.get("restoredMode") == "NORMAL_CONFIGURED", "restored mode drift")
    require(scenario.get("maximumEmergencyDurationMinutes") == 60,
            "emergency duration boundary drift")
    required_checks = scenario.get("requiredRecoveryChecks")
    require(isinstance(required_checks, list) and len(required_checks) == 8 and
            len(required_checks) == len(set(required_checks)),
            "required recovery checks drift")

    policies = policy.get("policies")
    require(isinstance(policies, list), "source policies must be a list")
    selected = [item for item in policies if isinstance(item, dict) and item.get("policyId") == "apple-exchange"]
    require(len(selected) == 1 and selected[0].get("failureMode") == "fail_closed_emergency_local",
            "apple-exchange no longer permits only the bounded emergency-local fallback")

    modes = operations.get("operationalModes")
    require(isinstance(modes, list), "operationalModes must be a list")
    mode_map = {item.get("id"): item for item in modes if isinstance(item, dict)}
    require(mode_map.get("STRICT_LOCAL_EMERGENCY", {}).get("allowed") is True,
            "strict local emergency mode unavailable")
    require(mode_map.get("ROUTE_FAIL_CLOSED", {}).get("allowed") is True,
            "route fail-closed mode unavailable")
    require(mode_map.get("UNLIMITED_OR_FAIL_OPEN", {}).get("allowed") is False,
            "forbidden fail-open mode became selectable")

    assertions = contract.get("requiredAssertions")
    require(isinstance(assertions, dict) and len(assertions) == 14,
            "requiredAssertions drift")
    for flag in (
        "policyExplicitlyPermitsEmergencyLocal", "forbiddenFailOpenModeNeverSelected",
        "expirySelectsRouteFailClosed", "recoveryBeforeAllChecksPassRejected",
        "recoveryAfterAllChecksPassReturnsNormal", "appendOnlyWriterAcceptsValidLocalRecord",
        "duplicateOperationIdRejected", "exactSourceCommitBound",
    ):
        require(assertions.get(flag) is True, f"required assertion must be true: {flag}")
    for flag in (
        "containsSecrets", "runtimeTrafficChanged", "productionTraffic",
        "productionCredentials", "productionEvidence", "productionControlPlaneExercised",
    ):
        require(assertions.get(flag) is False, f"non-production assertion must be false: {flag}")

    limitations = contract.get("limitations")
    require(isinstance(limitations, list) and len(limitations) >= 6,
            "limitations must remain explicit")
    joined_limitations = "\n".join(limitations)
    for phrase in (
        "does not mutate a deployed", "distributed shared atomic store",
        "trusted-proxy", "simulated passage", "production alert routing",
        "cannot make OPS-P0-005 READY",
    ):
        require(phrase in joined_limitations, f"required limitation missing: {phrase}")

    result_exists = RESULT_PATH.is_file()
    if args.require_result:
        require(result_exists, "exact-source drill result is required")
    if result_exists:
        _validate_result(_load(RESULT_PATH), contract, args.expected_commit_sha)

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    require(readiness.get("contractDefined") is True, "readiness.contractDefined must be true")
    if args.require_reconciled:
        for flag in (
            "runnerImplemented", "validatorImplemented", "automaticWorkflowImplemented",
            "exactSourceResultCommitted", "localDecisionModelDrillExecuted",
        ):
            require(readiness.get(flag) is True, f"reconciled readiness missing: {flag}")
    for flag in (
        "runtimeEmergencyModeDrillExecuted", "productionControlPlaneImplemented",
        "automaticProductionExpiryImplemented", "productionReady",
    ):
        require(readiness.get(flag) is False, f"unproven readiness cannot be true: {flag}")

    print("Memory OS rate-limit emergency decision drill validation PASS")
    print(f"exact-source result: {'PRESENT' if result_exists else 'NOT_YET_COMMITTED'}")
    print("production control plane: NOT_EXERCISED")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"RATE-LIMIT EMERGENCY DRILL VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
