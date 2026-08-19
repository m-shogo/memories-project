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
SCENARIOS = (
    ROOT / "scripts/reconcile-memory-os-chaos-failure-drills.py",
    ROOT / "scripts/reconcile-memory-os-chaos-failure-drills-v2.py",
    ROOT / "scripts/reconcile-memory-os-parser-restart-matrix.py",
)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    canonical = load_module(CANONICAL, "memory_os_chaos_monotonicity_canonical")
    current = json.loads(STATUS.read_text(encoding="utf-8"))
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

    print("PASS: scenario-specific chaos reconcilers preserve canonical stronger missing-evidence authority")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
