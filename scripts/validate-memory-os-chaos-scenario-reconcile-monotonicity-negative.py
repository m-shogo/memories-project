#!/usr/bin/env python3
"""Prevent scenario-specific chaos reconcilers from restoring superseded coarse gaps."""

from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "contracts/operations/production-operability-status.json"
CANONICAL = ROOT / "scripts/reconcile-memory-os-chaos-authority.py"
INFLIGHT_OVERLAY = ROOT / "scripts/reconcile-memory-os-chaos-inflight-overlay.py"
SCENARIOS = (
    ROOT / "scripts/reconcile-memory-os-chaos-failure-drills.py",
    ROOT / "scripts/reconcile-memory-os-chaos-failure-drills-v2.py",
    ROOT / "scripts/reconcile-memory-os-parser-restart-matrix.py",
    ROOT / "scripts/reconcile-memory-os-parser-inflight-cancellation.py",
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_canonical_source_delegation(canonical, current: dict) -> None:
    original_runner = canonical.run_canonical_validator
    calls: list[str] = []
    try:
        canonical.run_canonical_validator = lambda script_name: calls.append(script_name)
        canonical.validate_canonical_source_authorities()
    finally:
        canonical.run_canonical_validator = original_runner

    database_result = json.loads(canonical.DATABASE_RESULT.read_text(encoding="utf-8"))
    assertions = database_result.get("assertions", {})
    expected = [canonical.OBJECT_VALIDATOR, canonical.PARSER_VALIDATOR]
    if isinstance(assertions, dict) and assertions.get("sameSpoolIdReused") is True:
        expected.append(canonical.DATABASE_VALIDATOR)
    if calls != expected:
        raise RuntimeError(f"canonical chaos source-validator delegation drift: {calls} != {expected}")

    original_runner = canonical.run_canonical_validator
    try:
        def reject_source(_script_name: str) -> None:
            raise canonical.ReconcileFailure("synthetic canonical source rejection")

        canonical.run_canonical_validator = reject_source
        try:
            canonical.normalized_status(copy.deepcopy(current))
        except canonical.ReconcileFailure as exc:
            if "synthetic canonical source rejection" not in str(exc):
                raise RuntimeError(f"unexpected canonical source rejection: {exc}") from exc
        else:
            raise RuntimeError("canonical chaos reconcile accepted rejected source authority")
    finally:
        canonical.run_canonical_validator = original_runner


def validate_inflight_source_delegation(current: dict) -> None:
    overlay = load_module(INFLIGHT_OVERLAY, "memory_os_chaos_inflight_delegation")
    if not overlay.RESULT_PATH.is_file():
        return
    result = overlay.load(overlay.RESULT_PATH)
    original_loader = overlay.load_result_validator
    calls: list[Path] = []
    try:
        def accept_loader(path: Path, _module_name: str):
            calls.append(path)
            return lambda _result, _expected_sha: None

        overlay.load_result_validator = accept_loader
        overlay.validate_inflight_result(result)
    finally:
        overlay.load_result_validator = original_loader
    if calls != [overlay.INFLIGHT_VALIDATOR]:
        raise RuntimeError(f"in-flight overlay validator delegation drift: {calls}")

    try:
        def reject_loader(_path: Path, _module_name: str):
            def reject(_result, _expected_sha) -> None:
                raise overlay.ReconcileFailure("synthetic in-flight source rejection")
            return reject

        overlay.load_result_validator = reject_loader
        try:
            overlay.validate_inflight_result(result)
        except overlay.ReconcileFailure as exc:
            if "synthetic in-flight source rejection" not in str(exc):
                raise RuntimeError(f"unexpected in-flight source rejection: {exc}") from exc
        else:
            raise RuntimeError("in-flight overlay accepted rejected canonical source authority")
    finally:
        overlay.load_result_validator = original_loader

    original_full_runner = overlay.run_full_validator
    full_calls: list[Path] = []
    try:
        def reject_full(path: Path) -> None:
            full_calls.append(path)
            raise overlay.ReconcileFailure("synthetic full in-flight source rejection")

        overlay.run_full_validator = reject_full
        try:
            overlay.normalize(copy.deepcopy(current))
        except overlay.ReconcileFailure as exc:
            if "synthetic full in-flight source rejection" not in str(exc):
                raise RuntimeError(f"unexpected full in-flight source rejection: {exc}") from exc
        else:
            raise RuntimeError("in-flight overlay accepted rejected full canonical source authority")
    finally:
        overlay.run_full_validator = original_full_runner
    if full_calls != [overlay.INFLIGHT_VALIDATOR]:
        raise RuntimeError(f"full in-flight source validation did not precede mutation: {full_calls}")


def main() -> int:
    canonical = load_module(CANONICAL, "memory_os_chaos_monotonicity_canonical")
    current = json.loads(STATUS.read_text(encoding="utf-8"))
    validate_canonical_source_delegation(canonical, current)
    validate_inflight_source_delegation(current)

    gate = next(
        item for item in current["areas"]
        if isinstance(item, dict) and item.get("id") == "OPS-P0-009"
    )
    missing = gate.get("missingEvidence")
    if not isinstance(missing, list):
        raise RuntimeError("OPS-P0-009 missingEvidence is not a list")
    for coarse in canonical.COARSE_GAPS:
        if coarse not in missing:
            missing.append(coarse)

    for index, path in enumerate(SCENARIOS):
        module = load_module(path, f"memory_os_chaos_scenario_{index}")
        with tempfile.TemporaryDirectory(prefix="memory-os-chaos-monotonicity-") as tmp:
            temp_status = Path(tmp) / "status.json"
            temp_status.write_text(
                json.dumps(copy.deepcopy(current), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            original_status = module.STATUS_PATH
            module.STATUS_PATH = temp_status
            try:
                result = module.main()
            finally:
                module.STATUS_PATH = original_status
            if result != 0:
                raise RuntimeError(f"scenario reconcile returned nonzero: {path.name}")
            reconciled = json.loads(temp_status.read_text(encoding="utf-8"))
            reconciled_gate = next(
                item for item in reconciled["areas"]
                if isinstance(item, dict) and item.get("id") == "OPS-P0-009"
            )
            reconciled_missing = reconciled_gate.get("missingEvidence")
            if not isinstance(reconciled_missing, list):
                raise RuntimeError(f"scenario reconcile lost missingEvidence list: {path.name}")
            restored = [item for item in canonical.COARSE_GAPS if item in reconciled_missing]
            if restored:
                raise RuntimeError(f"scenario reconcile restored coarse gaps in {path.name}: {restored}")
            if reconciled.get("productionDecision") != "NO_GO":
                raise RuntimeError(f"scenario reconcile changed production decision: {path.name}")

    print("PASS: chaos reconcile delegates full canonical source validation and preserves stronger missing-evidence authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
