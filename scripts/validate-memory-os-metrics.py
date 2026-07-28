#!/usr/bin/env python3
"""Fail-closed validator for the Memory OS metrics contract.

It checks the contract's internal consistency, its agreement with the Go
registry (schema version, metric names, types, required labels, histogram
buckets and per-metric cardinality budgets), that no metric carries a forbidden
personal or high-cardinality label, that every label value set is bounded, that
every referenced SLI/SLO/alert resolves, that every SLO stays PROPOSED with no
owner and no data unless it earns APPROVED honestly, that every alert stays
NOT_CONFIGURED unless routing evidence exists, and that OPS-P0-004 is not READY
without exporter, scrape, dashboard, alert-routing, retention and load evidence.

Every negative fixture case must be rejected by the same per-metric checker, so
a hole in the checker is itself a validation failure.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONTRACT = REPO / "contracts/operations/metrics-contract.v1.json"
NEGATIVE = REPO / "docs/fixtures/memory-os-operability/metrics.negative.v1.json"
STATUS = REPO / "contracts/operations/production-operability-status.json"
RECORDER_GO = REPO / "services/import-api/internal/metrics/recorder.go"

ALLOWED_PRIVACY = {"operational_nonpersonal"}
MAX_BUDGET = 100_000
MAX_BUCKETS = 20


class Fail(RuntimeError):
    pass


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Fail(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise Fail(f"invalid JSON: {path}: {exc}") from exc


def valid_buckets(buckets) -> bool:
    if not isinstance(buckets, list) or not buckets or len(buckets) > MAX_BUCKETS:
        return False
    prev = None
    for b in buckets:
        if not isinstance(b, (int, float)) or isinstance(b, bool):
            return False
        if math.isnan(b) or math.isinf(b) or b <= 0:
            return False
        if prev is not None and b <= prev:
            return False
        prev = b
    return True


def check_metric(metric: dict, contract: dict, seen: set[str]) -> list[str]:
    """Return reasons a single metric definition is invalid (empty = clean)."""
    reasons: list[str] = []
    allowed_types = set(contract["allowedTypes"])
    allowed_units = set(contract["allowedUnits"])
    forbidden = set(contract["forbiddenLabels"])
    label_values = contract["labelValues"]
    sli_ids = {s["id"] for s in contract["slis"]}
    alert_ids = {a["id"] for a in contract["alertCandidates"]}

    name = metric.get("metricName")
    if not name or not isinstance(name, str):
        reasons.append("metric missing metricName")
    else:
        if not re.fullmatch(r"memory_os_[a-z0-9_]+", name):
            reasons.append(f"invalid metric name: {name}")
        if name in seen:
            reasons.append(f"duplicate metric name: {name}")

    kind = metric.get("type")
    if kind not in allowed_types:
        reasons.append(f"unknown metric type: {kind}")

    unit = metric.get("unit")
    if unit not in allowed_units:
        reasons.append(f"unknown unit: {unit}")

    if "cardinalityBudget" not in metric:
        reasons.append(f"{name}: missing cardinality budget")
    else:
        budget = metric["cardinalityBudget"]
        if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1 or budget > MAX_BUDGET:
            reasons.append(f"{name}: cardinality budget out of range")

    if metric.get("privacyClassification") not in ALLOWED_PRIVACY:
        reasons.append(f"{name}: missing or unknown privacy classification")

    labels = metric.get("requiredLabels")
    if not isinstance(labels, list):
        reasons.append(f"{name}: requiredLabels must be a list")
    else:
        for label in labels:
            if label in forbidden:
                reasons.append(f"{name}: forbidden label {label}")
            elif label not in label_values:
                reasons.append(f"{name}: label {label} has no bounded value set")

    # Histogram buckets: required and valid for histograms, forbidden otherwise.
    if kind == "histogram":
        if unit != "seconds":
            reasons.append(f"{name}: histogram unit must be seconds")
        if "buckets" not in metric:
            reasons.append(f"{name}: histogram missing buckets")
        elif not valid_buckets(metric["buckets"]):
            reasons.append(f"{name}: invalid histogram buckets")
    else:
        if "buckets" in metric:
            reasons.append(f"{name}: non-histogram must not carry buckets")

    for sli in metric.get("sliUse", []) or []:
        if sli not in sli_ids:
            reasons.append(f"{name}: sliUse references undefined SLI {sli}")
    alert = metric.get("alertCandidate")
    if alert is not None and alert not in alert_ids:
        reasons.append(f"{name}: alertCandidate references undefined alert {alert}")

    return reasons


# --- Go registry cross-check ------------------------------------------------

def parse_go_registry(src: str) -> tuple[dict, dict, dict]:
    """Return (name_consts, bucket_vars, registrations) from recorder.go."""
    name_consts = dict(re.findall(r'(Metric\w+)\s*=\s*"([^"]+)"', src))
    bucket_vars: dict[str, list[float]] = {}
    for var, body in re.findall(r'(\w+Buckets)\s*=\s*\[\]float64\{([^}]*)\}', src):
        bucket_vars[var] = [float(x) for x in re.findall(r'[-\d.]+', body)]

    kind_map = {"TypeCounter": "counter", "TypeGauge": "gauge", "TypeHistogram": "histogram"}
    registrations: dict[str, dict] = {}
    for call in re.findall(r'reg\.register\(spec\{(.*?)\}\)', src):
        name_m = re.search(r'name:\s*(Metric\w+)', call)
        kind_m = re.search(r'kind:\s*(Type\w+)', call)
        labels_m = re.search(r'labels:\s*\[\]string\{([^}]*)\}', call)
        budget_m = re.search(r'budget:\s*(\d+)', call)
        buckets_m = re.search(r'buckets:\s*(\w+Buckets)', call)
        if not (name_m and kind_m and budget_m):
            raise Fail(f"unparseable register call: {call}")
        name = name_consts.get(name_m.group(1))
        if name is None:
            raise Fail(f"unknown metric constant: {name_m.group(1)}")
        labels = re.findall(r'"([^"]+)"', labels_m.group(1)) if labels_m else []
        registrations[name] = {
            "type": kind_map[kind_m.group(1)],
            "labels": labels,
            "budget": int(budget_m.group(1)),
            "buckets": bucket_vars.get(buckets_m.group(1)) if buckets_m else None,
        }
    return name_consts, bucket_vars, registrations


def main() -> int:
    try:
        contract = load(CONTRACT)
        recorder_src = RECORDER_GO.read_text(encoding="utf-8")

        # Schema version must match the Go constant exactly.
        go_schema = re.search(r'SchemaVersion\s*=\s*"([^"]+)"', recorder_src)
        if not go_schema or go_schema.group(1) != contract["schemaVersion"]:
            raise Fail(f"schema version drift: go={go_schema and go_schema.group(1)} contract={contract['schemaVersion']}")

        # No label value set may itself be a forbidden label name, and no allowed
        # label may appear in the forbidden list.
        forbidden = set(contract["forbiddenLabels"])
        if forbidden & set(contract["labelValues"].keys()):
            raise Fail("a labelValues key is also a forbidden label")

        # The shipped metric set must be clean, with every metric checked once.
        seen: set[str] = set()
        for metric in contract["metrics"]:
            reasons = check_metric(metric, contract, seen)
            if reasons:
                raise Fail(f"shipped metric invalid: {reasons}")
            seen.add(metric["metricName"])

        # Cross-check the shipped metric set against the Go registry: same names,
        # types, labels, budgets and histogram buckets, no metric missing on
        # either side.
        _, _, registrations = parse_go_registry(recorder_src)
        contract_by_name = {m["metricName"]: m for m in contract["metrics"]}
        if set(registrations) != set(contract_by_name):
            only_go = set(registrations) - set(contract_by_name)
            only_contract = set(contract_by_name) - set(registrations)
            raise Fail(f"metric name drift: only_go={only_go} only_contract={only_contract}")
        for name, reg in registrations.items():
            spec = contract_by_name[name]
            if reg["type"] != spec["type"]:
                raise Fail(f"{name}: type drift go={reg['type']} contract={spec['type']}")
            if reg["labels"] != spec["requiredLabels"]:
                raise Fail(f"{name}: label drift go={reg['labels']} contract={spec['requiredLabels']}")
            if reg["budget"] != spec["cardinalityBudget"]:
                raise Fail(f"{name}: budget drift go={reg['budget']} contract={spec['cardinalityBudget']}")
            if reg["type"] == "histogram":
                if reg["buckets"] != spec.get("buckets"):
                    raise Fail(f"{name}: bucket drift go={reg['buckets']} contract={spec.get('buckets')}")

        # SLI/SLO/alert graph consistency.
        sli_ids = {s["id"] for s in contract["slis"]}
        for slo in contract["slos"]:
            if slo["sli"] not in sli_ids:
                raise Fail(f"SLO {slo['id']} references undefined SLI {slo['sli']}")
            if slo["status"] not in ("PROPOSED", "APPROVED"):
                raise Fail(f"SLO {slo['id']} has unknown status {slo['status']}")
            if slo["status"] == "APPROVED":
                if slo.get("owner") in (None, "", "UNASSIGNED"):
                    raise Fail(f"SLO {slo['id']} APPROVED without an owner")
                if not slo.get("basedOnData"):
                    raise Fail(f"SLO {slo['id']} APPROVED without supporting data")
            else:
                if slo.get("basedOnData"):
                    raise Fail(f"SLO {slo['id']} is PROPOSED but claims to be based on data")
        for alert in contract["alertCandidates"]:
            if alert["sli"] not in sli_ids:
                raise Fail(f"alert {alert['id']} references undefined SLI {alert['sli']}")
            if alert["routingStatus"] not in ("NOT_CONFIGURED", "CONFIGURED"):
                raise Fail(f"alert {alert['id']} has unknown routingStatus {alert['routingStatus']}")
            if alert["routingStatus"] == "CONFIGURED" and not alert.get("runbook"):
                raise Fail(f"alert {alert['id']} CONFIGURED without a runbook")

        # Every metric alertCandidate must be NOT_CONFIGURED until routing exists.
        alert_by_id = {a["id"]: a for a in contract["alertCandidates"]}
        for metric in contract["metrics"]:
            aid = metric.get("alertCandidate")
            if aid and alert_by_id[aid]["routingStatus"] == "CONFIGURED" \
                    and not contract["readiness"]["alertRoutingConfigured"]:
                raise Fail(f"{metric['metricName']}: alert CONFIGURED but readiness.alertRoutingConfigured is false")

        # Every negative case must be rejected by the same checker.
        negative = load(NEGATIVE)
        for case in negative["cases"]:
            base = set(contract_by_name) if case.get("duplicatesShipped") else set()
            if not check_metric(case["metric"], contract, base):
                raise Fail(f"negative case was not rejected: {case['reason']}")

        # OPS-P0-004 readiness honesty.
        status = load(STATUS)
        gate = next((a for a in status["areas"] if a.get("id") == "OPS-P0-004"), None)
        if gate is None:
            raise Fail("OPS-P0-004 missing from operability status")
        if gate.get("status") == "READY":
            r = contract["readiness"]
            for need in ("exporterImplemented", "scrapeEndpointExposed", "dashboardsDefined",
                         "alertRoutingConfigured", "retentionDefined", "loadCalibrated"):
                if not r.get(need):
                    raise Fail(f"OPS-P0-004 READY but readiness.{need} is false")
        for ref in gate.get("evidenceRefs", []):
            if not (REPO / ref).is_file():
                raise Fail(f"OPS-P0-004 evidence path does not exist: {ref}")
        for ref in contract["evidenceRefs"]:
            if not (REPO / ref).is_file():
                raise Fail(f"contract evidence path does not exist: {ref}")

    except Fail as exc:
        print(f"METRICS VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"METRICS VALIDATION FAILED (unexpected): {exc}", file=sys.stderr)
        return 2

    print("Memory OS metrics contract validation PASS")
    print(f"metrics: {len(contract['metrics'])}  slis: {len(contract['slis'])}  "
          f"slos: {len(contract['slos'])}  alerts: {len(contract['alertCandidates'])}")
    print(f"negative cases rejected: {len(negative['cases'])}")
    print(f"OPS-P0-004 status: {gate.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
