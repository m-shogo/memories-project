#!/usr/bin/env python3
"""Fail-closed validator for the Memory OS load-test scenario contract and results.

It checks the scenario contract's internal consistency and its evidence paths,
validates the committed results document against it, and enforces load-specific
honesty rules: every persisted result names a defined scenario; every required
scenario has a persisted result; workload/dependency mode and observed status
classes match the scenario contract; environment metadata and a commit SHA are
mandatory; percentile latencies are present; an aborted or integrity-failed run
may not be a PASS; a production-equivalent/real-Apple run may not be claimed as
PASS evidence; series counts stay bounded; a run labelled SOAK must actually be
long; and OPS-P0-006 may not be READY without a production-shaped workload,
capacity boundary, soak and operational thresholds. Every negative fixture case
must be rejected by the same field-level checker without relying on unrelated
scenario-coverage failures.
"""
from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCENARIOS = REPO / "contracts/operations/load-test-scenario-contract.v1.json"
EXEMPTIONS = REPO / "contracts/operations/load-results-exemptions.v1.json"
RESULTS = REPO / "docs/fixtures/memory-os-operability/load-results.sample.v1.json"
NEGATIVE = REPO / "docs/fixtures/memory-os-operability/load-results.negative.v1.json"
STATUS = REPO / "contracts/operations/production-operability-status.json"
METRICS_CONTRACT = REPO / "contracts/operations/metrics-contract.v1.json"
RATE_LIMIT_CONTRACT = REPO / "contracts/operations/rate-limit-policy-contract.v1.json"

SERIES_CEILING = 5000
SOAK_MIN_SECONDS = 300
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_ENV = ("os", "arch", "goVersion", "dependencyMode", "numCpu")
REQUIRED_RESULT_FIELDS = (
    "scenarioId", "workloadType", "dependencyMode", "durationSeconds",
    "requests", "successes", "failures", "statusClassCounts", "throughput",
    "latencyP50Ms", "latencyP95Ms", "latencyP99Ms", "maxInFlight",
    "metricsSeriesBefore", "metricsSeriesAfter", "integrityResult",
    "abortReason", "result",
)


class Fail(RuntimeError):
    pass


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path}: {exc}") from exc


