#!/usr/bin/env python3
"""Register exact-source v2 API/parser/object outage evidence conservatively."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/chaos-failure-drill-results.v2.sample.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_RECONCILER = ROOT / "scripts/reconcile-memory-os-chaos-authority.py"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

NEW_EXISTING = (
    "local PostgreSQL 16 plus MinIO import-flow outage drill proving an unreachable object-store endpoint fails before parse/commit, leaves no Preview or spool residue and the exact same request succeeds once connectivity returns",
    "v2 machine-readable failure-drill authority superseding the two-scenario v1 inventory while preserving CI-vs-production evidence separation",
)
REMOVE_MISSING = (
    "object-store outage drill",
)
NEW_MISSING = (
    "production-shaped object-store process outage or network-partition drill with TLS, scoped credentials, lifecycle controls and recovery verification",
)
NEW_REFS = (
    "contracts/operations/chaos-failure-drill-contract.v2.json",
    "docs/fixtures/memory-os-operability/chaos-failure-drill-results.v2.sample.json",
    "services/import-api/internal/importflow/object_outage_drill_linux_test.go",
    "scripts/validate-memory-os-chaos-failure-drills-v2.py",
    "scripts/reconcile-memory-os-chaos-failure-drills-v2.py",
    ".github/workflows/chaos-failure-drills-v2.yml",
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


def load_canonical_normalizer():
    require(CANONICAL_RECONCILER.is_file(), "canonical chaos authority reconciler missing")
    spec = importlib.util.spec_from_file_location("memory_os_canonical_chaos_authority_v2", CANONICAL_RECONCILER)
    require(spec is not None and spec.loader is not None, "cannot load canonical chaos authority reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    normalizer = getattr(module, "normalized_status", None)
    require(callable(normalizer), "canonical chaos authority reconciler missing normalized_status")
    return normalizer


def source_is_ancestor(source_sha: str) -> bool:
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_sha, "HEAD"],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def main() -> int:
    result = load(RESULT_PATH)
    require(result.get("schemaVersion") == "memory-os-chaos-failure-drill-results.v2",
            "v2 result schemaVersion drift")
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and SHA_RE.fullmatch(source_sha) is not None,
            "v2 result source SHA is invalid")
    require(source_is_ancestor(source_sha),
            "v2 result source SHA is not an ancestor of current HEAD")
    require(result.get("overallResult") == "PARTIAL_PASS",
            "v2 result must remain PARTIAL_PASS")
    environment = result.get("environment")
    require(isinstance(environment, dict), "v2 result environment missing")
    require(environment.get("productionEvidence") is False,
            "v2 CI dependency result cannot be production evidence")
    require(environment.get("containsSecrets") is False,
            "v2 result must contain no secrets")

    scenarios = result.get("scenarios")
    require(isinstance(scenarios, list), "v2 result scenarios must be a list")
    by_id = {item.get("scenarioId"): item for item in scenarios if isinstance(item, dict)}
    for scenario_id in (
        "api-graceful-interruption-drain",
        "parser-restart-after-protocol-failure",
        "object-store-outage-and-recovery",
    ):
        item = by_id.get(scenario_id)
        require(isinstance(item, dict) and item.get("result") == "PASS" and
                item.get("integrityResult") == "PASS" and item.get("exitCode") == 0,
                f"required v2 CI drill is not PASS: {scenario_id}")
    for scenario_id in (
        "database-loss-or-failover",
        "mixed-version-failure-and-rollback",
    ):
        item = by_id.get(scenario_id)
        require(isinstance(item, dict) and item.get("result") == "NOT_RUN",
                f"unexecuted v2 production-shaped drill mislabeled: {scenario_id}")

    assertions = by_id["object-store-outage-and-recovery"].get("assertions")
    require(isinstance(assertions, dict), "object outage assertions missing")
    require(assertions.get("durablePreviewRowsDuringOutage") == 0,
            "outage created durable Preview state")
    require(assertions.get("spoolEntriesDuringOutage") == 0,
            "outage left spool residue")
    require(assertions.get("durablePreviewRowsAfterRecovery") == 1,
            "recovery did not commit exactly one Preview")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "v2 failure-drill evidence cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    matches = [item for item in areas
               if isinstance(item, dict) and item.get("id") == "OPS-P0-009"]
    require(len(matches) == 1, "OPS-P0-009 must exist exactly once")
    gate = matches[0]
    require(gate.get("status") == "PARTIAL", "OPS-P0-009 must remain PARTIAL")

    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-009 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-009 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-009 evidenceRefs must be a list")

    changed = False
    for item in NEW_EXISTING:
        if item not in existing:
            existing.append(item)
            changed = True
    for item in REMOVE_MISSING:
        if item in missing:
            missing.remove(item)
            changed = True
    for item in NEW_MISSING:
        if item not in missing:
            missing.append(item)
            changed = True
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"v2 chaos evidence path missing: {ref}")
        if ref not in refs:
            refs.append(ref)
            changed = True

    before_canonical = json.dumps(status, sort_keys=True, ensure_ascii=False)
    status = load_canonical_normalizer()(status)
    changed = changed or json.dumps(status, sort_keys=True, ensure_ascii=False) != before_canonical
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Chaos/failure-drill v2 authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Registered exact-source object-store outage recovery and preserved canonical stronger chaos authority")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"CHAOS/FAILURE-DRILL V2 RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
