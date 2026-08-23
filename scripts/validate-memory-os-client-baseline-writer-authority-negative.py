#!/usr/bin/env python3
"""Negative coverage for the client-baseline writer CLI authority boundary."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WRITER = ROOT / "scripts/register-memory-os-client-baseline.py"


class Failure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Failure(message)


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    writer = load_module(WRITER, "memory_os_client_baseline_writer_authority_negative")
    canonical_contract = writer.CANONICAL_CONTRACT.read_bytes()
    canonical_registry = writer.CANONICAL_REGISTRY.read_bytes()

    with tempfile.TemporaryDirectory() as temp_dir:
        outside = Path(temp_dir) / "outside-authority.json"
        outside.write_text("{}\n", encoding="utf-8")
        outside_lock = Path(temp_dir) / ".client-baseline.lock"
        substitutions = (
            ("CONTRACT", outside),
            ("REGISTRY", outside),
            ("VALIDATOR", outside),
            ("LOCK", outside_lock),
        )
        for name, replacement in substitutions:
            original = getattr(writer, name)
            setattr(writer, name, replacement)
            try:
                try:
                    writer.require_actual_cli_authorities()
                except writer.Failure:
                    pass
                else:
                    raise Failure(f"client baseline writer accepted {name} authority substitution")
            finally:
                setattr(writer, name, original)

    writer.require_actual_cli_authorities()
    require(writer.CANONICAL_CONTRACT.read_bytes() == canonical_contract, "canonical client contract mutated")
    require(writer.CANONICAL_REGISTRY.read_bytes() == canonical_registry, "canonical client registry mutated")
    print("Memory OS client baseline writer authority negative suite PASS")
    print("writer CLI contract/registry/validator/lock substitution accepted: false")
    print("client baseline created: false")
    print("production evidence generated: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
