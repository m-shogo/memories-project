#!/usr/bin/env python3
"""Fail-closed evidence immutability negatives for distributed rate-limit runtime admission."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/register-memory-os-rate-limit-distributed-runtime.py"
EVIDENCE_REL = "contracts/operations/rate-limit-policy-contract.v1.json"
EVIDENCE = ROOT / EVIDENCE_REL
TEMP_UNTRACKED = ROOT / "docs/fixtures/memory-os-operability/.rate-limit-runtime-evidence-untracked-negative.json"
TEMP_SYMLINK = ROOT / "docs/fixtures/memory-os-operability/.rate-limit-runtime-evidence-symlink-negative.json"


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_fail(writer: Any, name: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except writer.Fail:
        return
    raise RuntimeError(f"{name}: unsafe evidence authority was accepted")


def main() -> int:
    writer = load_module(WRITER_PATH, "rate_limit_runtime_evidence_binding_negative")
    original = EVIDENCE.read_bytes()
    digest = hashlib.sha256(original).hexdigest()

    writer.validate_evidence_digest_authority([EVIDENCE_REL], {EVIDENCE_REL: digest})
    expect_fail(
        writer,
        "stale digest",
        lambda: writer.validate_evidence_digest_authority([EVIDENCE_REL], {EVIDENCE_REL: "0" * 64}),
    )

    TEMP_UNTRACKED.write_text("{}\n", encoding="utf-8")
    try:
        untracked_rel = str(TEMP_UNTRACKED.relative_to(ROOT))
        expect_fail(
            writer,
            "untracked evidence",
            lambda: writer.validate_evidence_digest_authority(
                [untracked_rel], {untracked_rel: hashlib.sha256(TEMP_UNTRACKED.read_bytes()).hexdigest()}
            ),
        )
    finally:
        TEMP_UNTRACKED.unlink(missing_ok=True)

    TEMP_SYMLINK.unlink(missing_ok=True)
    TEMP_SYMLINK.symlink_to(EVIDENCE)
    try:
        symlink_rel = str(TEMP_SYMLINK.relative_to(ROOT))
        expect_fail(
            writer,
            "symlink evidence",
            lambda: writer.validate_evidence_digest_authority([symlink_rel], {symlink_rel: digest}),
        )
    finally:
        TEMP_SYMLINK.unlink(missing_ok=True)

    try:
        EVIDENCE.write_bytes(original + b"\n")
        expect_fail(
            writer,
            "post-commit evidence mutation",
            lambda: writer.validate_evidence_digest_authority(
                [EVIDENCE_REL], {EVIDENCE_REL: hashlib.sha256(EVIDENCE.read_bytes()).hexdigest()}
            ),
        )
    finally:
        EVIDENCE.write_bytes(original)

    if EVIDENCE.read_bytes() != original:
        raise RuntimeError("canonical evidence was not restored")

    print("PASS: distributed runtime evidence refs are committed, symlink-free and digest-bound")
    print("production evidence created: false")
    print("production readiness: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
