#!/usr/bin/env python3
"""Typed self-test for the migration evidence writer derived from canonical authorities."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-migration-rehearsal-evidence.py"
VALIDATOR = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"
HELPER = ROOT / "scripts/memory_os_migration_recovery_point.py"
LIFECYCLE = ROOT / "contracts/operations/migration-lifecycle-contract.v1.json"
ARTIFACT_REF = "docs/fixtures/memory-os-operability/backup-restore-results.sample.v1.json"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"root must be object: {path.relative_to(ROOT)}")
    return value


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load module: {path.relative_to(ROOT)}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*args: str, expect_success: bool) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if expect_success and completed.returncode != 0:
        raise SystemExit(f"expected success: {' '.join(args)}\n{completed.stdout[-4000:]}")
    if not expect_success and completed.returncode == 0:
        raise SystemExit(f"negative case unexpectedly succeeded: {' '.join(args)}")
    return completed


def write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    lifecycle = load(LIFECYCLE)
    sequence = lifecycle.get("migrationSequence")
    if not isinstance(sequence, list) or not sequence or not all(isinstance(item, str) for item in sequence):
        raise SystemExit("canonical migrationSequence unavailable")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    helper = load_module(HELPER, "memory_os_migration_recovery_point_selftest")
    artifact_link = helper.build_migration_recovery_artifact_link(
        ROOT,
        artifact_ref=ARTIFACT_REF,
        environment="LOCAL_REHEARSAL",
    )

    base: dict[str, Any] = {
        "schemaVersion": "memory-os-migration-rehearsal-evidence.v1",
        "migrationRunId": "MIG-20260807T000001Z-selftesta",
        "environment": "LOCAL_REHEARSAL",
        "databaseIdentityDigest": "a" * 64,
        "sourceCommitSha": head,
        "migrationSequenceBefore": list(sequence),
        "migrationSequenceAfter": list(sequence),
        "startedAt": "2026-08-07T00:00:00Z",
        "completedAt": "2026-08-07T00:01:00Z",
        "operator": "operator_selftest",
        "reviewer": "reviewer_selftest",
        "recoveryPointReference": ARTIFACT_REF,
        "recoveryArtifactLink": artifact_link,
        "lockTimeoutMs": 1000,
        "statementTimeoutMs": 5000,
        "lockBudgetResult": "PASS",
        "preflightResult": "PASS",
        "applyResult": "PASS",
        "verificationResult": "PASS",
        "recoveryDecision": "FORWARD_FIX_NOT_REQUIRED",
        "openRisks": [],
        "productionTraffic": False,
        "productionCredentials": False,
        "productionEvidence": False,
        "productionReady": False,
    }

    with tempfile.TemporaryDirectory(prefix="memory-os-migration-evidence-selftest-") as temp:
        root = Path(temp)
        records = root / "records"
        records.mkdir()
        success = records / "success.json"
        write(success, base)
        ledger = root / "ledger"
        run("python", str(WRITER), "--record", str(success), "--ledger-root", str(ledger), expect_success=True)
        run("python", str(VALIDATOR), "--ledger-root", str(ledger), expect_success=True)

        registered = load(ledger / f"{base['migrationRunId']}.json")
        checks = registered.get("recoveryArtifactChecks", {})
        expected_checks = {
            "artifactExists": True,
            "artifactSha256Matches": True,
            "artifactSourceCommitMatches": True,
            "artifactResultPass": True,
            "artifactIntegrityPass": True,
            "backupIdentityDigestMatches": True,
            "verificationRefMatches": True,
        }
        for key, expected in expected_checks.items():
            if checks.get(key) is not expected:
                raise SystemExit(f"success-case recovery check drift: {key}={checks.get(key)!r}")
        if registered.get("recoveryArtifactLink", {}).get("artifactVerified") is not True:
            raise SystemExit("success-case artifactVerified must be true")

        bad_recovery = copy.deepcopy(base)
        bad_recovery["migrationRunId"] = "MIG-20260807T000002Z-selftestb"
        bad_recovery["recoveryPointReference"] = "docs/fixtures/memory-os-operability/not-a-recovery-artifact.json"
        bad_recovery["recoveryArtifactLink"]["artifactRef"] = bad_recovery["recoveryPointReference"]
        bad_recovery_path = records / "bad-recovery.json"
        write(bad_recovery_path, bad_recovery)
        run("python", str(WRITER), "--record", str(bad_recovery_path), "--ledger-root", str(root / "ledger-bad-recovery"), expect_success=False)

        bad_environment = copy.deepcopy(base)
        bad_environment["migrationRunId"] = "MIG-20260807T000003Z-selftestc"
        bad_environment["environment"] = "PRODUCTION"
        bad_environment_path = records / "bad-environment.json"
        write(bad_environment_path, bad_environment)
        run("python", str(WRITER), "--record", str(bad_environment_path), "--ledger-root", str(root / "ledger-bad-environment"), expect_success=False)

        bad_skew = copy.deepcopy(base)
        bad_skew["migrationRunId"] = "MIG-20260807T000004Z-selftestd"
        bad_skew["recoveryArtifactLink"]["artifactSha256"] = "b" * 64
        bad_skew_path = records / "bad-skew.json"
        write(bad_skew_path, bad_skew)
        run("python", str(WRITER), "--record", str(bad_skew_path), "--ledger-root", str(root / "ledger-bad-skew"), expect_success=False)

    print("Memory OS migration evidence typed self-test PASS")
    print(f"canonical migrations exercised: {len(sequence)}")
    print("recovery artifact link derived from canonical exact-source restore result")
    print("negative cases: missing artifact, production relabel, digest skew rejected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
