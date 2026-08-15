#!/usr/bin/env python3
"""Negative suite for typed, append-only generation independent reviews."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-generation-independent-review.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_generation_independent_review_validator_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load independent review validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def head_sha() -> str:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    require(completed.returncode == 0, "cannot resolve HEAD")
    value = completed.stdout.strip()
    require(len(value) == 40, "HEAD sha invalid")
    return value


def expect_fail(module, registry: dict, label: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as handle:
        path = Path(handle.name)
        json.dump(registry, handle)
        handle.write("\n")
    original = module.REGISTRY
    try:
        module.REGISTRY = path
        try:
            module.main()
        except module.Fail:
            return
        raise Fail(f"negative case unexpectedly passed: {label}")
    finally:
        module.REGISTRY = original
        path.unlink(missing_ok=True)


def base_row() -> dict:
    return {
        "evidenceId": "brge_negative_review_authority",
        "sourceCommitSha": head_sha(),
        "securityReviewRef": "README.md",
        "operabilityReviewRef": "SECURITY.md",
    }


def registry(row: dict) -> dict:
    return {
        "schemaVersion": "memory-os-backup-restore-generation-evidence-registry.v1",
        "appendOnly": True,
        "registeredEvidenceCount": 1,
        "drillRequestBoundEvidenceCount": 1,
        "completeGenerationBoundBackupCount": 0,
        "completeGenerationBoundRestoreCount": 0,
        "productionEquivalentRecoveryCandidateCount": 0,
        "records": [row],
        "productionEvidence": False,
        "productionReady": False,
    }


def main() -> int:
    module = load_validator()

    expect_fail(module, registry(base_row()), "generic repository review refs")

    same_ref = base_row()
    same_ref["securityReviewRef"] = "docs/evidence/backup-restore/README.md"
    same_ref["operabilityReviewRef"] = "docs/evidence/backup-restore/README.md"
    expect_fail(module, registry(same_ref), "security/operability ref reuse")

    production_boundary = registry(base_row())
    production_boundary["productionReady"] = True
    expect_fail(module, production_boundary, "productionReady promotion")

    original_history = module.git_history
    try:
        module.git_history = lambda _ref, _field: ["a" * 40, "b" * 40]
        try:
            module.require_append_only_review(
                "docs/evidence/backup-restore/synthetic-review.json",
                Path("/tmp/not-read-after-history-rejection"),
                "securityReviewRef",
            )
        except module.Fail:
            pass
        else:
            raise Fail("review evidence edited after first commit was accepted")
    finally:
        module.git_history = original_history

    print("PASS: generation independent review negatives reject generic refs, review reuse, post-commit edits, and production promotion")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
