#!/usr/bin/env python3
"""Converge the in-flight cancellation slice of OPS-P0-009.

The overlay remains conservative for host/container restart, while preserving
completed child-process reaping authority when its exact-source result validates.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_STATUS_PATH = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL_RESULT_PATH = ROOT / "docs/fixtures/memory-os-operability/parser-inflight-cancellation-results.sample.v1.json"
CANONICAL_PROCESS_GROUP_RESULT = ROOT / "docs/fixtures/memory-os-operability/parser-process-group-reaping-results.sample.v1.json"
CANONICAL_INFLIGHT_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-inflight-cancellation.py"
CANONICAL_PROCESS_GROUP_VALIDATOR = ROOT / "scripts/validate-memory-os-parser-process-group-reaping.py"
CANONICAL_OPERABILITY_VALIDATOR = ROOT / "scripts/validate-memory-os-operability.py"
STATUS_PATH = CANONICAL_STATUS_PATH
RESULT_PATH = CANONICAL_RESULT_PATH
PROCESS_GROUP_RESULT = CANONICAL_PROCESS_GROUP_RESULT
INFLIGHT_VALIDATOR = CANONICAL_INFLIGHT_VALIDATOR
PROCESS_GROUP_VALIDATOR = CANONICAL_PROCESS_GROUP_VALIDATOR
OPERABILITY_VALIDATOR = CANONICAL_OPERABILITY_VALIDATOR
GAP = "in-flight parser cancellation latency and process-group termination proof while the worker is blocked"
CHILD_REAPING_GAP = "independent child-process orphan/reaping scan after parser process-group termination"
HOST_RESTART_GAP = "parser host or container restart recovery using a reviewed production artifact"
EVIDENCE = "started-worker parser cancellation drill proving a completed frame reaches spool storage before cancellation, the blocked pipe read returns context.Canceled in under one second, cleanup removes the partial attempt and the same spool ID recovers with independent verification"
REFS = (
    "contracts/operations/parser-inflight-cancellation-contract.v1.json",
    "docs/fixtures/memory-os-operability/parser-inflight-cancellation-results.sample.v1.json",
    "services/import-api/internal/parsersup/supervisor_linux.go",
    "services/import-api/internal/parsersup/worker.go",
    "services/import-api/internal/parsersup/inflight_cancellation_drill_linux_test.go",
    "scripts/validate-memory-os-parser-inflight-cancellation.py",
    "scripts/reconcile-memory-os-parser-inflight-cancellation.py",
    "scripts/reconcile-memory-os-chaos-inflight-overlay.py",
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


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    require(path.parent.is_dir(), f"authority parent missing: {path_label(path.parent)}")
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
        raise ReconcileFailure(f"cannot atomically write authority: {path_label(path)}: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass
            except OSError:
                pass


def require_exact_authority(path: Path, canonical: Path, label: str, *, optional: bool = False) -> None:
    require(path == canonical, f"{label} authority drift")
    if optional and not canonical.exists():
        return
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


def enforce_source_data_authorities() -> None:
    require_exact_authority(RESULT_PATH, CANONICAL_RESULT_PATH, "in-flight result", optional=True)
    require_exact_authority(
        PROCESS_GROUP_RESULT,
        CANONICAL_PROCESS_GROUP_RESULT,
        "process-group result",
        optional=True,
    )


def enforce_status_authority() -> None:
    if STATUS_PATH == CANONICAL_STATUS_PATH:
        require_exact_authority(STATUS_PATH, CANONICAL_STATUS_PATH, "production operability status")
        return
    require_external_fixture(STATUS_PATH, "production operability status")


def canonical_validator_path(path: Path) -> Path:
    try:
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise ReconcileFailure(f"canonical result validator missing or escapes repository: {path.name}") from exc
    require(resolved == Path("scripts") / path.name and path.is_file(),
            f"canonical result validator path drift: {path.name}")
    return path


def run_full_validator(path: Path) -> None:
    script = canonical_validator_path(path)
    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise ReconcileFailure(f"cannot execute canonical source validator: {path.name}") from exc
    require(type(result.returncode) is int and result.returncode == 0,
            f"canonical source validator rejected authority: {path.name}")


def load_result_validator(path: Path, module_name: str):
    canonical_validator_path(path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    require(spec is not None and spec.loader is not None,
            f"cannot load canonical result validator: {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    validator = getattr(module, "validate_result", None)
    require(callable(validator), f"canonical result validator missing validate_result: {path.name}")
    return validator


def validate_inflight_result(result: dict[str, Any]) -> None:
    try:
        load_result_validator(
            INFLIGHT_VALIDATOR,
            "memory_os_inflight_cancellation_for_chaos_overlay",
        )(result, None)
    except Exception as exc:
        if exc.__class__.__name__ in {"ValidationFailure", "ReconcileFailure"}:
            raise ReconcileFailure(f"in-flight cancellation authority invalid: {exc}") from exc
        raise


def process_group_reaping_complete() -> bool:
    if not PROCESS_GROUP_RESULT.is_file():
        return False
    run_full_validator(PROCESS_GROUP_VALIDATOR)
    try:
        load_result_validator(
            PROCESS_GROUP_VALIDATOR,
            "memory_os_process_group_reaping_for_inflight",
        )(load(PROCESS_GROUP_RESULT), None)
    except Exception as exc:
        if exc.__class__.__name__ in {"ValidationFailure", "ReconcileFailure"}:
            raise ReconcileFailure(f"process-group reaping authority invalid: {exc}") from exc
        raise
    return True


def run_post_write_validators() -> None:
    enforce_source_data_authorities()
    require_exact_authority(INFLIGHT_VALIDATOR, CANONICAL_INFLIGHT_VALIDATOR, "in-flight validator")
    require_exact_authority(
        PROCESS_GROUP_VALIDATOR,
        CANONICAL_PROCESS_GROUP_VALIDATOR,
        "process-group validator",
    )
    require_exact_authority(OPERABILITY_VALIDATOR, CANONICAL_OPERABILITY_VALIDATOR, "operability validator")
    if RESULT_PATH.is_file():
        run_full_validator(INFLIGHT_VALIDATOR)
    if PROCESS_GROUP_RESULT.is_file():
        run_full_validator(PROCESS_GROUP_VALIDATOR)
    run_full_validator(OPERABILITY_VALIDATOR)


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def normalize(status: dict[str, Any]) -> dict[str, Any]:
    enforce_source_data_authorities()
    require(status.get("productionDecision") == "NO_GO",
            "in-flight overlay requires productionDecision NO_GO")
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

    if RESULT_PATH.is_file():
        run_full_validator(INFLIGHT_VALIDATOR)
        validate_inflight_result(load(RESULT_PATH))
        while GAP in missing:
            missing.remove(GAP)
        if EVIDENCE not in existing:
            existing.append(EVIDENCE)
        if process_group_reaping_complete():
            while CHILD_REAPING_GAP in missing:
                missing.remove(CHILD_REAPING_GAP)
        elif CHILD_REAPING_GAP not in missing:
            missing.append(CHILD_REAPING_GAP)
        if HOST_RESTART_GAP not in missing:
            missing.append(HOST_RESTART_GAP)
        for ref in REFS:
            require((ROOT / ref).is_file(), f"in-flight evidence path missing: {ref}")
            if ref not in refs:
                refs.append(ref)
    else:
        while EVIDENCE in existing:
            existing.remove(EVIDENCE)
        if GAP not in missing:
            missing.append(GAP)
        for ref in REFS:
            while ref in refs:
                refs.remove(ref)

    gate["existingEvidence"] = unique(existing)
    gate["missingEvidence"] = unique(missing)
    gate["evidenceRefs"] = unique(refs)
    require(gate.get("status") == "PARTIAL", "OPS-P0-009 readiness changed unexpectedly")
    require(status.get("productionDecision") == "NO_GO",
            "production decision changed unexpectedly")
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    enforce_status_authority()
    current = load(STATUS_PATH)
    candidate = normalize(copy.deepcopy(current))
    candidate["asOf"] = dt.datetime.now(dt.timezone.utc).date().isoformat()
    left = copy.deepcopy(current)
    right = copy.deepcopy(candidate)
    left.pop("asOf", None)
    right.pop("asOf", None)
    changed = left != right

    if args.check:
        require(not changed, "in-flight chaos authority overlay is not normalized")
        if STATUS_PATH == CANONICAL_STATUS_PATH:
            run_post_write_validators()
        print("Memory OS in-flight chaos authority overlay check PASS")
        return 0
    if not changed:
        if STATUS_PATH == CANONICAL_STATUS_PATH:
            run_post_write_validators()
        print("Memory OS in-flight chaos authority overlay already normalized")
        return 0

    original_bytes = STATUS_PATH.read_bytes()
    payload = json.dumps(candidate, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    atomic_write_bytes(STATUS_PATH, payload)
    try:
        run_post_write_validators()
    except BaseException:
        atomic_write_bytes(STATUS_PATH, original_bytes)
        raise
    print("Normalized in-flight cancellation evidence within OPS-P0-009")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReconcileFailure as exc:
        print(f"CHAOS IN-FLIGHT OVERLAY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
