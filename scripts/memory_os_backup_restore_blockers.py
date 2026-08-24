#!/usr/bin/env python3
"""Canonical OPS-P0-007 production blocker authority.

Local restore evidence and generation-bound admission layers may add evidence,
but they must not invent, split, merge, remove, or reorder these blockers.
"""

from __future__ import annotations

from typing import Any

_IMMUTABLE_CANONICAL_GAPS: tuple[str, ...] = (
    "production PostgreSQL backup and PITR schedule with encrypted independent retention, WAL continuity and tested point-in-time recovery selection",
    "production independent object backup retention with TLS, restore-only credential separation, deletion protection, immutability, lifecycle controls and provider durability evidence",
    "approved and measured RPO and RTO under production-shaped recovery, with coherent PostgreSQL/object recovery-point skew measurement plus backup monitoring, freshness enforcement and paging",
    "production-shaped cross-cluster isolated restore drill with an approved recovery owner, coherent PostgreSQL and exact object-version recovery points, and an explicit promotion decision",
    "production deletion, expired/revoked-session, replay, idempotency and lease non-resurrection verification after restore",
    "independent review of generation-bound recovery evidence, security/privacy invariants, measured objectives and the restore promotion decision",
)
CANONICAL_GAPS: tuple[str, ...] = _IMMUTABLE_CANONICAL_GAPS


def require_canonical_gaps(
    value: Any,
    fail_type: type[Exception] = RuntimeError,
    canonical_gaps: tuple[str, ...] = _IMMUTABLE_CANONICAL_GAPS,
) -> list[str]:
    if CANONICAL_GAPS != canonical_gaps or _IMMUTABLE_CANONICAL_GAPS != canonical_gaps:
        raise fail_type("canonical OPS-P0-007 blocker authority drift")
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise fail_type("OPS-P0-007 missingEvidence must be a list of strings")
    if value != list(canonical_gaps):
        raise fail_type(
            "OPS-P0-007 missingEvidence must equal the ordered canonical six production blockers"
        )
    return value
