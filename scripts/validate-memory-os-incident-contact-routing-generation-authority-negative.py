#!/usr/bin/env python3
"""Reject corrupt environment-generation authority before contact-routing admission."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN_REGISTRY = ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json"
VALIDATOR = ROOT / "scripts/validate-memory-os-incident-contact-routing.py"


def expect_rejected(label: str) -> None:
    completed = subprocess.run(
        ["python", str(VALIDATOR)],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        return
    raise RuntimeError(f"contact-routing validator accepted corrupt generation authority: {label}")


def main() -> int:
    original = GEN_REGISTRY.read_bytes()
    registry = json.loads(original.decode("utf-8"))
    cases: list[tuple[str, dict]] = []

    candidate = copy.deepcopy(registry)
    candidate["appendOnly"] = False
    cases.append(("append-only disabled", candidate))

    candidate = copy.deepcopy(registry)
    candidate["registeredGenerationCount"] = True
    cases.append(("boolean generation count", candidate))

    candidate = copy.deepcopy(registry)
    candidate["productionEvidence"] = True
    cases.append(("production evidence escalation", candidate))

    try:
        for label, candidate in cases:
            GEN_REGISTRY.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
            expect_rejected(label)
    finally:
        GEN_REGISTRY.write_bytes(original)

    if GEN_REGISTRY.read_bytes() != original:
        raise RuntimeError("generation authority negative failed to restore registry")

    print("PASS: contact routing rejects corrupt environment-generation authority before admission")
    print("production evidence generated: false")
    print("production readiness changed: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
