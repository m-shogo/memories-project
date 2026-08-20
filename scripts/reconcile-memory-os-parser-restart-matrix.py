#!/usr/bin/env python3
"""Register exact-source parser restart matrix evidence conservatively."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-restart-matrix-results.sample.v1.json"
STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-chaos-authority.py"
CANONICAL_PARSER_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-restart-matrix.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
CANONICAL_RECONCILER = CANONICAL_RECONCILER_PATH
PARSER_VALIDATOR = CANONICAL_PARSER_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

OLD_MISSING = "expanded parser restart matrix across timeout, CPU, memory, cancellation, process-group and host-restart failures"
NEW_EXISTING = (
    "five-class parser restart recovery matrix covering protocol truncation, wall-clock timeout, CPU limit kill, memory limit kill and pre-start cancellation; each failure leaves no residue and permits independently verified same-spool recovery",
)
NEW_MISSING = (
    "in-flight parser cancellation latency and process-group termination proof while the worker is blocked",
    "independent child-process orphan/reaping scan after parser process-group termination",
    "parser host or container restart recovery using a reviewed production artifact",
)
NEW_REFS = (
    "contracts/operations/parser-restart-matrix-contract.v1.json",
    "docs/fixtures/memory-os-operability/parser-restart-matrix-results.sample.v1.json",
    "services/import-api/internal/parsersup/restart_matrix_drill_linux_test.go",
    "scripts/validate-memory-os-parser-restart-matrix.py",
    "scripts/reconcile-memory-os-parser-restart-matrix.py",
    ".github/workflows/parser-restart-matrix.yml",
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


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")


def load_canonical_normalizer():
    require_exact_authority(
        CANONICAL_RECONCILER,
        CANONICAL_RECONCILER_PATH,
        "chaos authority reconciler",
    )
    spec = importlib.util.spec_from_file_location("memory_os_canonical_chaos_authority_parser_matrix", CANONICAL_RECONCILER)
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


def run_validator(path: Path, *, expected_sha: str | None = None) -> None:
    require(path.is_file(), f"canonical validator missing: {path.relative_to(ROOT)}")
    require(not path.is_symlink(), f"canonical validator cannot be a symlink: {path.relative_to(ROOT)}")
    env = os.environ.copy()
    if expected_sha is not None:
        env["EXPECTED_COMMIT_SHA"] = expected_sha
    try:
        completed = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        raise ReconcileFailure(f"cannot execute canonical validator: {path.relative_to(ROOT)}") from exc
    require(
        type(completed.returncode) is int and completed.returncode == 0,
        f"canonical validator rejected authority: {path.relative_to(ROOT)}\n{completed.stdout[-4000:]}",
    )


def validate_authority_chain(source_sha: str) -> None:
    require_exact_authority(
        PARSER_VALIDATOR,
        CANONICAL_PARSER_VALIDATOR,
        "parser restart validator",
    )
    require_exact_authority(
        OPERABILITY_VALIDATOR,
        CANONICAL_OPERABILITY_VALIDATOR,
        "operability validator",
    )
    run_validator(PARSER_VALIDATOR, expected_sha=source_sha)
    run_validator(OPERABILITY_VALIDATOR)


def main() -> int:
    result = load(RESULT_PATH)
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and SHA_RE.fullmatch(source_sha) is not None,
            "matrix result source SHA is invalid")
    require(source_is_ancestor(source_sha),
            "matrix result source SHA is not an ancestor of current HEAD")

    # The canonical validator owns result/contract semantics. The reconciler must
    # not maintain a weaker parallel interpretation of exact-source evidence.
    validate_authority_chain(source_sha)

    original_status_bytes = STATUS_PATH.read_bytes()
    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO",
            "parser matrix cannot change production decision")
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
    if OLD_MISSING in missing:
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
        require((ROOT / ref).is_file(), f"matrix evidence path missing: {ref}")
        if ref not in refs:
            refs.append(ref)
            changed = True

    before_canonical = json.dumps(status, sort_keys=True, ensure_ascii=False)
    status = load_canonical_normalizer()(status)
    changed = changed or json.dumps(status, sort_keys=True, ensure_ascii=False) != before_canonical
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")

    if not changed:
        # A no-op reconcile must still prove that current derived authority is
        # acceptable to both the scenario validator and aggregate operability.
        validate_authority_chain(source_sha)
        print("Parser restart matrix authority already reconciled")
        return 0

    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    try:
        validate_authority_chain(source_sha)
    except Exception:
        STATUS_PATH.write_bytes(original_status_bytes)
        raise

    print("Registered exact-source parser restart matrix and preserved canonical stronger chaos authority")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"PARSER RESTART MATRIX RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
