#!/usr/bin/env python3
"""Prove strict OPS-P0-007 snapshot publication rolls back bytes/mode and preserves rollback diagnostics."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "scripts/generate-memory-os-ops-p0-007-admission-snapshot.py"
SNAPSHOT = ROOT / "contracts/operations/ops-p0-007-admission-snapshot.v1.json"


class Fail(RuntimeError):
    pass


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o7777


def load_generator_module():
    spec = importlib.util.spec_from_file_location(
        "memory_os_ops_p0_007_snapshot_post_write_rollback_negative_generator",
        GENERATOR,
    )
    if spec is None or spec.loader is None:
        raise Fail("cannot load strict snapshot generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corrupt_published_snapshot() -> None:
    value = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Fail("published strict snapshot candidate was not an object")
    value["productionAuthorization"] = True
    SNAPSHOT.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def run_successful_rollback() -> None:
    snapshot_before = SNAPSHOT.read_bytes()
    original_mode = mode(SNAPSHOT)
    module = load_generator_module()
    original_replace = module.os.replace
    snapshot_replace_count = 0

    def replace_then_corrupt_once(source: str | Path, destination: str | Path) -> None:
        nonlocal snapshot_replace_count
        original_replace(source, destination)
        try:
            destination_path = Path(destination).resolve()
        except (OSError, RuntimeError):
            return
        if destination_path != SNAPSHOT.resolve():
            return
        snapshot_replace_count += 1
        if snapshot_replace_count == 1:
            # Corrupt only the just-published candidate. The generator must let the
            # canonical validator reject it, then perform a second atomic replace
            # that restores the exact previous authority.
            corrupt_published_snapshot()

    try:
        SNAPSHOT.chmod(0o640)
        module.os.replace = replace_then_corrupt_once
        try:
            module.main()
        except SystemExit as exc:
            message = str(exc)
            if "generated strict snapshot invalid" not in message:
                raise Fail(f"post-write rejection surfaced at unexpected boundary: {message}") from exc
        else:
            raise Fail("corrupted post-write strict snapshot candidate unexpectedly validated")
        finally:
            module.os.replace = original_replace

        if snapshot_replace_count != 2:
            raise Fail(f"expected candidate publication plus rollback replace, observed {snapshot_replace_count}")
        if SNAPSHOT.read_bytes() != snapshot_before:
            raise Fail("post-write validation failure did not restore exact canonical snapshot bytes")
        if mode(SNAPSHOT) != 0o640:
            raise Fail(f"post-write validation rollback changed canonical mode: {oct(mode(SNAPSHOT))}")
        leftovers = list(SNAPSHOT.parent.glob(f".{SNAPSHOT.name}.*.tmp"))
        if leftovers:
            raise Fail(f"post-write validation rollback left temporary strict snapshot files: {leftovers}")
    finally:
        module.os.replace = original_replace
        if SNAPSHOT.read_bytes() != snapshot_before:
            SNAPSHOT.write_bytes(snapshot_before)
        SNAPSHOT.chmod(original_mode)

    if SNAPSHOT.read_bytes() != snapshot_before:
        raise Fail("successful rollback case mutated canonical strict snapshot bytes")
    if mode(SNAPSHOT) != original_mode:
        raise Fail("successful rollback case did not restore original canonical strict snapshot mode")


def run_failed_rollback_preserves_primary_diagnostic() -> None:
    snapshot_before = SNAPSHOT.read_bytes()
    original_mode = mode(SNAPSHOT)
    module = load_generator_module()
    original_replace = module.os.replace
    snapshot_replace_count = 0

    def replace_corrupt_then_reject_rollback(source: str | Path, destination: str | Path) -> None:
        nonlocal snapshot_replace_count
        try:
            destination_path = Path(destination).resolve()
        except (OSError, RuntimeError):
            original_replace(source, destination)
            return
        if destination_path != SNAPSHOT.resolve():
            original_replace(source, destination)
            return
        snapshot_replace_count += 1
        if snapshot_replace_count == 1:
            original_replace(source, destination)
            corrupt_published_snapshot()
            return
        if snapshot_replace_count == 2:
            raise OSError("synthetic strict snapshot rollback replace rejection")
        raise Fail(f"unexpected strict snapshot replace attempt: {snapshot_replace_count}")

    try:
        SNAPSHOT.chmod(0o640)
        module.os.replace = replace_corrupt_then_reject_rollback
        try:
            module.main()
        except SystemExit as exc:
            message = str(exc)
            required = (
                "generated strict snapshot invalid",
                "rollback incomplete",
                "synthetic strict snapshot rollback replace rejection",
            )
            missing = [fragment for fragment in required if fragment not in message]
            if missing:
                raise Fail(
                    "rollback failure did not preserve primary plus rollback diagnostics; "
                    f"missing={missing}: {message}"
                ) from exc
        else:
            raise Fail("synthetic rollback replace failure unexpectedly accepted")
        finally:
            module.os.replace = original_replace

        if snapshot_replace_count != 2:
            raise Fail(f"expected candidate publication plus rejected rollback replace, observed {snapshot_replace_count}")
        if mode(SNAPSHOT) != 0o640:
            raise Fail(f"failed rollback changed canonical snapshot mode before cleanup: {oct(mode(SNAPSHOT))}")
        leftovers = list(SNAPSHOT.parent.glob(f".{SNAPSHOT.name}.*.tmp"))
        if leftovers:
            raise Fail(f"failed rollback left temporary strict snapshot files: {leftovers}")
    finally:
        module.os.replace = original_replace
        SNAPSHOT.write_bytes(snapshot_before)
        SNAPSHOT.chmod(original_mode)

    if SNAPSHOT.read_bytes() != snapshot_before:
        raise Fail("failed rollback negative cleanup did not restore canonical strict snapshot bytes")
    if mode(SNAPSHOT) != original_mode:
        raise Fail("failed rollback negative cleanup did not restore canonical strict snapshot mode")


def main() -> int:
    run_successful_rollback()
    run_failed_rollback_preserves_primary_diagnostic()

    print("Memory OS OPS-P0-007 strict snapshot post-write rollback negative PASS")
    print("canonical post-write validator rejection exercised after candidate publication: true")
    print("exact snapshot bytes restored after successful validation rollback: true")
    print("canonical 0640 mode preserved across candidate publication and rollback: true")
    print("rollback writer failure preserves primary validation diagnostic: true")
    print("rollback writer failure is surfaced as rollback incomplete: true")
    print("temporary snapshot authority residue after rollback attempts: false")
    print("negative cleanup restores canonical strict snapshot bytes/mode: true")
    print("production evidence/readiness/promotion created: false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (Fail, json.JSONDecodeError, OSError) as exc:
        print(f"OPS-P0-007 SNAPSHOT POST-WRITE ROLLBACK NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
