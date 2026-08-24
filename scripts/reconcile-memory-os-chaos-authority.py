#!/usr/bin/env python3
"""Normalize OPS-P0-009 from all committed exact-source drill evidence.

Individual evidence workflows may complete in any order. This reconciler is the
single convergence point: older workflows cannot permanently re-add coarse gaps
that newer exact-source results have closed. It remains conservative when only a
legacy database result exists and upgrades to same-spool resume only after that
new result is committed. Completed in-flight cancellation, parser restart-matrix
and process-group reaping foundations must never be reintroduced as open gaps.
"""

from __future__ import annotations

import argparse
import copy
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
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
STATUS_PATH = CANONICAL_STATUS_PATH
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
OBJECT_RESULT = ROOT / "docs/fixtures/memory-os-operability/chaos-failure-drill-results.v2.sample.json"
PARSER_RESULT = ROOT / "docs/fixtures/memory-os-operability/parser-restart-matrix-results.sample.v1.json"
DATABASE_RESULT = ROOT / "docs/fixtures/memory-os-operability/database-commit-outage-results.sample.v1.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

OBJECT_VALIDATOR = "validate-memory-os-chaos-failure-drills-v2.py"
PARSER_VALIDATOR = "validate-memory-os-parser-restart-matrix.py"
DATABASE_VALIDATOR = "validate-memory-os-database-commit-outage.py"

OBJECT_EVIDENCE = (
    "local PostgreSQL 16 plus MinIO import-flow outage drill proving an unreachable object-store endpoint fails before parse/commit, leaves no Preview or spool residue and the exact same request succeeds once connectivity returns",
    "v2 machine-readable failure-drill authority superseding the two-scenario v1 inventory while preserving CI-vs-production evidence separation",
)
PARSER_EVIDENCE = (
    "five-class parser restart recovery matrix covering protocol truncation, wall-clock timeout, CPU limit kill, memory limit kill and pre-start cancellation; each failure leaves no residue and permits independently verified same-spool recovery",
)
DATABASE_LEGACY_EVIDENCE = (
    "local PostgreSQL commit-outage recovery drill proving a failed atomic Preview commit leaves zero durable rows, preserves sealed spool evidence, and a new attempt for the same source/Preview ID commits exactly once after connectivity returns",
)
DATABASE_RESUME_EVIDENCE = (
    "local PostgreSQL commit-outage recovery drill proving a failed atomic Preview commit leaves zero durable rows, preserves sealed spool evidence, and ResumeCommit commits from the exact same spool/request after connectivity returns without object-store or parser access",
)

COARSE_GAPS = (
    "object-store outage drill",
    "database loss or failover drill",
    "expanded parser restart matrix across timeout, CPU, memory, cancellation, process-group and host-restart failures",
    "in-flight parser cancellation latency and process-group termination proof while the worker is blocked",
    "independent child-process orphan/reaping scan after parser process-group termination",
    "mixed-version failure drill",
)
DIRECT_RESUME_GAP = "direct commit resume from the preserved sealed spool without re-fetching and re-parsing the source"
CANONICAL_GAPS = (
    "production multi-instance interruption, dependency and recovery drills with independent review",
    "production-shaped object-store process outage or network-partition drill with TLS, scoped credentials, lifecycle controls and recovery verification",
    "production-shaped PostgreSQL process loss, connection-pool disruption and replication failover drill",
    "database recovery verification for expired sessions, deleted accounts, leases and duplicate effects under failover",
    "parser host or container restart recovery using a reviewed production artifact",
)
HOST_RESUME_GAP = "host or container restart between spool seal and ResumeCommit with durable spool remount verification"
APPROVED_MIXED_VERSION_GAP = (
    "approved predecessor/current production-shaped mixed-version failure and rollback drill with release-authority binding, connection drain, rollback timing, dependency recovery and independent review"
)

