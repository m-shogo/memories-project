#!/usr/bin/env python3
"""Run the generation-binding read-only suite and prove canonical authority modes are immutable."""

from __future__ import annotations

import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITIES = (
    ROOT / "contracts/operations/backup-restore-generation-binding-contract.v1.json",
    ROOT / "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
    ROOT / "contracts/operations/recovery-objectives-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-drill-request-registry.v1.json",
    ROOT / "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
    ROOT / "contracts/operations/operability-admission-inventory.v1.json",
    ROOT / "contracts/operations/production-operability-status.json",
)
SUITE = (
    ROOT / "scripts/validate-memory-os-recovery-objectives.py",
    ROOT / "scripts/validate-memory-os-backup-restore-generation-evidence.py",
    ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-registry-aggregate-negative.py",
    ROOT / "scripts/validate-memory-os-backup-restore-generation-binding.py",
    ROOT / "scripts/validate-memory-os-backup-restore-generation-binding-negative.py",
    ROOT / "scripts/validate-memory-os-backup-restore-generation-status-authority-negative.py",
    ROOT / "scripts/reconcile-memory-os-backup-restore-generation-status.py",
    ROOT / "scripts/validate-memory-os-backup-restore.py",
    ROOT / "scripts/validate-memory-os-operability.py",
)


WORKFLOW = ROOT / ".github/workflows/backup-restore-generation-binding-readonly.yml"
TRIGGER_SCRIPTS = (Path(__file__).resolve(), *SUITE)


def validate_trigger_reachability(source: str) -> None:
    """Require both independent CI events to include every executed script."""
    pr_marker = "  pull_request:\n    paths:\n"
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    dispatch_marker = "  workflow_dispatch:\n"
    for marker in (pr_marker, push_marker, dispatch_marker):
        if source.count(marker) != 1:
            raise SystemExit(f"generation-binding readonly trigger marker drift: {marker.strip()}")
    pr_block = source.split(pr_marker, 1)[1].split(push_marker, 1)[0]
    push_block = source.split(push_marker, 1)[1].split(dispatch_marker, 1)[0]
    for event, block in (("pull_request", pr_block), ("push", push_block)):
        for path in TRIGGER_SCRIPTS:
            token = f'      - "{path.relative_to(ROOT).as_posix()}"\n'
            if block.count(token) != 1:
                raise SystemExit(
                    f"generation-binding readonly {event} trigger missing or duplicate: {path.relative_to(ROOT)}"
                )


def prove_trigger_reachability_negatives(source: str) -> None:
    """Remove each protected path from each event independently; require rejection."""
    push_marker = "  push:\n    branches: [so]\n    paths:\n"
    for event in ("pull_request", "push"):
        for path in TRIGGER_SCRIPTS:
            token = f'      - "{path.relative_to(ROOT).as_posix()}"\n'
            if source.count(token) != 2:
                raise SystemExit(f"generation-binding trigger negative anchor drift: {path}")
            if event == "pull_request":
                mutated = source.replace(token, "", 1)
            else:
                prefix, suffix = source.split(push_marker, 1)
                mutated = prefix + push_marker + suffix.replace(token, "", 1)
            try:
                validate_trigger_reachability(mutated)
            except SystemExit:
                continue
            raise SystemExit(f"generation-binding trigger negative accepted: {event} {path}")
    print(f"PASS: generation-binding readonly trigger reachability ({len(TRIGGER_SCRIPTS) * 2} removal negatives)")




def snapshot() -> dict[Path, tuple[bytes, int]]:
    result: dict[Path, tuple[bytes, int]] = {}
    for path in AUTHORITIES:
        if not path.is_file():
            raise SystemExit(f"missing canonical authority: {path.relative_to(ROOT)}")
        result[path] = (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
    return result


def main() -> int:
    source = WORKFLOW.read_text(encoding="utf-8")
    validate_trigger_reachability(source)
    prove_trigger_reachability_negatives(source)
    before = snapshot()
    for script in SUITE:
        subprocess.run(["python", str(script)], cwd=ROOT, check=True)
    after = snapshot()
    for path, (before_bytes, before_mode) in before.items():
        after_bytes, after_mode = after[path]
        if after_bytes != before_bytes:
            raise SystemExit(f"canonical authority bytes mutated: {path.relative_to(ROOT)}")
        if after_mode != before_mode:
            raise SystemExit(
                f"canonical authority mode mutated: {path.relative_to(ROOT)} "
                f"{before_mode:o}->{after_mode:o}"
            )
    print(f"PASS read-only: generation-binding suite preserved bytes/modes for {len(AUTHORITIES)} canonical authorities")
    print("production evidence created: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
