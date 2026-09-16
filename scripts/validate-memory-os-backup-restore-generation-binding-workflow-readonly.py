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


def snapshot() -> dict[Path, tuple[bytes, int]]:
    result: dict[Path, tuple[bytes, int]] = {}
    for path in AUTHORITIES:
        if not path.is_file():
            raise SystemExit(f"missing canonical authority: {path.relative_to(ROOT)}")
        result[path] = (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
    return result


def main() -> int:
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
