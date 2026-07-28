#!/usr/bin/env python3
"""Fail-closed validator for the Memory OS load-test scenario contract and results.

It checks the scenario contract's internal consistency and its evidence paths,
validates the committed results document against it, and enforces load-specific
honesty rules: every result names a defined scenario; environment metadata and a
commit SHA are mandatory; percentile latencies are present; an aborted or
integrity-failed run may not be a PASS; a MOCK/production-equivalent/real-Apple
run may not be claimed as production evidence; series counts stay bounded; a run
labelled SOAK must actually be long; and OPS-P0-006 may not be READY without a
production-shaped workload, capacity boundary, soak and operational thresholds
(and OPS-P0-004/005 may not be READY without their own evidence). Every negative
fixture case must be rejected by the same results checker.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCENARIOS = REPO / "contracts/operations/load-test-scenario-contract.v1.json"
RESULTS = REPO / "docs/fixtures/memory-os-operability/load-results.sample.v1.json"
NEGATIVE = REPO / "docs/fixtures/memory-os-operability/load-results.negative.v1.json"
STATUS = REPO / "contracts/operations/production-operability-status.json"
METRICS_CONTRACT = REPO / "contracts/operations/metrics-contract.v1.json"
RATE_LIMIT_CONTRACT = REPO / "contracts/operations/rate-limit-policy-contract.v1.json"

SERIES_CEILING = 5000  # a run whose series exceed this is a cardinality breach
SOAK_MIN_SECONDS = 300  # a SOAK run shorter than this is not a soak
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


def check_results(doc: dict, contract: dict) -> list[str]:
    """Return reasons a results document is invalid (empty = clean)."""
    reasons: list[str] = []
    if doc.get("schemaVersion") != contract["resultsSchemaVersion"]:
        reasons.append(f"results schemaVersion drift: {doc.get('schemaVersion')}")
    commit = doc.get("commitSha")
    if not commit or commit == "unknown":
        reasons.append("results missing a commit SHA")
    env = doc.get("environment")
    if not isinstance(env, dict):
        reasons.append("results missing environment metadata")
    else:
        for key in REQUIRED_ENV:
            if not env.get(key):
                reasons.append(f"environment missing {key}")

    defined = {s["scenarioId"] for s in contract["executedScenarios"]}
    forbidden_pass = set(contract["forbiddenAsPass"])
    scenarios = doc.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        reasons.append("results have no scenarios")
        return reasons

    for result in scenarios:
        sid = result.get("scenarioId", "?")
        for field in REQUIRED_RESULT_FIELDS:
            if field not in result:
                reasons.append(f"{sid}: missing result field {field}")
        if sid not in defined:
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
        series_after = result.get("metricsSeriesAfter")
        if isinstance(series_after, int) and series_after > SERIES_CEILING:
            reasons.append(f"{sid}: cardinality breach, series={series_after}")
        if result.get("workloadType") == "SOAK":
            dur = result.get("durationSeconds", 0)
            if not isinstance(dur, (int, float)) or dur < SOAK_MIN_SECONDS:
                reasons.append(f"{sid}: labelled SOAK but only {dur}s (SOAK PROOF INSUFFICIENT)")
    return reasons


def main() -> int:
    try:
        contract = load(SCENARIOS)

        # Contract internal consistency.
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
            for ref in scenario.get("evidenceRefs", []):
                if not (REPO / ref).is_file():
                    raise Fail(f"{scenario['scenarioId']}: evidence path missing: {ref}")
        for ref in contract["evidenceRefs"]:
            if not (REPO / ref).is_file():
                raise Fail(f"contract evidence path missing: {ref}")

        # The shipped results document must be clean.
        results = load(RESULTS)
        reasons = check_results(results, contract)
        if reasons:
            raise Fail(f"shipped results invalid: {reasons}")

        # Every negative case must be rejected.
        negative = load(NEGATIVE)
        for case in negative["cases"]:
            if not check_results(case["doc"], contract):
                raise Fail(f"negative case was not rejected: {case['reason']}")

        # Readiness honesty across the three gates this checkpoint touches.
        status = load(STATUS)
        area = {a["id"]: a for a in status["areas"]}

        load_gate = area.get("OPS-P0-006")
        if load_gate is None:
            raise Fail("OPS-P0-006 missing from operability status")
        if load_gate.get("status") == "READY":
            r = contract["readiness"]
            for need in ("productionShapedWorkload", "capacityBoundaryEstablished",
                         "sustainedSoakEvidence", "operationalThresholds",
                         "productionEquivalentDependencies"):
                if not r.get(need):
                    raise Fail(f"OPS-P0-006 READY but scenario readiness.{need} is false")
        for ref in load_gate.get("evidenceRefs", []):
            if not (REPO / ref).is_file():
                raise Fail(f"OPS-P0-006 evidence path missing: {ref}")

        metrics_gate = area.get("OPS-P0-004")
        if metrics_gate and metrics_gate.get("status") == "READY":
            m = load(METRICS_CONTRACT)["readiness"]
            for need in ("exporterImplemented", "scrapeEndpointExposed", "dashboardsDefined",
                         "alertRoutingConfigured", "retentionDefined", "loadCalibrated"):
                if not m.get(need):
                    raise Fail(f"OPS-P0-004 READY but metrics readiness.{need} is false")

        rate_gate = area.get("OPS-P0-005")
        if rate_gate and rate_gate.get("status") == "READY":
            store = load(RATE_LIMIT_CONTRACT)["store"]
            if not store.get("distributedEnforcementImplemented"):
                raise Fail("OPS-P0-005 READY but distributed enforcement is not implemented")

        if status.get("productionDecision") == "GO":
            # This checkpoint never advances production; a GO here is a mistake.
            if any(area[g].get("status") != "READY" for g in area if area[g].get("blocking")):
                raise Fail("productionDecision GO while a blocking gate is not READY")

    except Fail as exc:
        print(f"LOAD VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"LOAD VALIDATION FAILED (unexpected): {exc}", file=sys.stderr)
        return 2

    print("Memory OS load-test validation PASS")
    print(f"executed scenarios: {len(contract['executedScenarios'])}  "
          f"deferred: {len(contract['deferredScenarios'])}")
    print(f"results scenarios: {len(results['scenarios'])}  "
          f"negative cases rejected: {len(negative['cases'])}")
    print(f"OPS-P0-006 status: {load_gate.get('status')}  "
          f"productionDecision: {status.get('productionDecision')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
