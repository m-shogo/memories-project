#!/usr/bin/env python3
"""Negative suite for canonical OPS-P0-007 production blocker ownership."""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_backup_restore_blocker_negative_target", VALIDATOR
    )
    require(spec is not None and spec.loader is not None, "cannot load backup/restore validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except Exception:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")


def status_with_mutation(module, mutate: Callable[[list[str]], None]) -> dict[str, Any]:
    status = copy.deepcopy(module.load(module.STATUS_PATH))
    area = next(
        row for row in status["areas"]
        if isinstance(row, dict) and row.get("id") == "OPS-P0-007"
    )
    missing = area.get("missingEvidence")
    require(isinstance(missing, list), "OPS-P0-007 missingEvidence missing in baseline")
    mutate(missing)
    return status


def run_with_status(module, status: dict[str, Any]) -> int:
    real_load = module.load

    def fake_load(path: Path) -> dict[str, Any]:
        if path == module.STATUS_PATH:
            return copy.deepcopy(status)
        return real_load(path)

    module.load = fake_load
    try:
        return module.main()
    finally:
        module.load = real_load


def main() -> int:
    module = load_module()
    baseline = copy.deepcopy(module.load(module.STATUS_PATH))
    require(run_with_status(module, baseline) == 0,
            "canonical six-blocker baseline must validate")
    print("PASS baseline: canonical six OPS-P0-007 production blockers")

    extra = status_with_mutation(
        module,
        lambda missing: missing.append(
            "production object backup with independently owned retention, deletion protection and lifecycle verification"
        ),
    )
    expect_rejected(
        "extra legacy production blocker cannot coexist with canonical six",
        lambda: run_with_status(module, extra),
    )

    removed = status_with_mutation(module, lambda missing: missing.pop())
    expect_rejected(
        "canonical production blocker cannot disappear",
        lambda: run_with_status(module, removed),
    )

    def replace_with_legacy(missing: list[str]) -> None:
        missing[0] = "production PostgreSQL backup schedule, independent retention and PITR configuration"

    substituted = status_with_mutation(module, replace_with_legacy)
    expect_rejected(
        "legacy blocker wording cannot substitute for canonical semantic authority",
        lambda: run_with_status(module, substituted),
    )

    def cross_domain_duplicate(missing: list[str]) -> None:
        missing[-1] = (
            "independent review of generation-bound recovery evidence after production PostgreSQL backup and PITR schedule validation"
        )

    duplicated = status_with_mutation(module, cross_domain_duplicate)
    expect_rejected(
        "one blocker row cannot duplicate another canonical blocker domain",
        lambda: run_with_status(module, duplicated),
    )

    print("Memory OS backup/restore canonical blocker negative suite PASS")
    print("canonical blocker count: 6")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE BLOCKER NEGATIVE SUITE FAILED: {exc}")
        raise SystemExit(1)
