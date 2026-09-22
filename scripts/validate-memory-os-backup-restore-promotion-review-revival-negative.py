#!/usr/bin/env python3
"""Prove revoked human promotion authority cannot revive when its candidate returns."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-promotion-review.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location("promotion_review_revival_negative_writer", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load promotion review writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    writer = load_writer()
    decision_id = "brpr_revival_negative"
    row = {"decisionId": decision_id}
    registry = {
        "records": [row],
        "latestDecisionId": decision_id,
        "currentDecisionId": decision_id,
    }
    original_validate_history = writer.validate_registry_history
    original_expected_current = writer.expected_current_decision_id
    candidate_current = False

    def validate_history(value: dict[str, Any]) -> list[dict[str, Any]]:
        rows = value.get("records")
        require(rows == [row], "historical promotion review row drifted")
        require(value.get("latestDecisionId") == decision_id, "latest historical decision drifted")
        return rows

    def expected_current(_rows: list[dict[str, Any]]) -> str | None:
        return decision_id if candidate_current else None

    writer.validate_registry_history = validate_history
    writer.expected_current_decision_id = expected_current
    try:
        rows, current = writer.reconcile_current_decision(registry)
        require(rows == [row] and current is None, "candidate loss did not revoke current promotion authority")
        require(registry.get("currentDecisionId") is None, "revocation did not clear currentDecisionId")
        require(registry.get("records") == [row], "revocation mutated append-only review history")

        candidate_current = True
        try:
            writer.reconcile_current_decision(registry)
        except writer.Fail as exc:
            require(
                "promotion review current authority cannot be auto-created or repaired" in str(exc),
                f"candidate revival rejected at wrong boundary: {exc}",
            )
        else:
            raise Fail("revoked human promotion review automatically reactivated after candidate revival")

        require(registry.get("currentDecisionId") is None, "failed revival attempt restored current promotion authority")
        require(registry.get("records") == [row], "failed revival attempt mutated historical review")
    finally:
        writer.validate_registry_history = original_validate_history
        writer.expected_current_decision_id = original_expected_current

    print("Memory OS backup/restore promotion review revival negative PASS")
    print("candidate loss revoked current human promotion authority: true")
    print("historical promotion review preserved after revocation: true")
    print("candidate revival automatically reactivated revoked review: false")
    print("explicit new human promotion review still required: true")
    print("production evidence created: false")
    print("production traffic changed: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE PROMOTION REVIEW REVIVAL NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
