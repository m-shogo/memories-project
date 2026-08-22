#!/usr/bin/env python3
"""Synchronize validated scrape foundations into the primary metrics contract."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_METRICS_PATH = ROOT / "contracts/operations/metrics-contract.v1.json"
CANONICAL_SCRAPE_PATH = ROOT / "contracts/operations/metrics-scrape-contract.v1.json"
CANONICAL_SCRAPE_VALIDATOR = ROOT / "scripts/validate-memory-os-metrics-scrape.py"
CANONICAL_METRICS_VALIDATOR = ROOT / "scripts/validate-memory-os-metrics.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_ENTRY_DOCS_VALIDATOR = ROOT / "scripts/validate-memory-os-entry-docs.py"
METRICS_PATH = CANONICAL_METRICS_PATH
SCRAPE_PATH = CANONICAL_SCRAPE_PATH
SCRAPE_VALIDATOR = CANONICAL_SCRAPE_VALIDATOR
METRICS_VALIDATOR = CANONICAL_METRICS_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
ENTRY_DOCS_VALIDATOR = CANONICAL_ENTRY_DOCS_VALIDATOR

NEW_DESCRIPTION = (
    "Machine-readable runtime metrics contract for the import-api boundary. "
    "The validator checks this against the Go registry (metric names, types, "
    "required labels, histogram buckets, schema version and per-metric cardinality "
    "budgets), forbids personal or high-cardinality labels, and validates the "
    "SLI/SLO/alert graph. A deterministic Prometheus exporter, authenticated "
    "default-disabled scrape handler and explicit server mount seam now exist "
    "under a separate scrape contract. Production scraping, dashboards, alert "
    "routing, retention and load-calibrated thresholds remain unconfigured, so "
    "OPS-P0-004 remains PARTIAL."
)
NEW_NOTE = (
    "The typed registry and recorder are wired at the HTTP, rate-limit and "
    "deletion-worker boundaries. A deterministic Prometheus exporter, "
    "authenticated scrape handler and explicit default-disabled server mount "
    "seam are implemented and tested. Production runtime mounting, secret "
    "provisioning, private network policy, external scraping, dashboards, alert "
    "routing, retention and load-calibrated buckets/SLO targets remain missing. "
    "OPS-P0-004 is PARTIAL, not READY."
)
NEW_REFS = (
    "contracts/operations/metrics-scrape-contract.v1.json",
    "services/import-api/internal/metrics/prometheus.go",
    "services/import-api/internal/metrics/scrape.go",
    "services/import-api/internal/metrics/prometheus_test.go",
    "services/import-api/internal/httpserver/metrics_scrape_test.go",
    "scripts/validate-memory-os-metrics-scrape.py",
    "scripts/reconcile-memory-os-metrics-contract.py",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")
    try:
        resolved = canonical.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise ReconcileFailure(f"canonical {label} cannot be resolved") from exc
    require(resolved == canonical, f"canonical {label} escaped repository path")


def enforce_runtime_authorities() -> None:
    for path, canonical, label in (
        (METRICS_PATH, CANONICAL_METRICS_PATH, "metrics contract"),
        (SCRAPE_PATH, CANONICAL_SCRAPE_PATH, "metrics scrape contract"),
        (SCRAPE_VALIDATOR, CANONICAL_SCRAPE_VALIDATOR, "metrics scrape validator"),
        (METRICS_VALIDATOR, CANONICAL_METRICS_VALIDATOR, "metrics validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
        (ENTRY_DOCS_VALIDATOR, CANONICAL_ENTRY_DOCS_VALIDATOR, "entry docs validator"),
    ):
        require_exact_authority(path, canonical, label)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {path.relative_to(ROOT)}")
    return value


def load_validator(path: Path, name: str):
    enforce_runtime_authorities()
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load validator: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require_validator_success(path: Path, name: str) -> None:
    enforce_runtime_authorities()
    result = load_validator(path, name).main()
    require(
        not isinstance(result, bool) and isinstance(result, int) and result == 0,
        f"validator rejected authority: {path.relative_to(ROOT)} returned {result!r}",
    )


def validate_source_authority() -> None:
    require_validator_success(SCRAPE_VALIDATOR, "memory_os_metrics_scrape_validator")


def validate_written_authority() -> None:
    require_validator_success(METRICS_VALIDATOR, "memory_os_metrics_validator")
    require_validator_success(SCRAPE_VALIDATOR, "memory_os_metrics_scrape_validator_postwrite")
    require_validator_success(OPERABILITY_VALIDATOR, "memory_os_operability_validator")
    require_validator_success(ENTRY_DOCS_VALIDATOR, "memory_os_entry_docs_validator")


def write_transactionally(metrics: dict[str, Any]) -> None:
    enforce_runtime_authorities()
    original = METRICS_PATH.read_bytes()
    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        validate_written_authority()
    except BaseException:
        METRICS_PATH.write_bytes(original)
        raise


def main() -> int:
    enforce_runtime_authorities()
    validate_source_authority()

    metrics = load(METRICS_PATH)
    scrape = load(SCRAPE_PATH)
    require(metrics.get("schemaVersion") == "memory-os-metrics.v1",
            "primary metrics schema drift")
    require(scrape.get("schemaVersion") == "memory-os-metrics-scrape.v1",
            "scrape contract schema drift")

    scrape_readiness = scrape.get("readiness")
    require(isinstance(scrape_readiness, dict), "scrape readiness must be an object")
    for field in (
        "prometheusExporterImplemented",
        "authenticatedHandlerImplemented",
        "serverMountSupported",
    ):
        require(scrape_readiness.get(field) is True,
                f"scrape foundation not validated: {field}")
    require(scrape_readiness.get("runtimeMounted") is False,
            "primary contract reconcile cannot claim production runtime mounting")
    require(scrape_readiness.get("productionReady") is False,
            "primary contract reconcile cannot claim production readiness")

    readiness = metrics.get("readiness")
    require(isinstance(readiness, dict), "primary metrics readiness must be an object")
    changed = False
    if metrics.get("description") != NEW_DESCRIPTION:
        metrics["description"] = NEW_DESCRIPTION
        changed = True
    if readiness.get("exporterImplemented") is not True:
        readiness["exporterImplemented"] = True
        changed = True
    require(readiness.get("scrapeEndpointExposed") is False,
            "production scrape endpoint must remain unexposed")
    if readiness.get("note") != NEW_NOTE:
        readiness["note"] = NEW_NOTE
        changed = True

    refs = metrics.get("evidenceRefs")
    require(isinstance(refs, list), "primary metrics evidenceRefs must be a list")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"metrics evidence path missing: {ref}")
        if ref not in refs:
            refs.append(ref)
            changed = True

    for field in (
        "scrapeEndpointExposed",
        "alertRoutingConfigured",
        "loadCalibrated",
    ):
        require(readiness.get(field) is False,
                f"unproven metrics readiness cannot be true: {field}")

    if not changed:
        validate_written_authority()
        print("Primary metrics contract already reconciled")
        return 0

    write_transactionally(metrics)
    print("Registered exporter foundation in primary metrics contract")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"METRICS CONTRACT RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