def check_results(
    doc: dict,
    contract: dict,
    exempt_ids: set[str],
    *,
    require_coverage: bool = True,
) -> list[str]:
    """Return reasons a results document is invalid (empty = clean)."""
    reasons: list[str] = []
    if doc.get("schemaVersion") != contract["resultsSchemaVersion"]:
        reasons.append(f"results schemaVersion drift: {doc.get('schemaVersion')}")
    commit = doc.get("commitSha")
    if not isinstance(commit, str) or not COMMIT_SHA.fullmatch(commit):
        reasons.append("results missing a full 40-character commit SHA")
    env = doc.get("environment")
    if not isinstance(env, dict):
        reasons.append("results missing environment metadata")
    else:
        for key in REQUIRED_ENV:
            if not env.get(key):
                reasons.append(f"environment missing {key}")

    scenario_by_id = {s["scenarioId"]: s for s in contract["executedScenarios"]}
    forbidden_pass = set(contract["forbiddenAsPass"])
    scenarios = doc.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        reasons.append("results have no scenarios")
        return reasons

    seen: set[str] = set()
    for result in scenarios:
        sid = result.get("scenarioId", "?")
        if sid in seen:
            reasons.append(f"{sid}: duplicate persisted result")
        seen.add(sid)

        for field in REQUIRED_RESULT_FIELDS:
            if field not in result:
                reasons.append(f"{sid}: missing result field {field}")
        scenario = scenario_by_id.get(sid)
        if scenario is None:
            reasons.append(f"{sid}: not a defined scenario in the contract")

        passed = result.get("result") == "PASS"
        if result.get("result") not in ("PASS", "FAIL", "ABORTED"):
            reasons.append(f"{sid}: unknown result value {result.get('result')}")
        if result.get("abortReason") and passed:
            reasons.append(f"{sid}: aborted run marked PASS")
        if passed and result.get("integrityResult") != "PASS":
            reasons.append(f"{sid}: PASS without an integrity PASS")
        if passed and result.get("dependencyMode") in forbidden_pass:
            reasons.append(f"{sid}: PASS claimed for {result.get('dependencyMode')} (not real evidence)")

        requests = result.get("requests")
        successes = result.get("successes")
        failures = result.get("failures")
        if all(isinstance(v, int) and v >= 0 for v in (requests, successes, failures)):
            if successes + failures != requests:
                reasons.append(f"{sid}: successes + failures != requests")
        else:
            reasons.append(f"{sid}: invalid request/success/failure counts")

        counts = result.get("statusClassCounts")
        if not isinstance(counts, dict) or not counts:
            reasons.append(f"{sid}: statusClassCounts missing or empty")
            observed: set[str] = set()
        else:
            observed = set()
            total = 0
            for status_class, count in counts.items():
                if status_class not in {"1xx", "2xx", "3xx", "4xx", "5xx"}:
                    reasons.append(f"{sid}: unknown status class {status_class}")
                if not isinstance(count, int) or count < 0:
                    reasons.append(f"{sid}: invalid count for {status_class}")
                    continue
                total += count
                if count > 0:
                    observed.add(status_class)
            if isinstance(requests, int) and total != requests:
                reasons.append(f"{sid}: status class counts total {total} != requests {requests}")

        if scenario is not None:
            if result.get("workloadType") != scenario.get("workloadType"):
                reasons.append(f"{sid}: workloadType drift")
            if result.get("dependencyMode") != scenario.get("dependencyMode"):
                reasons.append(f"{sid}: dependencyMode drift")
            expected = set(scenario.get("expectedStatusClasses", []))
            if not expected:
                reasons.append(f"{sid}: scenario has no expectedStatusClasses")
            if passed and not observed.issubset(expected):
                reasons.append(
                    f"{sid}: PASS observed unexpected status classes "
                    f"{sorted(observed - expected)}; expected only {sorted(expected)}"
                )

        series_after = result.get("metricsSeriesAfter")
        if isinstance(series_after, int) and series_after > SERIES_CEILING:
            reasons.append(f"{sid}: cardinality breach, series={series_after}")
        if result.get("workloadType") == "SOAK":
            dur = result.get("durationSeconds", 0)
            if not isinstance(dur, (int, float)) or dur < SOAK_MIN_SECONDS:
                reasons.append(f"{sid}: labelled SOAK but only {dur}s (SOAK PROOF INSUFFICIENT)")

    if require_coverage:
        required = set(scenario_by_id) - exempt_ids
        missing = sorted(required - seen)
        if missing:
            reasons.append(f"required executed scenarios missing persisted results: {missing}")
    return reasons


