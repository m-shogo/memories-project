#!/usr/bin/env python3
"""Register validated metrics scrape foundations without changing readiness."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/metrics-scrape-contract.v1.json"
CANONICAL_SCRAPE_VALIDATOR = ROOT / "scripts/validate-memory-os-metrics-scrape.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_ENTRY_DOCS_VALIDATOR = ROOT / "scripts/validate-memory-os-entry-docs.py"
STATUS_PATH = CANONICAL_STATUS_PATH
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
SCRAPE_VALIDATOR = CANONICAL_SCRAPE_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
ENTRY_DOCS_VALIDATOR = CANONICAL_ENTRY_DOCS_VALIDATOR

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
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production operability status"),
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "metrics scrape contract"),
        (SCRAPE_VALIDATOR, CANONICAL_SCRAPE_VALIDATOR, "metrics scrape validator"),
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


def validate_written_authority() -> None:
    require_validator_success(SCRAPE_VALIDATOR, "memory_os_metrics_scrape_validator")
    require_validator_success(OPERABILITY_VALIDATOR, "memory_os_operability_validator")
    require_validator_success(ENTRY_DOCS_VALIDATOR, "memory_os_entry_docs_validator")


def write_transactionally(status: dict[str, Any]) -> None:
    enforce_runtime_authorities()
    original = STATUS_PATH.read_bytes()
    STATUS_PATH.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        validate_written_authority()
    except BaseException:
        STATUS_PATH.write_bytes(original)
        raise


def has_gap(missing: list[Any], aliases: tuple[str, ...]) -> bool:
    return any(
        isinstance(item, str) and any(alias in item for alias in aliases)
        for item in missing
    )


def main() -> int:
    enforce_runtime_authorities()
    validate_written_authority()

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

    required_gap_groups = (
        ("production metrics scrape secret provisioning",),
        ("external Prometheus/OTel scraper integration",),
        ("dashboards and load-calibrated", "provider dashboard generation/deployment"),
        ("alert routing", "production alert routing"),
        ("metrics retention policy", "metrics backend retention tiers"),
    )
    for aliases in required_gap_groups:
        require(has_gap(missing, aliases),
                f"required OPS-P0-004 gap disappeared: {aliases[0]}")

    require(gate.get("status") == "PARTIAL", "metrics readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        validate_written_authority()
        print("Metrics scrape status already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    write_transactionally(status)
    print("Registered metrics scrape foundations; OPS-P0-004 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"METRICS SCRAPE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
