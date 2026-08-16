#!/usr/bin/env python3
"""Reject corrupted environment-generation authority before host-failure admission."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-deletion-worker-host-failure.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def write(value: dict[str, Any]) -> None:
    REGISTRY.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rejected(label: str, mutate: Callable[[dict[str, Any]], None], baseline: dict[str, Any], baseline_bytes: bytes) -> None:
    candidate = copy.deepcopy(baseline)
    mutate(candidate)
    write(candidate)
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(completed.returncode != 0, f"{label}: corrupt generation authority was accepted")
    REGISTRY.write_bytes(baseline_bytes)
    require(REGISTRY.read_bytes() == baseline_bytes, f"{label}: canonical generation registry was not restored")


def main() -> int:
    baseline_bytes = REGISTRY.read_bytes()
    baseline = json.loads(baseline_bytes.decode("utf-8"))
    require(isinstance(baseline, dict), "baseline generation registry root must be object")
    try:
        cases: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
            ("registry class drift", lambda value: value.__setitem__("registryClass", "FORGED_GENERATIONS")),
            ("append-only disabled", lambda value: value.__setitem__("appendOnly", False)),
            ("boolean generation count", lambda value: value.__setitem__("registeredGenerationCount", False)),
            ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
            ("empty registry current pointer", lambda value: value.__setitem__("currentGenerationId", "forged-generation")),
        ]
        for label, mutate in cases:
            rejected(label, mutate, baseline, baseline_bytes)
    finally:
        REGISTRY.write_bytes(baseline_bytes)
    print("PASS: deletion host-failure admission rejects corrupted generation authority")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"DELETION HOST FAILURE GENERATION NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
