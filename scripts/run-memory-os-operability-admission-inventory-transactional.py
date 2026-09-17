#!/usr/bin/env python3
"""Run operability inventory generation transactionally against canonical source drift.

This runner does not create evidence. It protects the deterministic inventory from
being left partially updated when generation fails or a canonical input changes
while generation is in progress.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "contracts/operations/operability-admission-inventory.v1.json"
GENERATOR = ROOT / "scripts/generate-memory-os-operability-admission-inventory.py"

# These are the canonical JSON authorities read directly by the generator. Validator
# code has its own execution/path identity guards; this boundary protects the data
# authorities whose values determine the generated inventory.
INPUTS = tuple(
    ROOT / relative
    for relative in (
        "contracts/operations/production-operability-status.json",
        "contracts/operations/migration-production-shaped-admission-registry.v1.json",
        "contracts/operations/incident-contact-routing-admission-registry.v1.json",
        "contracts/operations/observability-stack-deployment-registry.v1.json",
        "contracts/operations/rate-limit-distributed-runtime-admission-registry.v1.json",
        "contracts/operations/load-test-scenario-contract.v1.json",
        "contracts/operations/sustained-soak-independent-review-registry.v1.json",
        "contracts/operations/production-equivalent-environment-generation-registry.v1.json",
        "contracts/operations/recovery-objectives-registry.v1.json",
        "contracts/operations/backup-restore-generation-binding-contract.v1.json",
        "contracts/operations/backup-restore-generation-evidence-registry.v1.json",
        "contracts/operations/backup-restore-non-resurrection-admission-contract.v1.json",
        "contracts/operations/backup-restore-non-resurrection-admission-registry.v1.json",
        "contracts/operations/backup-restore-drill-request-contract.v1.json",
        "contracts/operations/backup-restore-drill-request-registry.v1.json",
        "contracts/operations/backup-restore-drill-preflight-contract.v1.json",
        "contracts/operations/backup-restore-promotion-review-registry.v1.json",
        "contracts/operations/release-baseline-registry.v1.json",
        "contracts/operations/release-compatibility-pair-registry.v1.json",
        "contracts/operations/client-baseline-registry.v1.json",
        "contracts/operations/parser-artifact-registry.v1.json",
        "contracts/operations/production-shaped-failure-drill-registry.v1.json",
    )
)


@dataclass(frozen=True)
class Snapshot:
    digest: str
    mode: int


def canonical_file(path: Path, label: str) -> None:
    try:
        relative = path.relative_to(ROOT)
        resolved = path.resolve(strict=True).relative_to(ROOT.resolve())
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"canonical {label} missing or escapes repository: {path}") from exc
    if resolved != relative or not path.is_file() or path.is_symlink():
        raise SystemExit(f"canonical {label} path drift: {relative}")


def snapshot(path: Path) -> Snapshot:
    canonical_file(path, "transactional inventory authority")
    try:
        payload = path.read_bytes()
        mode = path.stat().st_mode & 0o7777
    except OSError as exc:
        raise SystemExit(f"cannot snapshot canonical authority: {path.relative_to(ROOT)}: {exc}") from exc
    return Snapshot(hashlib.sha256(payload).hexdigest(), mode)


def restore_output(payload: bytes, mode: int) -> None:
    canonical_file(OUTPUT, "inventory output")
    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{OUTPUT.name}.", suffix=".tmp", dir=OUTPUT.parent
        )
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, OUTPUT)
        temp_name = None
    except OSError as exc:
        raise SystemExit(f"cannot rollback operability inventory: {exc}") from exc
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def main() -> int:
    canonical_file(GENERATOR, "inventory generator")
    canonical_file(OUTPUT, "inventory output")
    before_inputs = {path: snapshot(path) for path in INPUTS}
    try:
        before_output = OUTPUT.read_bytes()
        before_output_mode = OUTPUT.stat().st_mode & 0o7777
    except OSError as exc:
        raise SystemExit(f"cannot snapshot inventory output: {exc}") from exc

    result = subprocess.run([sys.executable, str(GENERATOR)], cwd=ROOT, check=False)

    drift: list[str] = []
    for path, before in before_inputs.items():
        try:
            after = snapshot(path)
        except SystemExit:
            drift.append(str(path.relative_to(ROOT)))
            continue
        if after != before:
            drift.append(str(path.relative_to(ROOT)))

    if result.returncode != 0 or drift:
        restore_output(before_output, before_output_mode)
        if drift:
            raise SystemExit(
                "operability inventory source authority changed during generation: "
                + ", ".join(sorted(drift))
            )
        raise SystemExit(f"operability inventory generation failed: exit {result.returncode}")

    # A successful run must not mutate source authorities, and the output must retain
    # its pre-existing permission mode.
    if (OUTPUT.stat().st_mode & 0o7777) != before_output_mode:
        restore_output(before_output, before_output_mode)
        raise SystemExit("operability inventory output mode drift")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
