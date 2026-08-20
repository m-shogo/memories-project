#!/usr/bin/env python3
"""Prove Preview pre-fence proof reconcile rolls back after canonical rejection."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECONCILER = ROOT / "scripts/reconcile-memory-os-deletion-prefence-linearization.py"
SOURCE_SHA = "3" * 40


def load_module():
    spec = importlib.util.spec_from_file_location("prefence_proof_reconcile", RECONCILER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pre-fence proof reconciler")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    module = load_module()
    with tempfile.TemporaryDirectory(prefix="memory-os-prefence-proof-") as tmp:
        root = Path(tmp)
        contract = root / "contract.json"
        result = root / "result.json"
        validator = root / "validator.py"
        write_json(
            contract,
            {
                "readiness": {},
                "evidenceBoundary": {
                    "productionEvidence": False,
                    "productionEquivalentDependencies": False,
                    "previewReadSurfaceOnly": True,
                },
            },
        )
        write_json(
            result,
            {
                "commitSha": SOURCE_SHA,
                "scenario": {
                    "result": "PASS",
                    "integrityResult": "PASS",
                    "authenticatedBeforeFence": 32,
                    "unauthorizedAfterFence": 32,
                    "unexpectedStatusCount": 0,
                    "transportErrors": 0,
                },
            },
        )

        module.ROOT = root
        module.CONTRACT_PATH = contract
        module.RESULT_PATH = result
        module.VALIDATOR = validator
        before = contract.read_bytes()
        previous = os.environ.get("EXPECTED_COMMIT_SHA")
        os.environ["EXPECTED_COMMIT_SHA"] = SOURCE_SHA
        calls: list[list[str]] = []

        def fake_run(command, *, cwd, check):
            calls.append(list(command))
            if cwd != root or check is not True:
                raise AssertionError("validator invocation lost fail-closed execution options")
            raise subprocess.CalledProcessError(1, command)

        module.subprocess.run = fake_run
        try:
            try:
                module.main()
            except subprocess.CalledProcessError:
                pass
            else:
                raise AssertionError("canonical validator rejection must fail pre-fence proof reconcile")
        finally:
            if previous is None:
                os.environ.pop("EXPECTED_COMMIT_SHA", None)
            else:
                os.environ["EXPECTED_COMMIT_SHA"] = previous

        if contract.read_bytes() != before:
            raise AssertionError("pre-fence proof contract changed after rejected reconcile")
        expected = ["python", str(validator), "--require-result", "--expected-commit-sha", SOURCE_SHA]
        if calls != [expected]:
            raise AssertionError(f"validator invocation drift: {calls!r}")

    print("PASS: pre-fence proof reconcile rolls back after canonical rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
