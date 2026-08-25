#!/usr/bin/env python3
"""Prove the canonical OPS-P0-007 six-blocker helper cannot be rebound at runtime."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/memory_os_backup_restore_blockers.py"
SEMANTIC_OVERLAY = ROOT / "scripts/reconcile-memory-os-backup-semantic-overlay.py"
STATUS = ROOT / "contracts/operations/production-operability-status.json"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    require(HELPER.is_file() and not HELPER.is_symlink(), "canonical blocker helper missing or symlinked")
    require(HELPER.resolve(strict=True).relative_to(ROOT.resolve()) == HELPER.relative_to(ROOT), "canonical blocker helper path drift")
    spec = importlib.util.spec_from_file_location("memory_os_backup_restore_blocker_authority_negative", HELPER)
    require(spec is not None and spec.loader is not None, "cannot load canonical blocker helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_semantic_overlay():
    require(SEMANTIC_OVERLAY.is_file() and not SEMANTIC_OVERLAY.is_symlink(), "canonical semantic overlay missing or symlinked")
    require(SEMANTIC_OVERLAY.resolve(strict=True).relative_to(ROOT.resolve()) == SEMANTIC_OVERLAY.relative_to(ROOT), "canonical semantic overlay path drift")
    spec = importlib.util.spec_from_file_location("memory_os_backup_semantic_overlay_authority_negative", SEMANTIC_OVERLAY)
    require(spec is not None and spec.loader is not None, "cannot load canonical semantic overlay")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ops7_missing_evidence() -> list[str]:
    import json

    status = json.loads(STATUS.read_text(encoding="utf-8"))
    rows = status.get("areas")
    require(isinstance(rows, list), "production status areas missing")
    ops7 = next((row for row in rows if isinstance(row, dict) and row.get("id") == "OPS-P0-007"), None)
    require(isinstance(ops7, dict), "OPS-P0-007 status missing")
    missing = ops7.get("missingEvidence")
    require(isinstance(missing, list), "OPS-P0-007 missingEvidence missing")
    return missing


def expect_rejected(module: Any, field: str, replacement: Any, value: list[str]) -> None:
    original = getattr(module, field)
    setattr(module, field, replacement)
    rejected = False
    try:
        module.require_canonical_gaps(value, module.RuntimeError if hasattr(module, "RuntimeError") else RuntimeError)
    except RuntimeError as exc:
        require("canonical OPS-P0-007 blocker authority drift" in str(exc), f"{field} rejected at unexpected boundary: {exc}")
        rejected = True
    finally:
        setattr(module, field, original)
    require(rejected, f"canonical blocker helper accepted substituted {field}")


def expect_overlay_rejected(overlay: Any, name: str, field: str, replacement: Any) -> None:
    original = getattr(overlay, field)
    setattr(overlay, field, replacement)
    try:
        rejected = False
        try:
            overlay.main()
        except overlay.ReconcileFailure:
            rejected = True
        require(rejected, f"semantic overlay accepted substituted {name}")
    finally:
        setattr(overlay, field, original)


def main() -> int:
    module = load_module()
    value = ops7_missing_evidence()
    status_before = STATUS.read_bytes()
    baseline = tuple(module.CANONICAL_GAPS)
    require(len(baseline) == 6, "canonical blocker count must remain six")
    require(value == list(baseline), "Production Status does not match canonical blocker helper")
    require(module.require_canonical_gaps(value, RuntimeError) == value, "clean canonical blocker authority rejected")

    replacement = tuple(reversed(baseline))
    expect_rejected(module, "CANONICAL_GAPS", replacement, value)
    expect_rejected(module, "_IMMUTABLE_CANONICAL_GAPS", replacement, value)

    reordered = list(reversed(value))
    rejected = False
    try:
        module.require_canonical_gaps(reordered, RuntimeError)
    except RuntimeError:
        rejected = True
    require(rejected, "canonical blocker helper accepted reordered blockers")

    replaced = list(value)
    replaced[0] = "fabricated replacement blocker"
    rejected = False
    try:
        module.require_canonical_gaps(replaced, RuntimeError)
    except RuntimeError:
        rejected = True
    require(rejected, "canonical blocker helper accepted replaced blocker content")

    overlay = load_semantic_overlay()
    expect_overlay_rejected(overlay, "blocker validator", "require_canonical_gaps", lambda *args, **kwargs: args[0] if args else None)
    expect_overlay_rejected(overlay, "runtime authority guard", "validate_runtime_authority", lambda: None)
    expect_overlay_rejected(overlay, "status loader", "load", lambda path: {"productionDecision": "NO_GO", "areas": []})
    expect_overlay_rejected(overlay, "semantic validator", "validate", lambda status: None)
    expect_overlay_rejected(overlay, "Production Status path", "STATUS_PATH", ROOT / "contracts/operations/operability-admission-inventory.v1.json")
    expect_overlay_rejected(overlay, "repository root", "ROOT", ROOT / "scripts")

    require(tuple(module.CANONICAL_GAPS) == baseline, "negative probes mutated canonical blocker authority")
    require(ops7_missing_evidence() == value, "negative probes mutated canonical Production Status blockers")
    require(STATUS.read_bytes() == status_before, "semantic overlay authority probes mutated canonical Production Status")

    print("Memory OS backup/restore blocker authority negative PASS")
    print("canonical blocker count: 6")
    print("runtime blocker tuple substitution accepted: false")
    print("runtime immutable blocker authority substitution accepted: false")
    print("blocker reordering accepted: false")
    print("blocker replacement accepted: false")
    print("semantic blocker validator substitution accepted: false")
    print("semantic runtime guard substitution accepted: false")
    print("semantic status loader substitution accepted: false")
    print("semantic validator substitution accepted: false")
    print("semantic Production Status path substitution accepted: false")
    print("semantic repository root substitution accepted: false")
    print("Production Status blockers mutated: false")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, OSError) as exc:
        print(f"BACKUP RESTORE BLOCKER AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
