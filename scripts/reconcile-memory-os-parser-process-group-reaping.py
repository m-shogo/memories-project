#!/usr/bin/env python3
"""Register exact-source parser process-group reaping evidence conservatively."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/parser-process-group-reaping-contract.v1.json"
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-process-group-reaping-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
PROCESS_GROUP_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-process-group-reaping.py"
OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

SATISFIED_MISSING = "independent child-process orphan/reaping scan after parser process-group termination"
EXISTING = (
    "exact-source Linux parser process-group reaping drill starts a synthetic child in the supervised worker group, independently observes at least two marked /proc members before cancellation, returns context.Canceled promptly, then proves every captured worker/child /proc entry disappears after Parse returns with zero spool residue; raw process identifiers are never persisted and this remains local CI evidence",
)
REFS = (
    "contracts/operations/parser-process-group-reaping-contract.v1.json",
    "docs/fixtures/memory-os-operability/parser-process-group-reaping-results.sample.v1.json",
    "services/import-api/internal/parsersup/supervisor_linux.go",
    "services/import-api/internal/parsersup/worker.go",
    "services/import-api/internal/parsersup/process_group_reaping_drill_linux_test.go",
    "scripts/validate-memory-os-parser-process-group-reaping.py",
    "scripts/reconcile-memory-os-parser-process-group-reaping.py",
    ".github/workflows/parser-process-group-reaping.yml",
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
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
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


def append_once(values: list[Any], value: str) -> bool:
    if value in values:
        return False
    values.append(value)
    return True


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_post_validators() -> None:
    for validator in (PROCESS_GROUP_VALIDATOR, OPERABILITY_VALIDATOR):
        completed = subprocess.run(
            [sys.executable, str(validator)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        require(completed.returncode == 0,
                f"post-write validator failed: {validator.relative_to(ROOT)}\n{completed.stdout}")


def commit_candidate(contract: dict[str, Any], status: dict[str, Any]) -> None:
    original_contract = CONTRACT_PATH.read_bytes()
    original_status = STATUS_PATH.read_bytes()
    try:
        write_json(CONTRACT_PATH, contract)
        write_json(STATUS_PATH, status)
        run_post_validators()
    except Exception:
        CONTRACT_PATH.write_bytes(original_contract)
        STATUS_PATH.write_bytes(original_status)
        raise


def main() -> int:
    result = load(RESULT_PATH)
    require(result.get("schemaVersion") == "memory-os-parser-process-group-reaping-results.v1",
            "process-group reaping result schemaVersion drift")
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and SHA_RE.fullmatch(source_sha) is not None,
            "process-group reaping result source SHA invalid")
    require(source_is_ancestor(source_sha),
            "process-group reaping result source SHA is not an ancestor of HEAD")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS" and
            result.get("exitCode") == 0,
            "process-group reaping result is not PASS")
    environment = result.get("environment")
    require(isinstance(environment, dict) and environment.get("productionEvidence") is False and
            environment.get("containsSecrets") is False,
            "process-group reaping environment boundary drift")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "process-group reaping assertions missing")
    require(isinstance(assertions.get("trackedProcessCountBeforeCancel"), int) and
            assertions["trackedProcessCountBeforeCancel"] >= 2,
            "worker plus child were not independently observed")
    require(assertions.get("trackedProcessCountAfterCancel") == 0 and
            assertions.get("allCapturedProcEntriesGone") is True,
            "captured process entries survived cancellation")
    require(assertions.get("returnedContextCanceled") is True and
            assertions.get("spoolResidueAbsent") is True,
            "cancellation or spool cleanup assertion failed")

    contract = load(CONTRACT_PATH)
    readiness = contract.get("readiness")
    refs = contract.get("evidenceRefs")
    require(isinstance(readiness, dict) and isinstance(refs, list),
            "process-group reaping contract readiness/refs missing")
    changed = False
    for key in ("exactSourcePassResultCommitted", "childProcessOrphanScanCompleted"):
        if readiness.get(key) is not True:
            readiness[key] = True
            changed = True
    if append_once(refs, str(RESULT_PATH.relative_to(ROOT))):
        changed = True
    require(readiness.get("hostRestartExecuted") is False and
            readiness.get("productionArtifactExecuted") is False and
            readiness.get("productionReady") is False,
            "local reaping evidence cannot promote production boundaries")

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "process-group reaping evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL" and
            gate.get("blocking") is True,
            "OPS-P0-009 must remain blocking PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    evidence_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list) and isinstance(missing, list) and isinstance(evidence_refs, list),
            "OPS-P0-009 authority arrays missing")

    while SATISFIED_MISSING in missing:
        missing.remove(SATISFIED_MISSING)
        changed = True
    for item in EXISTING:
        if append_once(existing, item):
            changed = True
    for ref in REFS:
        require((ROOT / ref).is_file(), f"process-group reaping evidence path missing: {ref}")
        if append_once(evidence_refs, ref):
            changed = True

    joined = "\n".join(missing)
    for phrase in (
        "production multi-instance",
        "production-shaped object-store",
        "production-shaped PostgreSQL",
        "parser host or container restart",
        "host or container restart",
        "mixed-version failure",
    ):
        require(phrase in joined, f"required production-shaped failure gap disappeared: {phrase}")
    require(SATISFIED_MISSING not in missing,
            "completed child-process orphan/reaping gap remained stale")

    if not changed:
        run_post_validators()
        print("Parser process-group reaping authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    commit_candidate(contract, status)
    print("Registered exact-source parser process-group reaping evidence")
    print("child-process orphan/reaping gap: satisfied locally")
    print("OPS-P0-009: PARTIAL")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"PARSER PROCESS-GROUP REAPING RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
