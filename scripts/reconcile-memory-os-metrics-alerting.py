#!/usr/bin/env python3
"""Register validated alert rules/runbooks without claiming routing."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "contracts/operations/metrics-contract.v1.json"
ALERTING_PATH = ROOT / "contracts/operations/metrics-alerting-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"

OLD_GAP = "alert routing, on-call and runbooks"
NEW_EXISTING = (
    "seven provider-neutral Prometheus alert rules bound one-to-one to the primary metrics alert candidates",
    "canonical privacy-safe response runbook covering HTTP 5xx, panic, Apple exchange, rate-limit store, database and deletion alerts",
    "generated Prometheus rule file with stable alert IDs and explicit provisional-threshold labels",
)
NEW_GAP = (
    "production alert routing, paging delivery, on-call ownership, acknowledgement/escalation targets, inhibition rules and delivery/response drills",
)
NEW_REFS = (
    "contracts/operations/metrics-alerting-contract.v1.json",
    "infra/observability/prometheus/memory-os-alerts.yml",
    "docs/runbooks/memory-os-metrics-alerts.md",
    "scripts/validate-memory-os-metrics-alerting.py",
    "scripts/reconcile-memory-os-metrics-alerting.py",
)
NEW_NOTE = (
    "The typed registry, Prometheus exporter, authenticated default-disabled "
    "scrape seam, dashboard specifications, retention/error-budget policy, "
    "seven alert rules and canonical alert runbooks are defined. Production "
    "mounting, external scraping, dashboard/data-source deployment, retention "
    "backend configuration, alert routing/paging/on-call ownership, approved "
    "SLOs, promtool validation and load-calibrated thresholds remain missing. "
    "OPS-P0-004 is PARTIAL, not READY."
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def append_once(items: list[Any], value: str) -> bool:
    if value in items:
        return False
    items.append(value)
    return True


def validate_written_authority() -> None:
    for script in (
        "scripts/validate-memory-os-metrics.py",
        "scripts/validate-memory-os-metrics-alerting.py",
        "scripts/validate-memory-os-operability.py",
    ):
        result = subprocess.run(
            [sys.executable, script],
            cwd=ROOT,
            check=False,
        )
        require(result.returncode == 0, f"post-write validator failed: {script}")


def write_transactionally(metrics: dict[str, Any], status: dict[str, Any]) -> None:
    original_metrics = METRICS_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    try:
        METRICS_PATH.write_text(
            json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        STATUS_PATH.write_text(
            json.dumps(status, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        validate_written_authority()
    except BaseException:
        METRICS_PATH.write_bytes(original_metrics)
        STATUS_PATH.write_bytes(original_status)
        raise


def main() -> int:
    metrics = load(METRICS_PATH)
    alerting = load(ALERTING_PATH)
    readiness = alerting.get("readiness")
    require(isinstance(readiness, dict), "alerting readiness must be an object")
    for field in (
        "ruleDefinitionsComplete",
        "canonicalRunbooksDefined",
        "prometheusRuleFileGenerated",
    ):
        require(readiness.get(field) is True,
                f"alerting foundation not validated: {field}")
    for field in (
        "productionRoutingConfigured",
        "onCallOwnershipConfigured",
        "deliveryVerified",
        "responseDrillCompleted",
        "productionReady",
    ):
        require(readiness.get(field) is False,
                f"unproven alerting readiness cannot be true: {field}")

    rules = alerting.get("rules")
    candidates = metrics.get("alertCandidates")
    require(isinstance(rules, list), "alerting rules must be a list")
    require(isinstance(candidates, list), "primary alertCandidates must be a list")
    rule_by_id = {item.get("alertId"): item for item in rules if isinstance(item, dict)}
    candidate_by_id = {item.get("id"): item for item in candidates if isinstance(item, dict)}
    require(len(rule_by_id) == len(rules), "duplicate or invalid alerting rule")
    require(len(candidate_by_id) == len(candidates), "duplicate or invalid primary candidate")
    require(set(rule_by_id) == set(candidate_by_id), "alert candidate/rule set drift")

    primary_readiness = metrics.get("readiness")
    require(isinstance(primary_readiness, dict), "primary metrics readiness must be an object")
    require(primary_readiness.get("exporterImplemented") is True,
            "metrics exporter foundation must be reconciled first")
    require(primary_readiness.get("dashboardsDefined") is True,
            "dashboard definitions must be reconciled first")
    require(primary_readiness.get("retentionDefined") is True,
            "retention policy must be reconciled first")
    require(primary_readiness.get("alertRoutingConfigured") is False,
            "alert routing remains unconfigured")
    require(primary_readiness.get("loadCalibrated") is False,
            "alert thresholds remain uncalibrated")

    changed = False
    for alert_id, candidate in candidate_by_id.items():
        rule = rule_by_id[alert_id]
        require(candidate.get("sli") == rule.get("sli"), f"{alert_id}: SLI drift")
        require(candidate.get("severity") == rule.get("severity"),
                f"{alert_id}: severity drift")
        require(candidate.get("routingStatus") == "NOT_CONFIGURED",
                f"{alert_id}: routing cannot be configured by reconcile")
        runbook = rule.get("runbook")
        require(isinstance(runbook, str) and runbook,
                f"{alert_id}: runbook binding missing")
        if candidate.get("runbook") != runbook:
            candidate["runbook"] = runbook
            changed = True

    if primary_readiness.get("note") != NEW_NOTE:
        primary_readiness["note"] = NEW_NOTE
        changed = True

    metric_refs = metrics.get("evidenceRefs")
    require(isinstance(metric_refs, list), "primary metrics evidenceRefs must be a list")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"alerting evidence missing: {ref}")
        changed = append_once(metric_refs, ref) or changed

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "alert definitions cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-004"]
    require(len(matches) == 1, "OPS-P0-004 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL",
            "alert definitions cannot alter a non-PARTIAL gate")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-004 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-004 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-004 evidenceRefs must be a list")

    for item in NEW_EXISTING:
        changed = append_once(existing, item) or changed
    if OLD_GAP in missing:
        missing.remove(OLD_GAP)
        changed = True
    for item in NEW_GAP:
        changed = append_once(missing, item) or changed
    for ref in NEW_REFS:
        changed = append_once(refs, ref) or changed

    for required_gap in (
        "production alert routing",
        "load-calibrated histogram buckets",
        "metrics backend retention tiers",
        "production metrics scrape secret provisioning",
    ):
        require(any(required_gap in item for item in missing),
                f"required OPS-P0-004 gap disappeared: {required_gap}")
    require(gate.get("status") == "PARTIAL", "OPS-P0-004 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Metrics alerting authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    write_transactionally(metrics, status)
    print("Registered alert rules and runbooks; routing remains NOT_CONFIGURED and OPS-P0-004 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"METRICS ALERTING RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
