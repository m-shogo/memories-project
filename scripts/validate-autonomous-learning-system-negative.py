#!/usr/bin/env python3
"""Negative suite proving the autonomous learning guard fails closed."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path("contracts/operations/autonomous-learning-system.json")
LEARNING = Path("docs/operations/AUTONOMOUS-OPS-LEARNING.md")
VALIDATOR = Path("scripts/validate-autonomous-learning-system.py")
NEGATIVE_VALIDATOR = Path("scripts/validate-autonomous-learning-system-negative.py")


def seed(root: Path) -> None:
    # The positive validator verifies both executable guard bindings. Seed the
    # complete canonical guard set so the positive control proves a real pass
    # before any negative mutation is applied.
    for rel in (CONTRACT, LEARNING, VALIDATOR, NEGATIVE_VALIDATOR):
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)


def run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / VALIDATOR), "--repo-root", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )


def require_failure(name: str, mutate) -> None:
    with tempfile.TemporaryDirectory(prefix="learning-negative-") as tmp:
        root = Path(tmp)
        seed(root)
        mutate(root)
        result = run(root)
        if result.returncode == 0:
            raise RuntimeError(f"negative case unexpectedly passed: {name}")
        if "AUTONOMOUS LEARNING VALIDATION FAILED" not in result.stderr:
            raise RuntimeError(f"negative case did not fail through canonical guard: {name}: {result.stderr}")


def edit_contract(root: Path, edit) -> None:
    path = root / CONTRACT
    data = json.loads(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="learning-positive-") as tmp:
        root = Path(tmp)
        seed(root)
        result = run(root)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            return 1

    cases = [
        ("weaken mandatory rule", lambda root: edit_contract(root, lambda d: d["rules"].__setitem__("unchangedBlockerIsNotRetried", False))),
        ("weaken NO_GO default", lambda root: edit_contract(root, lambda d: d["protectedInvariants"].__setitem__("productionDecisionDefault", "GO"))),
        ("break executable guard binding", lambda root: edit_contract(root, lambda d: d.__setitem__("validator", "scripts/other.py"))),
        ("break negative guard binding", lambda root: edit_contract(root, lambda d: d.__setitem__("negativeValidator", "scripts/other-negative.py"))),
        ("remove learning authority", lambda root: (root / LEARNING).unlink()),
        ("remove executable guard", lambda root: (root / VALIDATOR).unlink()),
        ("remove negative guard", lambda root: (root / NEGATIVE_VALIDATOR).unlink()),
        ("drop anti-regression lesson", lambda root: (root / LEARNING).write_text((root / LEARNING).read_text(encoding="utf-8").replace("Repeating a known failed approach without changed preconditions is a regression", "known failures may be retried"), encoding="utf-8")),
    ]
    for name, mutate in cases:
        require_failure(name, mutate)

    print(f"Autonomous learning negative validation PASS ({len(cases)} fail-closed cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
