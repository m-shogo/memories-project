#!/usr/bin/env python3
"""Register validated metrics scrape foundations without changing readiness."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CONTRACT_PATH = ROOT / "contracts/operations/metrics-scrape-contract.v1.json"

OLD_MISSING = "Prometheus/OTel exporter and an exposed scrape endpoint"
NEW_EXISTING = (
    "deterministic concurrency-safe Prometheus text exporter with TYPE directives and mandatory histogram +Inf buckets",
    "fail-closed bearer-authenticated metrics scrape handler with constant-time digest comparison, no-store/nosniff responses and a bounded snapshot size",
    "explicit default-disabled HTTP server metrics mount seam isolated from public API rate-limit buckets while remaining inside privacy-safe request observability",
)
NEW_MISSING = (
    "production metrics scrape secret provisioning, private operational network policy and deliberate runtime mount",
    "external Prometheus/OTel scraper integration and scrape availability monitoring",
)
NEW_REFS = (
    "contracts/operations/metrics-scrape-contract.v1.json",
    "services/import-api/internal/metrics/prometheus.go",
    "services/import-api/internal/metrics/scrape.go",
    "services/import-api/internal/metrics/prometheus_test.go",
    "services/import-api/internal/httpserver/server.go",
    "services/import-api/internal/httpserver/metrics_scrape_test.go",
    "scripts/validate-memory-os-metrics-scrape.py",
    "scripts/reconcile-memory-os-metrics-scrape-status.py",
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


def main() -> int:
    contract = load(CONTRACT_PATH)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "scrape readiness must be an object")
    for implemented in (
        "prometheusExporterImplemented",
        "authenticatedHandlerImplemented",
        "serverMountSupported",
    ):
        require(readiness.get(implemented) is True,
                f"scrape foundation not validated: {implemented}")
    require(readiness.get("runtimeMounted") is False,
            "reconcile is only for an unmounted production scrape boundary")
    require(readiness.get("productionReady") is False,
            "reconcile cannot register a production-ready claim")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "reconcile requires productionDecision NO_GO")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-004"]
    require(len(matches) == 1, "OPS-P0-004 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL",
            "scrape foundation cannot alter a non-PARTIAL metrics gate")

    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-004 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-004 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-004 evidenceRefs must be a list")

    changed = False
    for item in NEW_EXISTING:
        if item not in existing:
            existing.append(item)
            changed = True
    if OLD_MISSING in missing:
        missing.remove(OLD_MISSING)
        changed = True
    for item in NEW_MISSING:
        if item not in missing:
            missing.append(item)
            changed = True
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"scrape evidence path missing: {ref}")
        if ref not in refs:
            refs.append(ref)
            changed = True

    for required_gap in (
        "production metrics scrape secret provisioning",
        "external Prometheus/OTel scraper integration",
        "dashboards and load-calibrated",
        "alert routing",
        "metrics retention policy",
    ):
        require(any(required_gap in item for item in missing),
                f"required OPS-P0-004 gap disappeared: {required_gap}")

    require(gate.get("status") == "PARTIAL", "metrics readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Metrics scrape status already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Registered metrics scrape foundations; OPS-P0-004 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"METRICS SCRAPE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