def main() -> int:
    try:
        contract = load(SCENARIOS)
        exemptions = load(EXEMPTIONS)

        exec_ids = [s["scenarioId"] for s in contract["executedScenarios"]]
        if len(exec_ids) != len(set(exec_ids)):
            raise Fail("duplicate executed scenario id")
        workloads = set(contract["workloadTypes"])
        modes = set(contract["dependencyModes"])
        for scenario in contract["executedScenarios"]:
            if scenario["workloadType"] not in workloads:
                raise Fail(f"{scenario['scenarioId']}: unknown workloadType")
            if scenario["dependencyMode"] not in modes:
                raise Fail(f"{scenario['scenarioId']}: unknown dependencyMode")
            if not scenario.get("expectedStatusClasses"):
                raise Fail(f"{scenario['scenarioId']}: expectedStatusClasses missing")
            for ref in scenario.get("evidenceRefs", []):
                if not (REPO / ref).is_file():
                    raise Fail(f"{scenario['scenarioId']}: evidence path missing: {ref}")
        for ref in contract["evidenceRefs"]:
            if not (REPO / ref).is_file():
                raise Fail(f"contract evidence path missing: {ref}")

        if exemptions.get("schemaVersion") != "memory-os-load-result-exemptions.v1":
            raise Fail("load-result exemptions schema drift")
        exempt_ids: set[str] = set()
        for item in exemptions.get("exemptions", []):
            sid = item.get("scenarioId")
            if sid not in exec_ids:
                raise Fail(f"result exemption references unknown scenario: {sid}")
            if not item.get("reason"):
                raise Fail(f"result exemption lacks reason: {sid}")
            if sid in exempt_ids:
                raise Fail(f"duplicate result exemption: {sid}")
            exempt_ids.add(sid)

        results = load(RESULTS)
        reasons = check_results(results, contract, exempt_ids)
        if reasons:
            raise Fail(f"shipped results invalid: {reasons}")

        negative = load(NEGATIVE)
        for case in negative["cases"]:
            if not check_results(
                case["doc"], contract, exempt_ids, require_coverage=False
            ):
                raise Fail(f"negative case was not rejected: {case['reason']}")

        # Self-prove the two contract gaps this revision closes. These are
        # generated from the shipped clean fixture, so a future refactor cannot
        # silently remove the checks without making this validator fail.
        status_drift = copy.deepcopy(results)
        first = status_drift["scenarios"][0]
        first["statusClassCounts"] = {"5xx": first["requests"]}
        first["successes"] = 0
        first["failures"] = first["requests"]
        if not check_results(status_drift, contract, exempt_ids):
            raise Fail("self-check failed: unexpected status class was accepted")

        required_ids = [sid for sid in exec_ids if sid not in exempt_ids]
        missing_result = copy.deepcopy(results)
        missing_result["scenarios"] = [
            r for r in missing_result["scenarios"] if r.get("scenarioId") != required_ids[0]
        ]
        if not check_results(missing_result, contract, exempt_ids):
            raise Fail("self-check failed: missing required scenario result was accepted")

        status = load(STATUS)
        area = {a["id"]: a for a in status["areas"]}

        load_gate = area.get("OPS-P0-006")
        if load_gate is None:
            raise Fail("OPS-P0-006 missing from operability status")
        if load_gate.get("status") == "READY":
            readiness = contract["readiness"]
            for need in (
                "productionShapedWorkload", "capacityBoundaryEstablished",
                "sustainedSoakEvidence", "operationalThresholds",
                "productionEquivalentDependencies",
            ):
                if not readiness.get(need):
                    raise Fail(f"OPS-P0-006 READY but scenario readiness.{need} is false")
        for ref in load_gate.get("evidenceRefs", []):
            if not (REPO / ref).is_file():
                raise Fail(f"OPS-P0-006 evidence path missing: {ref}")

        metrics_gate = area.get("OPS-P0-004")
        if metrics_gate and metrics_gate.get("status") == "READY":
            metrics_readiness = load(METRICS_CONTRACT)["readiness"]
            for need in (
                "exporterImplemented", "scrapeEndpointExposed", "dashboardsDefined",
                "alertRoutingConfigured", "retentionDefined", "loadCalibrated",
            ):
                if not metrics_readiness.get(need):
                    raise Fail(f"OPS-P0-004 READY but metrics readiness.{need} is false")

        rate_gate = area.get("OPS-P0-005")
        if rate_gate and rate_gate.get("status") == "READY":
            store = load(RATE_LIMIT_CONTRACT)["store"]
            if not store.get("distributedEnforcementImplemented"):
                raise Fail("OPS-P0-005 READY but distributed enforcement is not implemented")

        if status.get("productionDecision") == "GO":
            if any(area[g].get("status") != "READY" for g in area if area[g].get("blocking")):
                raise Fail("productionDecision GO while a blocking gate is not READY")

    except Fail as exc:
        print(f"LOAD VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"LOAD VALIDATION FAILED (unexpected): {exc}", file=sys.stderr)
        return 2

    print("Memory OS load-test validation PASS")
    print(
        f"executed scenarios: {len(contract['executedScenarios'])}  "
        f"persisted-result exemptions: {len(exempt_ids)}  "
        f"deferred: {len(contract['deferredScenarios'])}"
    )
    print(
        f"results scenarios: {len(results['scenarios'])}  "
        f"negative cases rejected: {len(negative['cases'])}"
    )
    print(
        f"OPS-P0-006 status: {load_gate.get('status')}  "
        f"productionDecision: {status.get('productionDecision')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
