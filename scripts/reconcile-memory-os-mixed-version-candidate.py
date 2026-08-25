#!/usr/bin/env python3
"""Register exact-source candidate compatibility evidence conservatively."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_CONTRACT_PATH = ROOT / "contracts/operations/mixed-version-candidate-contract.v1.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json"
CANONICAL_REJECTION_PATH = ROOT / "docs/fixtures/memory-os-operability/mixed-version-candidate-rejections.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_CANDIDATE_VALIDATOR = ROOT / "scripts/validate-memory-os-mixed-version-candidate.py"
CANONICAL_VERSION_VALIDATOR = ROOT / "scripts/validate-memory-os-version-compatibility.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CONTRACT_PATH = CANONICAL_CONTRACT_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
REJECTION_PATH = CANONICAL_REJECTION_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
CANDIDATE_VALIDATOR = CANONICAL_CANDIDATE_VALIDATOR
VERSION_VALIDATOR = CANONICAL_VERSION_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
ACTIVE_BASELINE_SHA = "2af6e8e10755cc707c6bdd958a049a0f4afb3d70"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RESULT_REF = "docs/fixtures/memory-os-operability/mixed-version-candidate-results.sample.v1.json"

NEW_EXISTING = (
    "historical candidate-baseline compatibility drill applying the current expanded PostgreSQL schema before executing baseline-owned SQL and reviewed common Go integration surfaces sequentially",
    "candidate execution preserves the current memory_os schema fingerprint and current SQL/Go verification passes independently on a separate database",
    "exact active baseline/current SHAs are recorded while rejected historical candidates remain preserved in a separate machine-readable registry",
)
NEW_MISSING = (
    "approved predecessor release artifact and successor release pair for binding compatibility evidence",
    "simultaneous old/current application traffic against the same production-shaped database",
    "rolling deployment order, connection drain, failure injection and application rollback rehearsal",
    "destructive contract-migration and downgrade compatibility proof",
    "production-shaped mixed-version review with zero unresolved Critical or High findings",
)
NEW_REFS = (
    "contracts/operations/mixed-version-candidate-contract.v1.json",
    "docs/fixtures/memory-os-operability/mixed-version-candidate-rejections.v1.json",
    RESULT_REF,
    "scripts/run-memory-os-mixed-version-candidate.sh",
    "scripts/validate-memory-os-mixed-version-candidate.py",
    "scripts/reconcile-memory-os-mixed-version-candidate.py",
    ".github/workflows/mixed-version-candidate.yml",
)


class ReconcileFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileFailure(message)


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority substitution")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")
    try:
        resolved = canonical.resolve(strict=True)
    except OSError as exc:
        raise ReconcileFailure(f"canonical {label} cannot be resolved") from exc
    require(resolved == canonical, f"canonical {label} escaped repository path")


def enforce_runtime_authorities() -> None:
    for path, canonical, label in (
        (CONTRACT_PATH, CANONICAL_CONTRACT_PATH, "mixed-version candidate contract"),
        (RESULT_PATH, CANONICAL_RESULT_PATH, "mixed-version candidate result"),
        (REJECTION_PATH, CANONICAL_REJECTION_PATH, "mixed-version candidate rejection registry"),
        (STATUS_PATH, CANONICAL_STATUS_PATH, "production status"),
        (CANDIDATE_VALIDATOR, CANONICAL_CANDIDATE_VALIDATOR, "mixed-version candidate validator"),
        (VERSION_VALIDATOR, CANONICAL_VERSION_VALIDATOR, "version compatibility validator"),
        (OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator"),
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


def atomic_write_bytes(path: Path, data: bytes) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write(path: Path, value: dict[str, Any]) -> None:
    atomic_write_bytes(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def run_validator(path: Path, failure_label: str) -> None:
    enforce_runtime_authorities()
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    require(
        type(completed.returncode) is int and completed.returncode == 0,
        failure_label + ":\n" + completed.stdout[-4000:] + completed.stderr[-4000:],
    )


def commit_outputs_transactionally(outputs: dict[Path, dict[str, Any]]) -> None:
    originals = {path: path.read_bytes() for path in outputs}
    try:
        for path, value in outputs.items():
            write(path, value)
        run_validator(CANDIDATE_VALIDATOR, "candidate authority rejected after reconcile")
        run_validator(VERSION_VALIDATOR, "version compatibility authority rejected after candidate reconcile")
        run_validator(OPERABILITY_VALIDATOR, "operability authority rejected after candidate reconcile")
    except Exception as exc:
        rollback_errors: list[str] = []
        for path, data in originals.items():
            try:
                atomic_write_bytes(path, data)
            except Exception as rollback_exc:
                rollback_errors.append(f"{path.name}: {rollback_exc}")
        if rollback_errors:
            raise ReconcileFailure(
                "candidate reconcile validation failed and rollback was incomplete: "
                + "; ".join(rollback_errors)
                + f"; original failure: {exc}"
            ) from exc
        raise ReconcileFailure(f"candidate reconcile validation failed; restored prior authority: {exc}") from exc


def is_ancestor(base: str, head: str) -> bool:
    try:
        return subprocess.run(
            ["git", "merge-base", "--is-ancestor", base, head],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode == 0
    except OSError:
        return False


def main() -> int:
    enforce_runtime_authorities()
    result = load(RESULT_PATH)
    require(result.get("schemaVersion") ==
            "memory-os-mixed-version-candidate-results.v1",
            "candidate result schema drift")
    current_sha = result.get("currentCommitSha")
    require(isinstance(current_sha, str) and SHA_RE.fullmatch(current_sha) is not None,
            "candidate current SHA invalid")
    require(result.get("candidateBaselineCommitSha") == ACTIVE_BASELINE_SHA,
            "candidate result baseline SHA drift")
    require(is_ancestor(ACTIVE_BASELINE_SHA, current_sha) and
            is_ancestor(current_sha, "HEAD"),
            "candidate source lineage is invalid")
    environment = result.get("environment")
    require(isinstance(environment, dict) and
            environment.get("productionEvidence") is False and
            environment.get("releaseCompatibilityEvidence") is False and
            environment.get("candidateBaselineOnly") is True and
            environment.get("containsSecrets") is False and
            environment.get("syntheticDataOnly") is True,
            "candidate evidence boundary drift")
    scenario = result.get("scenario")
    require(isinstance(scenario, dict) and
            scenario.get("result") == "PASS" and
            scenario.get("integrityResult") == "PASS",
            "candidate compatibility result is not PASS")
    assertions = scenario.get("assertions")
    require(isinstance(assertions, dict) and assertions and all(assertions.values()),
            "candidate result contains a failed assertion")

    contract = load(CONTRACT_PATH)
    require(contract.get("candidateBaseline", {}).get("commitSha") == ACTIVE_BASELINE_SHA,
            "candidate contract baseline drift")
    require(contract.get("rejectedCandidateRegistry") ==
            str(REJECTION_PATH.relative_to(ROOT)),
            "candidate rejection registry authority drift")
    require(contract.get("evidenceBoundary", {}).get("productionReady") is False,
            "candidate contract cannot claim production readiness")
    readiness = contract.get("readiness")
    refs = contract.get("evidenceRefs")
    require(isinstance(readiness, dict), "candidate readiness missing")
    require(isinstance(refs, list), "candidate evidenceRefs must be a list")

    contract_changed = False
    for field in (
        "contractDefined", "runnerImplemented",
        "validatorImplemented", "automaticWorkflowImplemented",
        "exactSourcePassResultCommitted",
    ):
        if readiness.get(field) is not True:
            readiness[field] = True
            contract_changed = True
    for field in (
        "approvedReleaseBaselineAvailable", "simultaneousMixedTrafficExecuted",
        "rollingDeploymentFailureExecuted", "productionReady",
    ):
        require(readiness.get(field) is False,
                f"candidate evidence cannot promote readiness.{field}")
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"candidate evidence path missing: {ref}")
        if ref not in refs:
            refs.append(ref)
            contract_changed = True

    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "candidate evidence cannot change production decision")
    gate = next((item for item in status.get("areas", [])
                 if isinstance(item, dict) and item.get("id") == "OPS-P0-008"), None)
    require(isinstance(gate, dict) and gate.get("status") == "PARTIAL",
            "OPS-P0-008 must remain PARTIAL")
    existing = gate.get("existingEvidence")
    missing = gate.get("missingEvidence")
    status_refs = gate.get("evidenceRefs")
    require(isinstance(existing, list), "OPS-P0-008 existingEvidence must be a list")
    require(isinstance(missing, list), "OPS-P0-008 missingEvidence must be a list")
    require(isinstance(status_refs, list), "OPS-P0-008 evidenceRefs must be a list")

    status_changed = False
    for item in NEW_EXISTING:
        if item not in existing:
            existing.append(item)
            status_changed = True
    for item in NEW_MISSING:
        if item not in missing:
            missing.append(item)
            status_changed = True
    for ref in NEW_REFS:
        if ref not in status_refs:
            status_refs.append(ref)
            status_changed = True

    lowered = [str(item).lower() for item in missing]
    for label, terms in {
        "approved predecessor release": ("approved", "predecessor", "release"),
        "simultaneous mixed traffic": ("simultaneous", "old/current", "traffic"),
        "rolling rollback": ("rolling", "rollback"),
        "contract migration": ("contract-migration", "downgrade"),
        "independent review": ("critical", "high"),
    }.items():
        require(any(all(term in item for term in terms) for item in lowered),
                f"required compatibility gap disappeared: {label}")

    outputs: dict[Path, dict[str, Any]] = {}
    if contract_changed:
        outputs[CONTRACT_PATH] = contract
    if status_changed:
        status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
        outputs[STATUS_PATH] = status

    commit_outputs_transactionally(outputs)
    if not outputs:
        run_validator(CANDIDATE_VALIDATOR, "candidate authority rejected without reconcile")
        run_validator(VERSION_VALIDATOR, "version compatibility authority rejected without candidate reconcile")
        run_validator(OPERABILITY_VALIDATOR, "operability authority rejected without candidate reconcile")
        print("Mixed-version candidate authority already reconciled")
        return 0
    print("Registered active historical candidate compatibility; OPS-P0-008 remains PARTIAL")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"MIXED-VERSION CANDIDATE RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
