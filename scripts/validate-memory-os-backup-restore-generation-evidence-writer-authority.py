#!/usr/bin/env python3
"""Fail closed if generation-evidence upstream writer authority is substituted."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-backup-restore-generation-evidence.py"
EXPECTED_GENERATION_WRITER = ROOT / "scripts/register-memory-os-production-equivalent-environment-generation.py"
EXPECTED_OBJECTIVES_WRITER = ROOT / "scripts/register-memory-os-recovery-objectives.py"


class Fail(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)


def load_writer() -> Any:
    require(WRITER.is_file(), "canonical generation-evidence writer missing")
    spec = importlib.util.spec_from_file_location("memory_os_generation_evidence_writer_authority", WRITER)
    require(spec is not None and spec.loader is not None, "cannot load canonical generation-evidence writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    writer = load_writer()
    generation_writer = getattr(writer, "GEN_WRITER", None)
    objectives_writer = getattr(writer, "OBJECTIVES_WRITER", None)

    require(
        generation_writer == EXPECTED_GENERATION_WRITER,
        "generation-evidence environment-generation writer authority drift",
    )
    require(
        objectives_writer == EXPECTED_OBJECTIVES_WRITER,
        "generation-evidence recovery-objectives writer authority drift",
    )
    require(callable(getattr(writer, "canonical_repo_file", None)), "canonical repository authority guard missing")
    writer.canonical_repo_file(generation_writer, "environment generation writer")
    writer.canonical_repo_file(objectives_writer, "recovery objectives writer")

    print("Memory OS generation-evidence upstream writer authority validation PASS")
    print("environment-generation writer substitution accepted: false")
    print("recovery-objectives writer substitution accepted: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"GENERATION EVIDENCE WRITER AUTHORITY VALIDATION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
