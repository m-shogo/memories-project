#!/usr/bin/env python3
"""Recover the full operability validator from the parent of the accidental truncation.

This is intentionally deterministic and fail-closed: it restores the exact
pre-truncation validator, then applies only the LOCAL_LONG_SOAK open-gap
transition. It refuses to write if the expected source anchors drift.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "scripts/validate-memory-os-operability.py"
BAD_COMMIT = "82e41d6643fc31e41597169d7e4bcc5f83aa67b5"

CONSTANT_ANCHOR = '''LIVE_LOAD_FOUNDATION_REFS = {
    "services/import-api/internal/httpserver/live_load_test.go",
    "services/import-api/internal/httpserver/live_object_load_test.go",
    LIVE_POSTGRES_CONTRACT_PATH.as_posix(),
    LIVE_OBJECT_CONTRACT_PATH.as_posix(),
    "scripts/validate-memory-os-live-load.py",
    "scripts/validate-memory-os-live-object-load.py",
    ".github/workflows/regenerate-live-postgres-load-results.yml",
}
'''
CONSTANT_REPLACEMENT = CONSTANT_ANCHOR + '''LONG_SOAK_CONTRACT_PATH = Path(
    "contracts/operations/sustained-local-soak-contract.v1.json"
)
LONG_SOAK_REVIEW_PATH = Path(
    "docs/fixtures/memory-os-operability/sustained-local-soak-trend-review.v1.json"
)
'''

LOAD_BLOCK_OLD = '''    if area.get("status") != "READY":
        for phrase in ("capacity boundary", "sustained soak", "production-equivalent"):
            if not any(phrase in item for item in missing):
                raise ValidationFailure(
                    f"OPS-P0-006: missingEvidence must retain the open gap: {phrase}"
                )
'''
LOAD_BLOCK_NEW = '''    if area.get("status") != "READY":
        for phrase in ("capacity boundary", "production-equivalent"):
            if not any(phrase in item for item in missing):
                raise ValidationFailure(
                    f"OPS-P0-006: missingEvidence must retain the open gap: {phrase}"
                )

        long_contract_path = repo_root / LONG_SOAK_CONTRACT_PATH
        long_review_path = repo_root / LONG_SOAK_REVIEW_PATH
        long_soak_completed = False
        if (
            LONG_SOAK_CONTRACT_PATH.as_posix() in refs
            and LONG_SOAK_REVIEW_PATH.as_posix() in refs
            and long_contract_path.is_file()
            and long_review_path.is_file()
        ):
            long_contract = load_json(long_contract_path)
            long_readiness = long_contract.get("readiness")
            long_review = load_json(long_review_path)
            if isinstance(long_readiness, dict):
                long_soak_completed = (
                    long_readiness.get("secondIndependentLongRunCommitted") is True
                    and long_readiness.get("trendReviewCompleted") is True
                    and long_readiness.get("localSustainedSoakEvidence") is True
                    and long_readiness.get("productionSustainedSoakEvidence") is False
                    and long_readiness.get("leakProofAvailable") is False
                    and long_review.get("trendReviewCompleted") is True
                    and long_review.get("localSustainedSoakEvidenceEligible") is True
                    and long_review.get("leakProof") is False
                    and long_review.get("productionEvidence") is False
                    and long_review.get("productionReady") is False
                )

        if long_soak_completed:
            if not any(
                "production-shaped" in item and "soak" in item
                for item in missing
            ):
                raise ValidationFailure(
                    "OPS-P0-006: completed local repeated soak must retain a distinct production-shaped soak gap"
                )
            if not any(
                "leak/stability" in item and "independent" in item
                for item in missing
            ):
                raise ValidationFailure(
                    "OPS-P0-006: local descriptive trend review must retain independent leak/stability review gap"
                )
        elif not any("sustained soak" in item for item in missing):
            raise ValidationFailure(
                "OPS-P0-006: missingEvidence must retain the open gap: sustained soak"
            )
'''


def git_show(spec: str) -> str:
    completed = subprocess.run(
        ["git", "show", spec],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"git show failed for {spec}: {completed.stderr[-1000:]}")
    return completed.stdout


def main() -> int:
    parent = git_show(f"{BAD_COMMIT}^:scripts/validate-memory-os-operability.py")
    if parent.count(CONSTANT_ANCHOR) != 1:
        raise RuntimeError("pre-truncation constant anchor drift")
    if parent.count(LOAD_BLOCK_OLD) != 1:
        raise RuntimeError("pre-truncation load-gap anchor drift")
    recovered = parent.replace(CONSTANT_ANCHOR, CONSTANT_REPLACEMENT, 1)
    recovered = recovered.replace(LOAD_BLOCK_OLD, LOAD_BLOCK_NEW, 1)
    TARGET.write_text(recovered, encoding="utf-8")
    print("Recovered full operability validator and applied LOCAL_LONG_SOAK gap transition")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"OPERABILITY VALIDATOR RECOVERY FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
