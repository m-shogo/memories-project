#!/usr/bin/env python3
"""Fail-closed validation for Memory OS metrics alert definitions."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "contracts/operations/metrics-contract.v1.json"
ALERTING_PATH = ROOT / "contracts/operations/metrics-alerting-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_ALERT_IDS = {
    "alert_http_5xx_burst",
    "alert_panic_detected",
    "alert_apple_exchange_failure_spike",
    "alert_rate_limit_store_failing",
    "alert_db_failing",
    "alert_deletion_backlog_stuck",
    "alert_deletion_terminal_failure",
}
EXPECTED_EVIDENCE = {
    "contracts/operations/metrics-alerting-contract.v1.json",
    "infra/observability/prometheus/memory-os-alerts.yml",
    "docs/runbooks/memory-os-metrics-alerts.md",
    "scripts/validate-memory-os-metrics-alerting.py",
}
ALLOWED_SEVERITIES = {"medium", "high"}
ALLOWED_THRESHOLD_STATUSES = {
    "PROVISIONAL_NOT_LOAD_CALIBRATED",
    "INVARIANT_ANY_OCCURRENCE",
    "PROVISIONAL_ZERO_TOLERANCE_PENDING_BASELINE",
    "PROVISIONAL_POLICY_WINDOW",
}
FORBIDDEN_TOKENS = {
    "account_id", "job_id", "session_id", "request_id", "correlation_id",
    "apple_subject", "email", "ip_digest", "network_digest", "raw_url",
    "raw_path", "bearer", "authorization", "filename", "object_key",
    "preview_id", "upload_id",
}


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def main() -> int:
    metrics = load(METRICS_PATH)
    alerting = load(ALERTING_PATH)
    require(alerting.get("schemaVersion") == "memory-os-metrics-alerting.v1",
            "alerting schemaVersion drift")
    require(alerting.get("sourceMetricsContract") ==
            "contracts/operations/metrics-contract.v1.json",
            "alerting source contract drift")
    require(alerting.get("prometheusRuleFile") ==
            "infra/observability/prometheus/memory-os-alerts.yml",
            "Prometheus rule path drift")
    require(alerting.get("canonicalRunbook") ==
            "docs/runbooks/memory-os-metrics-alerts.md",
            "canonical runbook path drift")
    require(alerting.get("status") == "RULES_DEFINED_ROUTING_NOT_CONFIGURED",
            "alerting status must remain honest")

    primary_candidates = metrics.get("alertCandidates")
    require(isinstance(primary_candidates, list), "primary alertCandidates must be a list")
    primary_by_id: dict[str, dict[str, Any]] = {}
    for candidate in primary_candidates:
        require(isinstance(candidate, dict), "primary alert candidate must be an object")
        alert_id = candidate.get("id")
        require(isinstance(alert_id, str) and alert_id,
                "primary alert candidate id is required")
        require(alert_id not in primary_by_id, f"duplicate primary alert id: {alert_id}")
        primary_by_id[alert_id] = candidate
    require(set(primary_by_id) == EXPECTED_ALERT_IDS,
            f"primary alert set drift: {sorted(primary_by_id)}")

    metric_names = {item.get("metricName") for item in metrics.get("metrics", [])}
    sli_ids = {item.get("id") for item in metrics.get("slis", [])}
    require(None not in metric_names and metric_names, "primary metric set invalid")
    require(None not in sli_ids and sli_ids, "primary SLI set invalid")

    rules = alerting.get("rules")
    require(isinstance(rules, list) and rules, "alert rules must be a non-empty list")
    rules_by_id: dict[str, dict[str, Any]] = {}
    prometheus_names: set[str] = set()
    for rule in rules:
        require(isinstance(rule, dict), "alert rule must be an object")
        alert_id = rule.get("alertId")
        require(alert_id in EXPECTED_ALERT_IDS, f"unknown alert rule id: {alert_id}")
        require(alert_id not in rules_by_id, f"duplicate alert rule id: {alert_id}")
        rules_by_id[alert_id] = rule
        prometheus_name = rule.get("prometheusAlertName")
        require(isinstance(prometheus_name, str) and
                re.fullmatch(r"MemoryOS[A-Za-z0-9]+", prometheus_name),
                f"{alert_id}: invalid Prometheus alert name")
        require(prometheus_name not in prometheus_names,
                f"duplicate Prometheus alert name: {prometheus_name}")
        prometheus_names.add(prometheus_name)
        require(rule.get("sli") == primary_by_id[alert_id].get("sli"),
                f"{alert_id}: SLI drift from primary contract")
        require(rule.get("sli") in sli_ids, f"{alert_id}: undefined SLI")
        require(rule.get("severity") == primary_by_id[alert_id].get("severity"),
                f"{alert_id}: severity drift from primary contract")
        require(rule.get("severity") in ALLOWED_SEVERITIES,
                f"{alert_id}: unsupported severity")
        require(rule.get("routingStatus") == "NOT_CONFIGURED",
                f"{alert_id}: routing is not configured")
        require(rule.get("thresholdStatus") in ALLOWED_THRESHOLD_STATUSES,
                f"{alert_id}: threshold honesty missing")
        expression = rule.get("expression")
        require(isinstance(expression, str) and 1 <= len(expression) <= 1200,
                f"{alert_id}: expression missing or too long")
        for forbidden in FORBIDDEN_TOKENS:
            require(forbidden not in expression.lower(),
                    f"{alert_id}: forbidden query token {forbidden}")
        referenced = {name for name in metric_names if name in expression}
        require(referenced, f"{alert_id}: expression references no registered metric")
        duration = rule.get("for")
        require(isinstance(duration, str) and re.fullmatch(r"\d+[smh]", duration),
                f"{alert_id}: invalid hold duration")
        runbook = rule.get("runbook")
        require(isinstance(runbook, str) and runbook.startswith(
            "docs/runbooks/memory-os-metrics-alerts.md#alert-"),
            f"{alert_id}: canonical runbook binding missing")

    require(set(rules_by_id) == EXPECTED_ALERT_IDS,
            f"alerting rule set drift: {sorted(rules_by_id)}")

    routing = alerting.get("routing")
    require(isinstance(routing, dict), "routing must be an object")
    require(routing.get("configured") is False, "routing is not configured")
    require(routing.get("silenceGovernanceDefined") is True,
            "silence governance must be defined")
    for unproven in (
        "pagingDestinationConfigured",
        "onCallOwnerAssigned",
        "acknowledgementTargetDefined",
        "escalationTimerDefined",
        "inhibitionRulesDefined",
        "deliveryTestCompleted",
        "responseDrillCompleted",
    ):
        require(routing.get(unproven) is False,
                f"unproven routing field cannot be true: {unproven}")

    safety = alerting.get("safety")
    require(isinstance(safety, dict), "safety must be an object")
    for flag in (
        "personalLabelsForbidden",
        "rawIdentifiersForbidden",
        "secretAnnotationsForbidden",
        "everyRuleRequiresRunbook",
        "everyRuleRequiresStableAlertId",
        "provisionalThresholdsCannotApproveSlo",
        "missingMetricsMustNotResolveSafetyIncidents",
        "routingConfigurationCannotChangeProductionDecision",
    ):
        require(safety.get(flag) is True, f"safety.{flag} must be true")

    readiness = alerting.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    for foundation in (
        "ruleDefinitionsComplete",
        "canonicalRunbooksDefined",
        "prometheusRuleFileGenerated",
    ):
        require(readiness.get(foundation) is True,
                f"readiness.{foundation} must be true")
    for unproven in (
        "promtoolValidationCompleted",
        "productionRoutingConfigured",
        "onCallOwnershipConfigured",
        "deliveryVerified",
        "responseDrillCompleted",
        "operatorReviewCompleted",
        "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven alert readiness cannot be true: {unproven}")

    rule_path = ROOT / alerting["prometheusRuleFile"]
    runbook_path = ROOT / alerting["canonicalRunbook"]
    require(rule_path.is_file(), "Prometheus rule file missing")
    require(runbook_path.is_file(), "metrics alert runbook missing")
    rule_text = rule_path.read_text(encoding="utf-8")
    runbook_text = runbook_path.read_text(encoding="utf-8")
    for alert_id, rule in rules_by_id.items():
        for required in (
            f"alert: {rule['prometheusAlertName']}",
            f"alert_id: {alert_id}",
            f"severity: {rule['severity']}",
            f"for: {rule['for']}",
            rule["runbook"],
        ):
            require(required in rule_text,
                    f"{alert_id}: generated rule file missing {required!r}")
        anchor_heading = "## " + alert_id.replace("_", "-")
        require(anchor_heading in runbook_text,
                f"{alert_id}: runbook heading missing: {anchor_heading}")
        require(rule["runbook"].split("#", 1)[1] in rule_text,
                f"{alert_id}: rule file runbook anchor drift")
    for forbidden in FORBIDDEN_TOKENS | {"password", "private_key", "client_secret"}:
        require(forbidden not in rule_text.lower(),
                f"generated alert rules contain forbidden token: {forbidden}")

    for required_runbook_phrase in (
        "Production decision remains: **NO_GO**",
        "A dashboard or alert returning to green does not prove data integrity",
        "Do not silence an alert without an owner, expiry, reason and follow-up issue",
        "No production Prometheus/Alertmanager or equivalent is configured",
        "No alert delivery or response drill has been completed",
    ):
        require(required_runbook_phrase in runbook_text,
                f"runbook missing binding phrase: {required_runbook_phrase}")

    refs = alerting.get("evidenceRefs")
    require(isinstance(refs, list) and len(refs) == len(set(refs)),
            "alerting evidenceRefs invalid")
    require(set(refs) == EXPECTED_EVIDENCE, f"alerting evidence drift: {refs}")
    for ref in refs:
        require((ROOT / ref).is_file(), f"alerting evidence path missing: {ref}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "alert definitions cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-004"]
    require(len(matches) == 1, "OPS-P0-004 must exist exactly once")
    require(matches[0].get("status") != "READY",
            "rules/runbooks without routing cannot make OPS-P0-004 READY")

    print("Memory OS metrics alerting validation PASS")
    print(f"alert rules: {len(rules_by_id)}")
    print("routing: NOT_CONFIGURED")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"METRICS ALERTING VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
