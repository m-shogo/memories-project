#!/usr/bin/env python3
"""Register exact-source in-flight parser cancellation evidence conservatively."""

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
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-inflight-cancellation-results.sample.v1.json"
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_RECONCILER_PATH = ROOT / "scripts/reconcile-memory-os-chaos-authority.py"
CANONICAL_OVERLAY_PATH = ROOT / "scripts/reconcile-memory-os-chaos-inflight-overlay.py"
CANONICAL_INFLIGHT_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-inflight-cancellation.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
RESULT_PATH = CANONICAL_RESULT_PATH
STATUS_PATH = CANONICAL_STATUS_PATH
CANONICAL_RECONCILER = CANONICAL_RECONCILER_PATH
CANONICAL_OVERLAY = CANONICAL_OVERLAY_PATH
INFLIGHT_VALIDATOR = CANONICAL_INFLIGHT_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
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


def path_label(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load(path: Path) -> dict[str, Any]:
    label = path_label(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileFailure(f"missing file: {label}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileFailure(f"invalid JSON in {label}: {exc}") from exc
    require(isinstance(value, dict), f"root must be an object: {label}")
    return value


def require_exact_authority(path: Path, canonical: Path, label: str) -> None:
    require(path == canonical, f"{label} authority drift")
    require(canonical.is_file(), f"canonical {label} missing")
    require(not canonical.is_symlink(), f"canonical {label} cannot be a symlink")


def require_external_fixture(path: Path, label: str) -> None:
    require(path.is_file(), f"{label} fixture missing")
    require(not path.is_symlink(), f"{label} fixture cannot be a symlink")
    try:
        path.resolve(strict=True).relative_to(ROOT.resolve())
    except ValueError:
        return
    except (FileNotFoundError, OSError, RuntimeError) as exc:
        raise ReconcileFailure(f"cannot resolve {label} fixture") from exc
    raise ReconcileFailure(f"{label} fixture must remain outside repository")


def enforce_data_authorities() -> None:
    canonical_result = RESULT_PATH == CANONICAL_RESULT_PATH
    canonical_status = STATUS_PATH == CANONICAL_STATUS_PATH
    require(canonical_result is canonical_status, "in-flight fixture boundary must replace result and status together")
    if canonical_result:
        require_exact_authority(RESULT_PATH, CANONICAL_RESULT_PATH, "in-flight result")
        require_exact_authority(STATUS_PATH, CANONICAL_STATUS_PATH, "production operability status")
        return
    require_external_fixture(RESULT_PATH, "in-flight result")
    require_external_fixture(STATUS_PATH, "production operability status")


def validate_executable_authorities() -> None:
    require_exact_authority(CANONICAL_RECONCILER, CANONICAL_RECONCILER_PATH, "chaos authority reconciler")
    require_exact_authority(CANONICAL_OVERLAY, CANONICAL_OVERLAY_PATH, "chaos in-flight overlay")
    require_exact_authority(INFLIGHT_VALIDATOR, CANONICAL_INFLIGHT_VALIDATOR, "in-flight validator")
    require_exact_authority(OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator")


def load_normalizer(path: Path, module_name: str, attribute: str):
    validate_executable_authorities()
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"canonical chaos authority missing or escapes repository: {path.name}") from exc
    require(resolved == Path("scripts") / path.name and path.is_file(), f"canonical chaos authority path drift: {path.name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None, f"cannot load canonical chaos authority: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    normalizer = getattr(module, attribute, None)
    require(callable(normalizer), f"canonical chaos authority missing {attribute}: {path.name}")
    return normalizer


def source_is_ancestor(source_sha: str) -> bool:
    try:
        return subprocess.run(["git", "merge-base", "--is-ancestor", source_sha, "HEAD"], cwd=ROOT, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def run_validator(path: Path, *, expected_sha: str | None = None) -> None:
    require(path.is_file(), f"canonical validator missing: {path.relative_to(ROOT)}")
    require(not path.is_symlink(), f"canonical validator cannot be a symlink: {path.relative_to(ROOT)}")
    env = os.environ.copy()
    if expected_sha is not None:
        env["EXPECTED_COMMIT_SHA"] = expected_sha
    completed = subprocess.run([sys.executable, str(path)], cwd=ROOT, env=env, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    require(type(completed.returncode) is int and completed.returncode == 0, f"canonical validator rejected authority: {path.relative_to(ROOT)}\n{completed.stdout[-4000:]}")


def validate_authority_chain(source_sha: str) -> None:
    validate_executable_authorities()
    run_validator(INFLIGHT_VALIDATOR, expected_sha=source_sha)
    run_validator(OPERABILITY_VALIDATOR)


def main() -> int:
    enforce_data_authorities()
    result = load(RESULT_PATH)
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str) and SHA_RE.fullmatch(source_sha) is not None, "in-flight result source SHA is invalid")
    require(source_is_ancestor(source_sha), "in-flight result source SHA is not an ancestor of current HEAD")
    validate_authority_chain(source_sha)
    original_status_bytes = STATUS_PATH.read_bytes()
    status = load(STATUS_PATH)
    require(status.get("productionDecision") == "NO_GO", "in-flight evidence cannot change production decision")
    areas = status.get("areas")
    require(isinstance(areas, list), "status areas must be a list")
    gate = next((item for item in areas if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
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
        missing.remove(OLD_MISSING); changed = True
    for item in NEW_EXISTING:
        if item not in existing: existing.append(item); changed = True
    for item in NEW_MISSING:
        if item not in missing: missing.append(item); changed = True
    for ref in NEW_REFS:
        require((ROOT / ref).is_file(), f"in-flight evidence path missing: {ref}")
        if ref not in refs: refs.append(ref); changed = True
    before_canonical = json.dumps(status, sort_keys=True, ensure_ascii=False)
    status = load_normalizer(CANONICAL_RECONCILER, "memory_os_canonical_chaos_authority_inflight_reconcile", "normalized_status")(status)
    status = load_normalizer(CANONICAL_OVERLAY, "memory_os_canonical_chaos_inflight_overlay_reconcile", "normalize")(status)
    changed = changed or json.dumps(status, sort_keys=True, ensure_ascii=False) != before_canonical
    gate = next((item for item in status.get("areas", []) if isinstance(item, dict) and item.get("id") == "OPS-P0-009"), None)
    require(isinstance(gate, dict), "OPS-P0-009 missing after canonical reconcile")
    missing = gate.get("missingEvidence")
    require(isinstance(missing, list), "OPS-P0-009 missingEvidence invalid after canonical reconcile")
    for phrase in ("production multi-instance", "production-shaped object-store", "production-shaped PostgreSQL", "host or container restart"):
        require(any(phrase in item for item in missing), f"required OPS-P0-009 gap disappeared: {phrase}")
    require(status.get("productionDecision") == "NO_GO", "production decision changed unexpectedly")
    if not changed:
        validate_authority_chain(source_sha)
        print("Parser in-flight cancellation authority already reconciled")
        return 0
    status["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    STATUS_PATH.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    try:
        validate_authority_chain(source_sha)
    except Exception:
        STATUS_PATH.write_bytes(original_status_bytes)
        raise
    print("Registered exact-source in-flight parser cancellation through canonical chaos authorities")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"PARSER IN-FLIGHT CANCELLATION RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
