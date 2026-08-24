#!/usr/bin/env python3
"""Reconcile one exact-source local actual recovery-artifact rehearsal."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts/operations/local-migration-recovery-artifact-contract.v1.json"
REGISTRY_PATH = ROOT / "contracts/operations/migration-evidence-registry.v1.json"
REGISTRY_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-migration-evidence-registry.py"
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-local-migration-recovery-artifact.py"
LIFECYCLE_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-migration-lifecycle.py"
OPERABILITY_VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-operability.py"
RECONCILE_PATH = ROOT / "scripts/reconcile-memory-os-local-migration-recovery-artifact.py"
RUNNER_PATH = ROOT / "scripts/run-memory-os-local-migration-recovery-artifact.sh"
WORKFLOW_PATH = ROOT / ".github/workflows/local-migration-recovery-artifact.yml"
EVIDENCE_ROOT = ROOT / "docs/evidence/migrations/recovery"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Fail(f"cannot load {path.relative_to(ROOT)}: {exc}") from exc
    require(isinstance(value, dict), f"root must be object: {path.relative_to(ROOT)}")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


def append_once(values: list[Any], value: str) -> None:
    if value not in values:
        values.append(value)


def atomic_replace_bytes(path: Path, payload: bytes) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def validate_runtime_authority() -> None:
    for path, expected, label in (
        (
            VALIDATOR_PATH,
            ROOT / "scripts/validate-memory-os-local-migration-recovery-artifact.py",
            "local migration recovery-artifact validator",
        ),
        (
            REGISTRY_VALIDATOR_PATH,
            ROOT / "scripts/validate-memory-os-migration-evidence-registry.py",
            "migration evidence registry validator",
        ),
        (
            LIFECYCLE_VALIDATOR_PATH,
            ROOT / "scripts/validate-memory-os-migration-lifecycle.py",
            "migration lifecycle validator",
        ),
        (
            OPERABILITY_VALIDATOR_PATH,
            ROOT / "scripts/validate-memory-os-operability.py",
            "operability validator",
        ),
    ):
        require(path == expected, f"canonical {label} identity drift")
        require(path.is_file(), f"canonical {label} missing")
        require(not path.is_symlink(), f"canonical {label} must not be a symlink")
        try:
            require(path.resolve(strict=True) == expected, f"canonical {label} path drift")
        except OSError as exc:
            raise Fail(f"cannot resolve canonical {label}") from exc


def run_validator(path: Path, *args: str) -> None:
    completed = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=ROOT,
        check=False,
    )
    require(
        type(completed.returncode) is int and completed.returncode == 0,
        f"canonical validator rejected local migration recovery authority: {path.name}",
    )


def main() -> int:
    args = parse_args()
    validate_runtime_authority()
    result_path = EVIDENCE_ROOT / f"{args.run_id}.json"
    require(result_path.is_file(), f"recovery artifact result missing: {result_path.relative_to(ROOT)}")
    result = load(result_path)
    require(result.get("migrationRunId") == args.run_id, "result migrationRunId mismatch")
    source_sha = result.get("commitSha")
    require(isinstance(source_sha, str), "result commitSha missing")

    run_validator(
        VALIDATOR_PATH,
        "--path", str(result_path),
        "--expected-commit-sha", source_sha,
        "--require-result",
    )
    run_validator(REGISTRY_VALIDATOR_PATH)
    run_validator(LIFECYCLE_VALIDATOR_PATH)
    run_validator(OPERABILITY_VALIDATOR_PATH)

    registry = load(REGISTRY_PATH)
    records = registry.get("records")
    require(isinstance(records, list), "migration evidence registry records missing")
    matches = [row for row in records if isinstance(row, dict) and row.get("migrationRunId") == args.run_id]
    require(len(matches) == 1, "migration evidence registry must contain this run exactly once")
    record = matches[0]
    artifact = result.get("recoveryArtifact")
    require(isinstance(artifact, dict), "recoveryArtifact missing")
    require(record.get("sourceCommitSha") == source_sha, "registry source SHA mismatch")
    require(record.get("recoveryPointReference") == artifact.get("reference"),
            "registry recovery reference mismatch")
    require(record.get("recoveryPointArtifactDigest") == artifact.get("sha256"),
            "registry recovery digest mismatch")
    require(record.get("recoveryPointRestoreEvidenceRef") == str(result_path.relative_to(ROOT)),
            "registry actual restore evidence reference mismatch")
    require(record.get("preflightResult") == "PASS" and
            record.get("applyResult") == "PASS" and
            record.get("verificationResult") == "PASS",
            "registry rehearsal results must all PASS")

    contract = load(CONTRACT_PATH)
    readiness = contract.get("readiness")
    require(isinstance(readiness, dict), "local recovery artifact readiness missing")
    for flag in (
        "contractDefined", "runnerImplemented", "validatorImplemented",
        "automaticWorkflowImplemented", "exactSourceEvidenceCommitted",
        "localActualRecoveryArtifactRestoreProven",
    ):
        readiness[flag] = True
    readiness["productionEquivalentRecoveryArtifactRestoreProven"] = False
    readiness["productionReady"] = False
    refs = contract.setdefault("evidenceRefs", [])
    require(isinstance(refs, list), "local recovery artifact evidenceRefs must be list")
    for path in (
        CONTRACT_PATH,
        RUNNER_PATH,
        VALIDATOR_PATH,
        REGISTRY_VALIDATOR_PATH,
        RECONCILE_PATH,
        WORKFLOW_PATH,
        result_path,
    ):
        require(path.is_file(), f"local recovery artifact evidence missing: {path.relative_to(ROOT)}")
        append_once(refs, str(path.relative_to(ROOT)))

    original_contract = CONTRACT_PATH.read_bytes()
    payload = (json.dumps(contract, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    atomic_replace_bytes(CONTRACT_PATH, payload)
    try:
        run_validator(VALIDATOR_PATH)
        run_validator(REGISTRY_VALIDATOR_PATH)
        run_validator(LIFECYCLE_VALIDATOR_PATH)
        run_validator(OPERABILITY_VALIDATOR_PATH)
    except Exception:
        atomic_replace_bytes(CONTRACT_PATH, original_contract)
        raise

    print("Memory OS local migration recovery-artifact reconciliation PASS")
    print(f"run: {args.run_id}")
    print("local actual recovery artifact restore proven: true")
    print("production-equivalent recovery artifact restore proven: false")
    print("production ready: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"LOCAL MIGRATION RECOVERY ARTIFACT RECONCILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
