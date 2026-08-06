#!/usr/bin/env python3
"""Fail-closed validation for the Memory OS Prometheus scrape foundation."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/metrics-scrape-contract.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
EXPECTED_EVIDENCE = {
    "services/import-api/internal/metrics/prometheus.go",
    "services/import-api/internal/metrics/scrape.go",
    "services/import-api/internal/metrics/prometheus_test.go",
    "scripts/validate-memory-os-metrics-scrape.py",
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


def source(path: str) -> str:
    target = ROOT / path
    require(target.is_file(), f"missing source: {path}")
    return target.read_text(encoding="utf-8")


def contains_all(text: str, snippets: tuple[str, ...], name: str) -> None:
    for snippet in snippets:
        require(snippet in text, f"{name} missing required boundary: {snippet}")


def main() -> int:
    contract = load(CONTRACT_PATH)
    require(contract.get("schemaVersion") == "memory-os-metrics-scrape.v1",
            "unsupported metrics scrape schemaVersion")

    implementation = contract.get("implementation")
    require(isinstance(implementation, dict), "implementation must be an object")
    require(implementation.get("prometheusExporter") ==
            "services/import-api/internal/metrics/prometheus.go",
            "prometheus exporter path drift")
    require(implementation.get("scrapeHandler") ==
            "services/import-api/internal/metrics/scrape.go",
            "scrape handler path drift")
    require(implementation.get("tests") ==
            "services/import-api/internal/metrics/prometheus_test.go",
            "scrape tests path drift")
    require(implementation.get("validator") ==
            "scripts/validate-memory-os-metrics-scrape.py",
            "validator path drift")

    format_contract = contract.get("format")
    require(isinstance(format_contract, dict), "format must be an object")
    require(format_contract.get("protocol") == "PROMETHEUS_TEXT", "protocol drift")
    require(format_contract.get("version") == "0.0.4", "text format version drift")
    require(format_contract.get("contentType") ==
            "text/plain; version=0.0.4; charset=utf-8",
            "content type drift")
    for flag in (
        "typeDirectivesRequired",
        "histogramPositiveInfinityBucketRequired",
        "deterministicMetricOrderingRequired",
        "deterministicSeriesOrderingRequired",
        "concurrentSnapshotRequired",
    ):
        require(format_contract.get(flag) is True, f"format.{flag} must be true")

    access = contract.get("accessBoundary")
    require(isinstance(access, dict), "accessBoundary must be an object")
    require(access.get("runtimeMounted") is False,
            "scrape endpoint is not yet mounted in the runtime")
    require(access.get("defaultDisabled") is True, "scrape handler must default disabled")
    require(access.get("authentication") == "BEARER_TOKEN", "authentication drift")
    require(access.get("minimumTokenLength") == 32, "minimum token length drift")
    require(access.get("maximumTokenLength") == 256, "maximum token length drift")
    require(access.get("constantTimeDigestComparisonRequired") is True,
            "constant-time digest comparison must remain required")
    require(access.get("allowedMethods") == ["GET"], "allowed method drift")
    require(access.get("cacheControl") == "no-store", "cache control drift")
    require(access.get("contentTypeOptions") == "nosniff", "nosniff drift")
    require(access.get("maximumResponseBytesDefault") == 4 << 20,
            "default response bound drift")
    require(access.get("maximumResponseBytesCeiling") == 16 << 20,
            "response ceiling drift")
    require(access.get("unauthenticatedStatus") == 401, "unauthenticated status drift")
    require(access.get("wrongMethodStatus") == 405, "method status drift")
    require(access.get("oversizedSnapshotStatus") == 503, "oversize status drift")

    privacy = contract.get("privacy")
    require(isinstance(privacy, dict), "privacy must be an object")
    require(privacy.get("classification") == "operational_nonpersonal",
            "privacy classification drift")
    for flag in (
        "rawRequestValuesForbidden",
        "requestIdForbidden",
        "accountIdForbidden",
        "jobIdForbidden",
        "sessionIdForbidden",
        "rawPathForbidden",
        "rawUrlForbidden",
        "ipForbidden",
        "authorizationHeaderForbidden",
        "scrapeTokenLoggingForbidden",
        "scrapeTokenMetricLabelForbidden",
    ):
        require(privacy.get(flag) is True, f"privacy.{flag} must be true")

    exporter_source = source(implementation["prometheusExporter"])
    contains_all(exporter_source, (
        "func (r *Registry) Prometheus() string",
        "r.mu.Lock()",
        "defer r.mu.Unlock()",
        "sort.Strings(names)",
        "sort.Strings(seriesKeys)",
        '"# TYPE %s %s\\n"',
        '"le", "+Inf"',
        "prometheusEscape",
    ), "prometheus exporter")

    scrape_source = source(implementation["scrapeHandler"])
    contains_all(scrape_source, (
        "minimumScrapeTokenLength = 32",
        "maximumScrapeTokenLength = 256",
        "defaultScrapeMaxBytes    = 4 << 20",
        "sha256.Sum256",
        "subtle.ConstantTimeCompare",
        'Set("Cache-Control", "no-store")',
        'Set("X-Content-Type-Options", "nosniff")',
        'Set("WWW-Authenticate", `Bearer realm="metrics"`)',
        "request.Method != http.MethodGet",
        "len(payload) > maxBytes",
        "http.StatusServiceUnavailable",
    ), "scrape handler")
    for forbidden in ("log.Print", "fmt.Printf", "slog.", "logger."):
        require(forbidden not in scrape_source,
                f"scrape handler contains a logging path: {forbidden}")

    test_source = source(implementation["tests"])
    contains_all(test_source, (
        "CANARY_JOB_123",
        "CANARY_TOKEN",
        "TestNewScrapeHandlerFailsClosed",
        "TestScrapeHandlerAuthenticationAndHeaders",
        "TestScrapeHandlerRejectsOversizedSnapshot",
        'le=\\"+Inf\\"',
    ), "scrape tests")

    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "readiness must be an object")
    require(readiness.get("prometheusExporterImplemented") is True,
            "Prometheus exporter implementation not recorded")
    require(readiness.get("authenticatedHandlerImplemented") is True,
            "authenticated handler implementation not recorded")
    for unproven in (
        "runtimeMounted",
        "productionSecretProvisioned",
        "privateNetworkPolicyDefined",
        "externalScraperConfigured",
        "dashboardConfigured",
        "retentionConfigured",
        "alertRoutingConfigured",
        "productionReady",
    ):
        require(readiness.get(unproven) is False,
                f"unproven scrape readiness cannot be true: {unproven}")

    refs = contract.get("evidenceRefs")
    require(isinstance(refs, list), "evidenceRefs must be a list")
    require(len(refs) == len(set(refs)), "evidenceRefs contains duplicates")
    require(set(refs) == EXPECTED_EVIDENCE, f"evidenceRefs drift: {refs}")
    for ref in refs:
        require((ROOT / ref).is_file(), f"evidence path missing: {ref}")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "scrape foundation cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-004"]
    require(len(matches) == 1, "OPS-P0-004 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") != "READY",
            "OPS-P0-004 cannot be READY while scrape runtime and operations are unconfigured")

    print("Memory OS metrics scrape validation PASS")
    print("Prometheus exporter: implemented")
    print("authenticated scrape handler: implemented, deliberately unmounted")
    print(f"OPS-P0-004 status: {gate.get('status')}")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationFailure as exc:
        print(f"METRICS SCRAPE VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
