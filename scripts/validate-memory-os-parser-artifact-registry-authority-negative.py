#!/usr/bin/env python3
"""Prove parser artifact append rejects corrupt registry aggregate authority."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
WRITER_PATH = ROOT / "scripts/register-memory-os-parser-artifact.py"
REGISTRY_PATH = ROOT / "contracts/operations/parser-artifact-registry.v1.json"


class NegativeFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NegativeFailure(message)


def load_writer() -> Any:
    spec = importlib.util.spec_from_file_location(
        "parser_artifact_writer_registry_negative", WRITER_PATH
    )
    require(spec is not None and spec.loader is not None, "cannot load parser writer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_rejection(writer: Any, base: dict[str, Any], label: str,
                     mutate: Callable[[dict[str, Any]], None]) -> None:
    candidate = copy.deepcopy(base)
    mutate(candidate)
    try:
        writer.validate_registry_for_append(candidate)
    except writer.RegistrationFailure:
        return
    raise NegativeFailure(f"writer accepted corrupt parser registry: {label}")


def main() -> int:
    writer = load_writer()
    base = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    require(isinstance(base, dict), "parser registry must be object")
    writer.validate_registry_for_append(copy.deepcopy(base))

    cases: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
        ("boolean reviewed count", lambda value: value.__setitem__("reviewedArtifactCount", True)),
        ("reviewed count drift", lambda value: value.__setitem__("reviewedArtifactCount", 1)),
        ("retained count drift", lambda value: value.__setitem__("retainedRollbackArtifactCount", 1)),
        ("replay count drift", lambda value: value.__setitem__("replayProvenArtifactCount", 1)),
        ("appendOnly false", lambda value: value.__setitem__("appendOnly", False)),
        ("production evidence promotion", lambda value: value.__setitem__("productionEvidence", True)),
        ("latest pointer drift", lambda value: value.__setitem__("latestReviewedArtifactId", "par_fake0000")),
        ("unknown registry field", lambda value: value.__setitem__("unexpectedAuthority", True)),
    )
    for label, mutate in cases:
        expect_rejection(writer, base, label, mutate)

    print("Parser artifact registry authority negative PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except NegativeFailure as exc:
        print(f"PARSER ARTIFACT REGISTRY AUTHORITY NEGATIVE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
