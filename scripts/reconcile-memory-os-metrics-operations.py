#!/usr/bin/env python3
"""Register validated metrics operations definitions without claiming deployment."""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "contracts/operations/metrics-contract.v1.json"
DASHBOARD_PATH = ROOT / "contracts/operations/metrics-dashboard-contract.v1.json"
RETENTION_PATH = ROOT / "contracts/operations/metrics-retention-error-budget-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"

OLD_DASHBOARD_GAP = (
    "dashboards and load-calibrated histogram buckets and SLO targets "
    "(depends on OPS-P0-006)"
)
OLD_RETENTION_GAP = "metrics retention policy and an error-budget policy"
NEW_EXISTING = (
    "four provider-neutral operational dashboard specifications covering service overview, authentication/abuse, dependencies/import and deletion safety",
    "binding privacy-safe metrics retention tiers (30-day native, 180-day five-minute and 730-day daily rollups) with change-control requirements",
    "error-budget policy with approved-SLO activation gates, data-gap safety and non-budgetable security, integrity, deletion-resurrection and data-loss events",
)
NEW_MISSING = (
    "provider dashboard generation/deployment, metrics data-source wiring and operator review",
    "load-calibrated histogram buckets and approved SLO targets (depends on OPS-P0-006)",
    "metrics backend retention tiers, recording rules, ingestion freshness monitoring and retention-deletion verification",
    "error-budget burn-rate automation remains inactive until SLO approval, owner assignment and validated production data",
)
NEW_REFS = (
    "contracts/operations/metrics-dashboard-contract.v1.json",
    "contracts/operations/metrics-retention-error-budget-contract.v1.json",
    "scripts/validate-memory-os-metrics-operations.py",
    "scripts/reconcile-memory-os-metrics-operations.py",
)
NEW_NOTE = (
    "The typed registry, deterministic Prometheus exporter, authenticated "
    "default-disabled scrape mount seam, four provider-neutral dashboard "
    "specifications, retention tiers and error-budget policy are defined. "
    "Production mounting, secret/network provisioning, external scraping, "
    "dashboard/data-source deployment, retention backend configuration, alert "
    "routing, approved SLOs and load-calibrated thresholds remain missing. "
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
        "scripts/validate-memory-os-metrics-operations.py",
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
    dashboards = load(DASHBOARD_PATH)
    retention = load(RETENTION_PATH)

    dashboard_readiness = dashboards.get("readiness")
    require(isinstance(dashboard_readiness, dict), "dashboard readiness must be an object")
    require(dashboard_readiness.get("dashboardSpecificationsDefined") is True,
            "dashboard specifications are not validated")
    require(dashboard_readiness.get("dashboardDeployed") is False,
            "dashboard deployment cannot be claimed by this reconcile")
    require(dashboard_readiness.get("productionReady") is False,
            "dashboard contract cannot be production-ready")

    operations_readiness = retention.get("readiness")
    require(isinstance(operations_readiness, dict), "operations readiness must be an object")
    require(operations_readiness.get("retentionPolicyDefined") is True,
            "retention policy is not validated")
    require(operations_readiness.get("errorBudgetPolicyDefined") is True,
            "error-budget policy is not validated")
    require(operations_readiness.get("backendRetentionConfigured") is False,
            "retention backend cannot be claimed by this reconcile")
    require(operations_readiness.get("productionReady") is False,
            "metrics operations contract cannot be production-ready")

    readiness = metrics.get("readiness")
    require(isinstance(readiness, dict), "primary metrics readiness must be an object")
    require(readiness.get("exporterImplemented") is True,
            "exporter foundation must be reconciled first")
    require(readiness.get("scrapeEndpointExposed") is False,
            "production scrape endpoint must remain unexposed")
    require(readiness.get("alertRoutingConfigured") is False,
            "alert routing remains unconfigured")
    require(readiness.get("loadCalibrated") is False,
            "load calibration remains unproven")

    changed = False
    if readiness.get("dashboardsDefined") is not True:
        readiness["dashboardsDefined"] = True
        changed = True
    if readiness.get("retentionDefined") is not True:
        readiness["retentionDefined"] = True
        changed = True
    if readiness.get("note") != NEW_NOTE:
        readiness["note"] = NEW_NOTE
        changed = True

    metric_refs = metrics.get("evidenceRefs")
    require(isinstance(metric_refs, list), "primary metrics evidenceRefs must be a list")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"metrics operations evidence missing: {ref}")
        changed = append_once(metric_refs, ref) or changed

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "metrics definitions cannot change productionDecision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-004"]
    require(len(matches) == 1, "OPS-P0-004 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL",
            "metrics definitions cannot alter a non-PARTIAL gate")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    status_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-004 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-004 missingEvidence must be a list")
    require(isinstance(status_refs, list), "OPS-P0-004 evidenceRefs must be a list")

    for evidence in NEW_EXISTING:
        changed = append_once(existing, evidence) or changed
    for obsolete in (OLD_DASHBOARD_GAP, OLD_RETENTION_GAP):
        if obsolete in missing:
            missing.remove(obsolete)
            changed = True
    for gap in NEW_MISSING:
        changed = append_once(missing, gap) or changed
    for ref in NEW_REFS:
        changed = append_once(status_refs, ref) or changed

    for required_gap in (
        "production metrics scrape secret provisioning",
        "external Prometheus/OTel scraper integration",
        "provider dashboard generation/deployment",
        "load-calibrated histogram buckets",
        "metrics backend retention tiers",
        "error-budget burn-rate automation",
        "alert routing",
    ):
        require(any(required_gap in item for item in missing),
                f"required OPS-P0-004 gap disappeared: {required_gap}")

    require(gate.get("status") == "PARTIAL", "OPS-P0-004 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Metrics operations authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    write_transactionally(metrics, status)
    print("Registered dashboard, retention and error-budget definitions; OPS-P0-004 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"METRICS OPERATIONS RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
