#!/usr/bin/env python3
"""Focused negatives for immutable release baseline evidence source binding."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-release-baseline-evidence-binding.py"
TRACKED_REF = "docs/evidence/releases/README.md"
UNTRACKED_REF = "docs/evidence/releases/.release-evidence-binding-negative.tmp"
SYMLINK_PARENT = ROOT / "docs/evidence/releases/.release-evidence-binding-negative-link"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("memory_os_release_evidence_binding_negative", VALIDATOR_PATH)
    require(spec is not None and spec.loader is not None, "cannot load release evidence binding validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejected(name: str, fn) -> None:
    try:
        fn()
    except Exception:
        return
    raise Fail(f"release evidence binding accepted invalid authority: {name}")


def main() -> int:
    validator = load_validator()
    head = validator.git("rev-parse", "HEAD")

    validator.validate_evidence_ref_binding(head, TRACKED_REF)

    tracked_path = ROOT / TRACKED_REF
    tracked_before = tracked_path.read_bytes()
    try:
        tracked_path.write_bytes(tracked_before + b"\n")
        expect_rejected(
            "post-source tracked evidence mutation",
            lambda: validator.validate_evidence_ref_binding(head, TRACKED_REF),
        )
    finally:
        tracked_path.write_bytes(tracked_before)

    untracked_path = ROOT / UNTRACKED_REF
    try:
        untracked_path.write_text("not source-bound\n", encoding="utf-8")
        expect_rejected(
            "post-source untracked evidence",
            lambda: validator.validate_evidence_ref_binding(head, UNTRACKED_REF),
        )
    finally:
        try:
            untracked_path.unlink()
        except FileNotFoundError:
            pass

    expect_rejected(
        "parent traversal",
        lambda: validator.validate_evidence_ref_binding(head, "docs/evidence/releases/../../../README.md"),
    )

    with tempfile.TemporaryDirectory(prefix="memory-os-release-evidence-") as temp_dir:
        outside = Path(temp_dir)
        (outside / "evidence.json").write_text("{}\n", encoding="utf-8")
        try:
            SYMLINK_PARENT.symlink_to(outside, target_is_directory=True)
            ref = str((SYMLINK_PARENT / "evidence.json").relative_to(ROOT))
            expect_rejected(
                "parent symlink repository escape",
                lambda: validator.validate_evidence_ref_binding(head, ref),
            )
        finally:
            try:
                SYMLINK_PARENT.unlink()
            except FileNotFoundError:
                pass

    require(tracked_path.read_bytes() == tracked_before,
            "negative suite failed to restore tracked evidence bytes")
    require(not untracked_path.exists(),
            "negative suite left untracked evidence behind")
    require(not SYMLINK_PARENT.exists() and not SYMLINK_PARENT.is_symlink(),
            "negative suite left symlink evidence behind")
    print("PASS: release baseline evidence refs are source-bound, repository-contained and symlink-safe")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE BASELINE EVIDENCE BINDING NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
