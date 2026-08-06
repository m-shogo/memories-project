#!/usr/bin/env python3
"""Register exact-source in-flight parser cancellation evidence conservatively."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-inflight-cancellation-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

OLD_MISSING = "in-flight parser cancellation latency and process-group termination proof while the worker is blocked"
NEW_EXISTING = (
    "started-worker parser cancellation drill proving a completed frame reaches spool storage before cancellation, the blocked pipe read returns context.Canceled in under one second, cleanup removes the partial attempt and the same spool ID recovers with independent verification",
)
NEW_MISSING = (
    "independent child-process orphan/reaping scan after parser process-group termination",
    "parser host or container restart recovery using a reviewed production artifact",
)
NEW_REFS = (
    "contracts/operations/parser-inflight-cancellation-contract.v1.json",
    "docs/fixtures/memory-os-operability/parser-inflight-cancellation-results.sample.v1.json",
    "services/import-api/internal/parsersup/supervisor_linux.go",
    "services/import-api/internal/parsersup/worker.go",
    "services/import-api/internal/parsersup/inflight_cancellation_drill_linux_test.go",
    "scripts/validate-memory-os-parser-inflight-cancellation.py",
    "scripts/reconcile-memory-os-parser-inflight-cancellation.py",
    ".github/workflows/parser-inflight-cancellation.yml",
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
    require(result.get("schemaVersion") ==
            "memory-os-parser-inflight-cancellation-results.v1",
            "in-flight result schemaVersion drift")
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and SHA_RE.fullmatch(source_sha) is not None,
            "in-flight result source SHA is invalid")
    require(source_is_ancestor(source_sha),
            "in-flight result source SHA is not an ancestor of current HEAD")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS" and
            result.get("exitCode") == 0,
            "in-flight cancellation result is not PASS")
    environment = result.get("environment")
    require(isinstance(environment, dict), "in-flight result environment missing")
    require(environment.get("productionEvidence") is False,
            "in-flight result cannot be production evidence")
    require(environment.get("containsSecrets") is False,
            "in-flight result must contain no secrets")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "in-flight result assertions missing")
    for flag in (
        "workerFrameObservedBeforeCancel", "spoolDataObservedBeforeCancel",
        "returnedContextCanceled", "spoolResidueAbsent", "sameSpoolReusable",
        "replacementSealValid", "independentVerificationMatched",
    ):
        require(assertions.get(flag) is True, f"in-flight assertion failed: {flag}")
    latency = assertions.get("cancellationLatencyMilliseconds")
    require(isinstance(latency, (int, float)) and 0 <= latency < 1000,
            "in-flight cancellation latency is not below one second")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "in-flight evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict), "OPS-P0-009 missing")
    require(gate.get("status") == "PARTIAL", "OPS-P0-009 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-009 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-009 missingEvidence must be a list")
    require(isinstance(refs, list), "OPS-P0-009 evidenceRefs must be a list")

    changed = False
    while OLD_MISSING in missing:
        missing.remove(OLD_MISSING)
        changed = True
    for item in NEW_EXISTING:
        if item not in existing:
            existing.append(item)
            changed = True
    for item in NEW_MISSING:
        if item not in missing:
            missing.append(item)
            changed = True
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"in-flight evidence path missing: {ref}")
        if ref not in refs:
            refs.append(ref)
            changed = True

    for phrase in (
        "mixed-version failure",
        "production multi-instance",
        "production-shaped object-store",
        "production-shaped PostgreSQL",
        "child-process orphan",
        "host or container restart",
    ):
        require(any(phrase in item for item in missing),
                f"required OPS-P0-009 gap disappeared: {phrase}")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        print("Parser in-flight cancellation authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Registered exact-source in-flight parser cancellation; OPS-P0-009 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"PARSER IN-FLIGHT CANCELLATION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
