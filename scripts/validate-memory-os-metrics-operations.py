#!/usr/bin/env python3
"""Fail-closed validation for Memory OS metrics operations definitions."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "contracts/operations/metrics-contract.v1.json"
DASHBOARD_PATH = ROOT / "contracts/operations/metrics-dashboard-contract.v1.json"
RETENTION_PATH = ROOT / "contracts/operations/metrics-retention-error-budget-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
ALLOWED_VISUALIZATIONS = {"time_series", "stat", "table", "heatmap"}
FORBIDDEN_QUERY_TOKENS = {
    "account_id", "job_id", "session_id", "request_id", "correlation_id",
    "apple_subject", "email", "ip", "raw_path", "raw_url", "token",
    "authorization", "filename", "object_key", "preview_id", "upload_id",
}
EXPECTED_DASHBOARDS = {
    "memory-os-overview",
    "memory-os-auth-and-abuse",
    "memory-os-dependencies-and-import",
    "memory-os-deletion",
}
EXPECTED_TIERS = {
    "raw-high-resolution": (30, "native_scrape_interval"),
    "five-minute-rollup": (180, "5m"),
    "daily-rollup": (730, "1d"),
}
EXPECTED_BANDS = ["healthy", "watch", "restricted", "exhausted"]
REQUIRED_NON_BUDGETABLE = (
    "cross-tenant",
    "authorization bypass",
    "resurrection",
    "integrity verification bypass",
    "secret or personal-data disclosure",
    "destructive migration",
    "loss of accepted memory data",
)
EXPECTED_EVIDENCE = {
    "contracts/operations/metrics-dashboard-contract.v1.json",
    "contracts/operations/metrics-retention-error-budget-contract.v1.json",
    "scripts/validate-memory-os-metrics-operations.py",
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


def unique_objects(items: Any, key: str, field: str) -> dict[str, dict[str, Any]]:
    require(isinstance(items, list) and items, f"{field} must be a non-empty list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        require(isinstance(item, dict), f"{field} entries must be objects")
        identifier = item.get(key)
        require(isinstance(identifier, str) and identifier,
                f"{field}.{key} is required")
        require(identifier not in result, f"duplicate {field} identifier: {identifier}")
        result[identifier] = item
    return result


def main() -> int:
    metrics = load(METRICS_PATH)
    dashboards = load(DASHBOARD_PATH)
    retention = load(RETENTION_PATH)

    require(dashboards.get("schemaVersion") == "memory-os-metrics-dashboards.v1",
            "dashboard schemaVersion drift")
    require(retention.get("schemaVersion") ==
            "memory-os-metrics-retention-error-budget.v1",
            "retention/error-budget schemaVersion drift")
    require(dashboards.get("sourceMetricsContract") ==
            "contracts/operations/metrics-contract.v1.json",
            "dashboard source contract drift")
    require(retention.get("sourceMetricsContract") ==
            "contracts/operations/metrics-contract.v1.json",
            "retention source contract drift")
    require(dashboards.get("status") == "DEFINED_NOT_CONFIGURED",
            "dashboard configuration status must remain honest")
    require(retention.get("status") == "POLICY_DEFINED_NOT_CONFIGURED",
            "retention configuration status must remain honest")

    metric_names = {item.get("metricName") for item in metrics.get("metrics", [])}
    sli_ids = {item.get("id") for item in metrics.get("slis", [])}
    require(None not in metric_names and metric_names, "primary metrics set is invalid")
    require(None not in sli_ids and sli_ids, "primary SLI set is invalid")

    rules = dashboards.get("rules")
    require(isinstance(rules, dict), "dashboard rules must be an object")
    for flag in (
        "providerNeutral",
        "personalDataForbidden",
        "rawIdentifierVariablesForbidden",
        "loadCalibratedThresholdsRequiredBeforeAlerting",
        "dashboardGreenDoesNotImplyProductionReady",
    ):
        require(rules.get(flag) is True, f"dashboard rules.{flag} must be true")
    require(rules.get("minimumRefreshSeconds") >= 30,
            "dashboard refresh interval is too aggressive")
    max_panels = rules.get("maximumPanelsPerDashboard")
    require(isinstance(max_panels, int) and 1 <= max_panels <= 20,
            "maximumPanelsPerDashboard is invalid")

    dashboard_map = unique_objects(dashboards.get("dashboards"), "id", "dashboards")
    require(set(dashboard_map) == EXPECTED_DASHBOARDS,
            f"dashboard set drift: {sorted(dashboard_map)}")
    panel_ids: set[str] = set()
    for dashboard_id, dashboard in dashboard_map.items():
        require(isinstance(dashboard.get("title"), str) and dashboard["title"],
                f"{dashboard_id}: title is required")
        require(isinstance(dashboard.get("purpose"), str) and dashboard["purpose"],
                f"{dashboard_id}: purpose is required")
        panels = dashboard.get("panels")
        require(isinstance(panels, list) and 1 <= len(panels) <= max_panels,
                f"{dashboard_id}: panel count is invalid")
        for panel in panels:
            require(isinstance(panel, dict), f"{dashboard_id}: panel must be an object")
            panel_id = panel.get("id")
            require(isinstance(panel_id, str) and panel_id,
                    f"{dashboard_id}: panel id is required")
            require(panel_id not in panel_ids, f"duplicate global panel id: {panel_id}")
            panel_ids.add(panel_id)
            require(panel.get("visualization") in ALLOWED_VISUALIZATIONS,
                    f"{panel_id}: unsupported visualization")
            query = panel.get("query")
            require(isinstance(query, str) and 1 <= len(query) <= 1000,
                    f"{panel_id}: query is missing or too long")
            lowered = query.lower()
            for forbidden in FORBIDDEN_QUERY_TOKENS:
                require(forbidden not in lowered,
                        f"{panel_id}: forbidden query token {forbidden}")
            referenced = panel.get("metrics")
            require(isinstance(referenced, list) and referenced,
                    f"{panel_id}: metrics must be a non-empty list")
            require(len(referenced) == len(set(referenced)),
                    f"{panel_id}: duplicate metric reference")
            for metric_name in referenced:
                require(metric_name in metric_names,
                        f"{panel_id}: undefined metric {metric_name}")
                require(metric_name in query,
                        f"{panel_id}: declared metric absent from query: {metric_name}")
            # Every explicit label matcher must be from the bounded primary contract.
            for label in re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=~?\"", query):
                require(label in metrics.get("labelValues", {}),
                        f"{panel_id}: query uses unbounded label {label}")

    dashboard_readiness = dashboards.get("readiness")
    require(isinstance(dashboard_readiness, dict), "dashboard readiness must be an object")
    require(dashboard_readiness.get("dashboardSpecificationsDefined") is True,
            "dashboard specifications are not recorded")
    for unproven in (
        "providerConfigurationGenerated",
        "dashboardDeployed",
        "dataSourceConfigured",
        "thresholdsLoadCalibrated",
        "operatorReviewCompleted",
        "productionReady",
    ):
        require(dashboard_readiness.get(unproven) is False,
                f"unproven dashboard readiness cannot be true: {unproven}")

    privacy = retention.get("privacy")
    require(isinstance(privacy, dict), "retention privacy must be an object")
    require(privacy.get("classification") == "operational_nonpersonal",
            "retention privacy classification drift")
    for flag in (
        "personalDataForbidden",
        "rawIdentifiersForbidden",
        "secretValuesForbidden",
        "incidentExportsMustUseDigestsAndClosedEnums",
    ):
        require(privacy.get(flag) is True, f"retention privacy.{flag} must be true")

    retention_policy = retention.get("retention")
    require(isinstance(retention_policy, dict), "retention policy must be an object")
    require(retention_policy.get("timezone") == "UTC", "retention timezone drift")
    tiers = unique_objects(retention_policy.get("tiers"), "id", "retention tiers")
    require(set(tiers) == set(EXPECTED_TIERS), f"retention tier drift: {sorted(tiers)}")
    previous_days = 0
    for tier_id in ("raw-high-resolution", "five-minute-rollup", "daily-rollup"):
        tier = tiers[tier_id]
        days, resolution = EXPECTED_TIERS[tier_id]
        require(tier.get("retentionDays") == days,
                f"{tier_id}: retention days drift")
        require(tier.get("resolution") == resolution,
                f"{tier_id}: resolution drift")
        require(tier.get("required") is True, f"{tier_id}: must remain required")
        require(days > previous_days, "coarser retention tier must live longer")
        previous_days = days
    require(retention_policy.get("minimumFreshnessCheckMinutes") == 5,
            "freshness check interval drift")
    require(retention_policy.get("maximumAllowedIngestionLagMinutes") == 10,
            "ingestion lag boundary drift")
    for flag in (
        "retentionDeletionVerificationRequired",
        "backendConfigurationCommittedAsCodeRequired",
        "silentRetentionExtensionForbidden",
        "silentRetentionReductionForbidden",
    ):
        require(retention_policy.get(flag) is True,
                f"retention.{flag} must be true")
    require(retention_policy.get("configured") is False,
            "retention backend is not configured")
    require(retention_policy.get("verified") is False,
            "retention deletion is not verified")

    budget = retention.get("errorBudget")
    require(isinstance(budget, dict), "errorBudget must be an object")
    require(budget.get("window") == "30d_rolling", "error-budget window drift")
    require(budget.get("activationStatus") ==
            "INACTIVE_UNTIL_SLO_APPROVED_AND_DATA_VALIDATED",
            "error budget activated without approved SLO/data")
    eligible = budget.get("eligibleSLIs")
    require(isinstance(eligible, list) and eligible,
            "eligibleSLIs must be a non-empty list")
    require(len(eligible) == len(set(eligible)), "eligibleSLIs contains duplicates")
    for sli in eligible:
        require(sli in sli_ids, f"error budget references undefined SLI: {sli}")
    not_budgetable = budget.get("notBudgetable")
    require(isinstance(not_budgetable, list), "notBudgetable must be a list")
    joined = "\n".join(not_budgetable)
    for phrase in REQUIRED_NON_BUDGETABLE:
        require(phrase in joined, f"non-budgetable safety event omitted: {phrase}")
    bands = budget.get("consumptionBands")
    require(isinstance(bands, list), "consumptionBands must be a list")
    require([item.get("id") for item in bands if isinstance(item, dict)] == EXPECTED_BANDS,
            "error-budget band order drift")
    require(bands[0].get("consumedPercentUpperExclusive") == 50,
            "healthy band boundary drift")
    require(bands[1].get("consumedPercentLowerInclusive") == 50 and
            bands[1].get("consumedPercentUpperExclusive") == 75,
            "watch band boundary drift")
    require(bands[2].get("consumedPercentLowerInclusive") == 75 and
            bands[2].get("consumedPercentUpperExclusive") == 100,
            "restricted band boundary drift")
    require(bands[3].get("consumedPercentLowerInclusive") == 100,
            "exhausted band boundary drift")
    require("feature_freeze" in bands[3].get("releasePolicy", ""),
            "exhausted budget must freeze feature releases")
    for flag in (
        "multiWindowBurnAlertsRequired",
        "dataGapPausesBudgetEvaluation",
        "dataGapNeverResetsConsumedBudget",
        "manualBudgetResetForbidden",
        "approvedSloRequired",
        "ownerRequired",
    ):
        require(budget.get(flag) is True, f"errorBudget.{flag} must be true")
    require(budget.get("configured") is False,
            "error budget automation is not configured")
    require(budget.get("verified") is False,
            "error budget automation is not verified")

    change = retention.get("changeControl")
    require(isinstance(change, dict), "changeControl must be an object")
    for flag in (
        "retentionChangeRequiresReview",
        "errorBudgetRuleChangeRequiresReview",
        "exactSourceCommitRequired",
        "rollbackPlanRequired",
        "historicalDataRewriteForbidden",
        "productionDecisionCannotChangeAutomatically",
    ):
        require(change.get(flag) is True, f"changeControl.{flag} must be true")

    operations_readiness = retention.get("readiness")
    require(isinstance(operations_readiness, dict), "operations readiness must be an object")
    require(operations_readiness.get("retentionPolicyDefined") is True,
            "retention policy not recorded")
    require(operations_readiness.get("errorBudgetPolicyDefined") is True,
            "error-budget policy not recorded")
    for unproven in (
        "backendRetentionConfigured",
        "recordingRulesConfigured",
        "approvedSloTargetsExist",
        "burnRateAlertsConfigured",
        "dataFreshnessAlertConfigured",
        "retentionDeletionVerified",
        "operatorReviewCompleted",
        "productionReady",
    ):
        require(operations_readiness.get(unproven) is False,
                f"unproven operations readiness cannot be true: {unproven}")

    evidence = set(dashboards.get("evidenceRefs", [])) | set(retention.get("evidenceRefs", []))
    require(evidence == EXPECTED_EVIDENCE, f"metrics operations evidence drift: {sorted(evidence)}")
    for ref in evidence:
        require((ROOT / ref).is_file(), f"metrics operations evidence missing: {ref}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "metrics operations definitions cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-004"]
    require(len(matches) == 1, "OPS-P0-004 must exist exactly once")
    require(matches[0].get("status") != "READY",
            "definitions alone cannot make OPS-P0-004 READY")

    print("Memory OS metrics operations validation PASS")
    print(f"dashboards: {len(dashboard_map)}  panels: {len(panel_ids)}")
    print(f"retention tiers: {len(tiers)}  eligible SLIs: {len(eligible)}")
    print("configuration state: NOT_CONFIGURED")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"METRICS OPERATIONS VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
