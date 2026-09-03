#!/usr/bin/env python3
"""Register validated alert rules/runbooks without claiming routing."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_METRICS_PATH = ROOT / "contracts/operations/metrics-contract.v1.json"
CANONICAL_ALERTING_PATH = ROOT / "contracts/operations/metrics-alerting-contract.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_METRICS_VALIDATOR = ROOT / "scripts/validate-memory-os-metrics.py"
CANONICAL_ALERTING_VALIDATOR = ROOT / "scripts/validate-memory-os-metrics-alerting.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_ENTRY_DOCS_VALIDATOR = ROOT / "scripts/validate-memory-os-entry-docs.py"
METRICS_PATH = CANONICAL_METRICS_PATH
ALERTING_PATH = CANONICAL_ALERTING_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
METRICS_VALIDATOR = CANONICAL_METRICS_VALIDATOR
ALERTING_VALIDATOR = CANONICAL_ALERTING_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
ENTRY_DOCS_VALIDATOR = CANONICAL_ENTRY_DOCS_VALIDATOR
CANONICAL_OS_REPLACE = os.replace
CANONICAL_SUBPROCESS_RUN = subprocess.run

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


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    mode = path.stat().st_mode & 0o7777
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        CANONICAL_OS_REPLACE(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


CANONICAL_ATOMIC_WRITE_BYTES = atomic_write_bytes


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")
    try:
        resolved = canonical.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise ReconcileFailure(f"canonical {label} cannot be resolved") from exc
    require(resolved == canonical, f"canonical {label} escaped repository path")


def enforce_runtime_authorities(
    expected_replace=CANONICAL_OS_REPLACE,
    expected_subprocess_run=CANONICAL_SUBPROCESS_RUN,
    expected_atomic_writer=CANONICAL_ATOMIC_WRITE_BYTES,
) -> None:
    for path, canonical, label in (
        (METRICS_PATH, CANONICAL_METRICS_PATH, "metrics contract"),
        (ALERTING_PATH, CANONICAL_ALERTING_PATH, "metrics alerting contract"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production operability status"),
        (METRICS_VALIDATOR, CANONICAL_METRICS_VALIDATOR, "metrics validator"),
        (ALERTING_VALIDATOR, CANONICAL_ALERTING_VALIDATOR, "metrics alerting validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
        (ENTRY_DOCS_VALIDATOR, CANONICAL_ENTRY_DOCS_VALIDATOR, "entry docs validator"),
    ):
        require_exact_authority(path, canonical, label)
    require(CANONICAL_OS_REPLACE is expected_replace, "canonical os.replace transport authority drift")
    require(os.replace is expected_replace, "os.replace transport authority drift")
    require(CANONICAL_SUBPROCESS_RUN is expected_subprocess_run, "canonical subprocess transport authority drift")
    require(subprocess.run is expected_subprocess_run, "subprocess transport authority drift")
    require(CANONICAL_ATOMIC_WRITE_BYTES is expected_atomic_writer, "canonical atomic writer authority drift")
    require(atomic_write_bytes is expected_atomic_writer, "atomic writer authority drift")


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


def run_validator(path: Path) -> None:
    enforce_runtime_authorities()
    result = CANONICAL_SUBPROCESS_RUN(
        [sys.executable, str(path)],
        cwd=ROOT,
        check=False,
    )
    require(type(result.returncode) is int and result.returncode == 0,
            f"validator failed: {path.relative_to(ROOT)}")


def validate_source_authority() -> None:
    run_validator(ALERTING_VALIDATOR)


def validate_written_authority() -> None:
    for path in (
        METRICS_VALIDATOR,
        ALERTING_VALIDATOR,
        OPERABILITY_VALIDATOR,
        ENTRY_DOCS_VALIDATOR,
    ):
        run_validator(path)


def write_transactionally(metrics: dict[str, Any], status: dict[str, Any]) -> None:
    enforce_runtime_authorities()
    original_metrics = METRICS_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    metrics_payload = (json.dumps(metrics, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    status_payload = (json.dumps(status, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        CANONICAL_ATOMIC_WRITE_BYTES(METRICS_PATH, metrics_payload)
        CANONICAL_ATOMIC_WRITE_BYTES(STATUS_PATH, status_payload)
        validate_written_authority()
    except BaseException:
        CANONICAL_ATOMIC_WRITE_BYTES(METRICS_PATH, original_metrics)
        CANONICAL_ATOMIC_WRITE_BYTES(STATUS_PATH, original_status)
        raise


def main() -> int:
    enforce_runtime_authorities()
    validate_source_authority()
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
        validate_written_authority()
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
