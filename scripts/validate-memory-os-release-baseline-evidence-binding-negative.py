#!/usr/bin/env python3
"""Focused negatives for immutable release baseline evidence source binding."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-release-baseline-evidence-binding.py"
TRACKED_REF = "docs/evidence/releases/README.md"
UNTRACKED_REF = "docs/evidence/releases/.release-evidence-binding-negative.tmp"


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

    require(tracked_path.read_bytes() == tracked_before,
            "negative suite failed to restore tracked evidence bytes")
    require(not untracked_path.exists(),
            "negative suite left untracked evidence behind")
    print("PASS: release baseline evidence refs are source-bound and immutable")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"RELEASE BASELINE EVIDENCE BINDING NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