OBJECT_REFS = (
    "contracts/operations/chaos-failure-drill-contract.v2.json",
    "docs/fixtures/memory-os-operability/chaos-failure-drill-results.v2.sample.json",
    "services/import-api/internal/importflow/object_outage_drill_linux_test.go",
    "scripts/validate-memory-os-chaos-failure-drills-v2.py",
    "scripts/reconcile-memory-os-chaos-failure-drills-v2.py",
    ".github/workflows/chaos-failure-drills-v2.yml",
)
PARSER_REFS = (
    "contracts/operations/parser-restart-matrix-contract.v1.json",
    "docs/fixtures/memory-os-operability/parser-restart-matrix-results.sample.v1.json",
    "services/import-api/internal/parsersup/restart_matrix_drill_linux_test.go",
    "scripts/validate-memory-os-parser-restart-matrix.py",
    "scripts/reconcile-memory-os-parser-restart-matrix.py",
    ".github/workflows/parser-restart-matrix.yml",
)
DATABASE_REFS = (
    "contracts/operations/database-commit-outage-contract.v1.json",
    "docs/fixtures/memory-os-operability/database-commit-outage-results.sample.v1.json",
    "services/import-api/internal/importflow/database_outage_drill_linux_test.go",
    "services/import-api/internal/importflow/resume.go",
    "scripts/validate-memory-os-database-commit-outage.py",
    "scripts/reconcile-memory-os-database-commit-outage.py",
    ".github/workflows/database-commit-outage.yml",
)
AUTHORITY_REFS = (
    "scripts/reconcile-memory-os-chaos-authority.py",
    ".github/workflows/reconcile-chaos-authority.yml",
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
    except OSError as exc:
        raise ReconcileFailure(f"canonical {label} cannot be resolved") from exc
    require(resolved == canonical, f"canonical {label} escaped repository path")


def enforce_runtime_authorities() -> None:
    require_exact_authority(STATUS_PATH, CANONICAL_STATUS_PATH, "production operability status")
    require_exact_authority(
        OPERABILITY_VALIDATOR,
        CANONICAL_OPERABILITY_VALIDATOR,
        "operability validator",
    )


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    require(path.parent.is_dir(), f"authority parent missing: {path.parent}")
    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except OSError as exc:
        raise ReconcileFailure(f"cannot atomically write authority: {path.relative_to(ROOT)}: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                pass


def run_canonical_validator(script_name: str) -> None:
    script = ROOT / "scripts" / script_name
    try:
        resolved = script.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"canonical chaos validator missing or escapes repository: {script_name}") from exc
    require(resolved == Path("scripts") / script_name and script.is_file(),
            f"canonical chaos validator path drift: {script_name}")
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise ReconcileFailure(f"cannot execute canonical chaos validator: {script_name}") from exc
    require(result.returncode == 0, f"canonical chaos validator rejected authority: {script_name}")


def run_operability_validator() -> None:
    enforce_runtime_authorities()
    try:
        result = subprocess.run(
            [sys.executable, str(OPERABILITY_VALIDATOR)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        raise ReconcileFailure("cannot execute canonical operability validator") from exc
    require(
        type(result.returncode) is int and result.returncode == 0,
        f"canonical operability validator rejected authority\n{result.stdout[-4000:]}",
    )


def validate_canonical_source_authorities() -> None:
    run_canonical_validator(OBJECT_VALIDATOR)
    run_canonical_validator(PARSER_VALIDATOR)
    database_result = load(DATABASE_RESULT)
    assertions = database_result.get("assertions")
    require(isinstance(assertions, dict), "database outage assertions missing")
    if assertions.get("sameSpoolIdReused") is True:
        run_canonical_validator(DATABASE_VALIDATOR)


def run_post_write_validators() -> None:
    validate_canonical_source_authorities()
    run_operability_validator()


def source_is_ancestor(source_sha: Any) -> bool:
    if not isinstance(source_sha, str) or SHA_RE.fullmatch(source_sha) is None:
        return False
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


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def append_all(target: list[str], values: tuple[str, ...]) -> None:
    for value in values:
        if value not in target:
            target.append(value)


def remove_all(target: list[str], values: tuple[str, ...]) -> None:
    for value in values:
        while value in target:
            target.remove(value)


def validate_object_result(result: dict[str, Any]) -> None:
    require(result.get("schemaVersion") == "memory-os-chaos-failure-drill-results.v2",
            "object outage result schema drift")
    require(source_is_ancestor(result.get("commitSha")),
            "object outage source SHA is not an ancestor")
    require(result.get("overallResult") == "PARTIAL_PASS",
            "object outage authority is not PARTIAL_PASS")
    environment = result.get("environment")
    require(isinstance(environment, dict) and environment.get("productionEvidence") is False,
            "object outage result cannot be production evidence")
    scenarios = result.get("scenarios")
    require(isinstance(scenarios, list), "object outage scenarios missing")
    item = next((entry for entry in scenarios
                 if isinstance(entry, dict) and
                 entry.get("scenarioId") == "object-store-outage-and-recovery"), None)
    require(isinstance(item, dict) and item.get("result") == "PASS" and
            item.get("integrityResult") == "PASS" and item.get("exitCode") == 0,
            "object outage scenario is not exact-source PASS")


def validate_parser_result(result: dict[str, Any]) -> None:
    require(result.get("schemaVersion") == "memory-os-parser-restart-matrix-results.v1",
            "parser matrix result schema drift")
    require(source_is_ancestor(result.get("commitSha")),
            "parser matrix source SHA is not an ancestor")
    require(result.get("overallResult") == "PASS",
            "parser matrix is not PASS")
    cases = result.get("failureClasses")
    require(isinstance(cases, list) and len(cases) == 5,
            "parser matrix does not contain five cases")
    require(all(isinstance(item, dict) and item.get("result") == "PASS"
                for item in cases), "parser matrix contains a non-PASS case")


def validate_database_result(result: dict[str, Any]) -> bool:
    require(result.get("schemaVersion") == "memory-os-database-commit-outage-results.v1",
            "database outage result schema drift")
    require(source_is_ancestor(result.get("commitSha")),
            "database outage source SHA is not an ancestor")
    require(result.get("result") == "PASS" and result.get("integrityResult") == "PASS" and
            result.get("exitCode") == 0,
            "database outage result is not PASS")
    assertions = result.get("assertions")
    require(isinstance(assertions, dict), "database outage assertions missing")
    require(assertions.get("previewRowsDuringOutage") == 0 and
            assertions.get("previewRowsAfterRecovery") == 1,
            "database outage durable-row assertions failed")
    modern = (
        assertions.get("sameSpoolIdReused") is True and
        assertions.get("resumeWithoutObjectStore") is True and
        assertions.get("resumeWithoutParser") is True
    )
    if not modern:
        require(assertions.get("newSpoolAttemptUsed") is True,
                "database outage result is neither legacy nor same-spool format")
    return modern


def normalized_status(status: dict[str, Any]) -> dict[str, Any]:
    require(status.get("productionDecision") == "NO_GO",
            "chaos authority requires productionDecision NO_GO")
    validate_canonical_source_authorities()
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

    object_result = load(OBJECT_RESULT)
    parser_result = load(PARSER_RESULT)
    database_result = load(DATABASE_RESULT)
    validate_object_result(object_result)
    validate_parser_result(parser_result)
    modern_database = validate_database_result(database_result)

    remove_all(missing, COARSE_GAPS)
    append_all(existing, OBJECT_EVIDENCE)
    append_all(existing, PARSER_EVIDENCE)
    append_all(missing, CANONICAL_GAPS)
    append_all(missing, (APPROVED_MIXED_VERSION_GAP,))

    remove_all(existing, DATABASE_LEGACY_EVIDENCE + DATABASE_RESUME_EVIDENCE)
    if modern_database:
        append_all(existing, DATABASE_RESUME_EVIDENCE)
        remove_all(missing, (DIRECT_RESUME_GAP,))
        append_all(missing, (HOST_RESUME_GAP,))
    else:
        append_all(existing, DATABASE_LEGACY_EVIDENCE)
        append_all(missing, (DIRECT_RESUME_GAP,))
        remove_all(missing, (HOST_RESUME_GAP,))

    for ref in OBJECT_REFS + PARSER_REFS + DATABASE_REFS + AUTHORITY_REFS:
        require((ROOT / ref).is_file(), f"chaos authority evidence path missing: {ref}")
    append_all(refs, OBJECT_REFS + PARSER_REFS + DATABASE_REFS + AUTHORITY_REFS)

    gate["existingEvidence"] = unique(existing)
    gate["missingEvidence"] = unique(missing)
    gate["evidenceRefs"] = unique(refs)
    for stale in COARSE_GAPS:
        require(stale not in gate["missingEvidence"],
                f"completed/coarse chaos gap remained stale: {stale}")
    require(gate.get("status") == "PARTIAL", "OPS-P0-009 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")
    return status


def commit_candidate(candidate: dict[str, Any]) -> None:
    enforce_runtime_authorities()
    original_status = STATUS_PATH.read_bytes()
    payload = json.dumps(candidate, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    atomic_write_bytes(STATUS_PATH, payload)
    try:
        run_post_write_validators()
    except Exception:
        atomic_write_bytes(STATUS_PATH, original_status)
        raise


def main() -> int:
    enforce_runtime_authorities()
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    current = load(STATUS_PATH)
    candidate = normalized_status(copy.deepcopy(current))
    candidate["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()

    # Direct invocation must validate the current aggregate boundary even when
    # normalization is already a no-op or the caller uses --check.
    run_operability_validator()

    current_compare = copy.deepcopy(current)
    candidate_compare = copy.deepcopy(candidate)
    current_compare.pop("asOf", None)
    candidate_compare.pop("asOf", None)
    changed = current_compare != candidate_compare

    if args.check:
        require(not changed, "OPS-P0-009 authority is not normalized")
        print("Memory OS chaos authority normalization check PASS")
        return 0
    if not changed:
        print("Memory OS chaos authority already normalized")
        return 0
    commit_candidate(candidate)
    print("Normalized OPS-P0-009 across object, parser, database and completed parser-control evidence")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"CHAOS AUTHORITY NORMALIZATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
