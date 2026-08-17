#!/usr/bin/env python3
"""Negative checks for admission authority path containment."""

from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-admission-authority-linkage.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("admission_authority_linkage_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load admission authority linkage validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_entry_fail(module, value: str, *, directory: bool, contains: str) -> None:
    try:
        module.repository_entry(value, "negative.fixture", directory=directory)
    except module.Fail as exc:
        if contains not in str(exc):
            raise AssertionError(f"unexpected failure for {value}: {exc}") from exc
    else:
        raise AssertionError(f"unsafe authority path unexpectedly accepted: {value}")


def expect_slot_fail(module, value: str, *, contains: str) -> None:
    try:
        module.repository_file_slot(value, "negative.appendLockPath")
    except module.Fail as exc:
        if contains not in str(exc):
            raise AssertionError(f"unexpected slot failure for {value}: {exc}") from exc
    else:
        raise AssertionError(f"unsafe authority file slot unexpectedly accepted: {value}")


def main() -> int:
    module = load_validator()
    fixture = ROOT / f".tmp-admission-authority-linkage-negative-{os.getpid()}"
    external_root = Path(tempfile.mkdtemp(prefix="memory-os-linkage-negative-"))
    try:
        fixture.mkdir(parents=True, exist_ok=False)
        normal = fixture / "normal.txt"
        normal.write_text("safe\n", encoding="utf-8")
        module.repository_entry(str(normal.relative_to(ROOT)), "negative.normal", directory=False)
        module.repository_file_slot(str((fixture / ".safe.lock").relative_to(ROOT)), "negative.safeLock")

        final_link = fixture / "final-link.txt"
        final_link.symlink_to(normal.name)
        expect_entry_fail(
            module,
            str(final_link.relative_to(ROOT)),
            directory=False,
            contains="symlinked admission authority path",
        )

        external_file = external_root / "payload.txt"
        external_file.write_text("outside\n", encoding="utf-8")
        parent_link = fixture / "external"
        parent_link.symlink_to(external_root, target_is_directory=True)
        expect_entry_fail(
            module,
            str((parent_link / external_file.name).relative_to(ROOT)),
            directory=False,
            contains="symlinked admission authority path",
        )
        expect_slot_fail(
            module,
            str((parent_link / ".escaped.lock").relative_to(ROOT)),
            contains="symlinked admission authority path",
        )

        external_dir = external_root / "directory"
        external_dir.mkdir()
        directory_link = fixture / "external-directory"
        directory_link.symlink_to(external_dir, target_is_directory=True)
        expect_entry_fail(
            module,
            str(directory_link.relative_to(ROOT)),
            directory=True,
            contains="symlinked admission authority path",
        )

        expect_slot_fail(module, "../outside.lock", contains="unsafe linked path")

        lock_target = fixture / "real.lock"
        lock_target.write_text("lock\n", encoding="utf-8")
        lock_link = fixture / "alias.lock"
        lock_link.symlink_to(lock_target.name)
        expect_slot_fail(
            module,
            str(lock_link.relative_to(ROOT)),
            contains="symlinked admission authority file slot",
        )

        print("PASS: admission authority symlink, repository-escape and append-lock paths are rejected")
        return 0
    finally:
        shutil.rmtree(fixture, ignore_errors=True)
        shutil.rmtree(external_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
