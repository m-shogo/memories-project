#!/usr/bin/env python3
"""Negative coverage for coherent recovery-set repository authority containment."""

from __future__ import annotations

import importlib.util
import shutil
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-local-coherent-recovery-set.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_local_coherent_recovery_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load coherent recovery validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_fail(call: Callable[[], object], needle: str) -> None:
    try:
        call()
    except Exception as exc:  # validator Fail is loaded dynamically
        if needle not in str(exc):
            raise AssertionError(f"unexpected rejection: {exc}") from exc
        return
    raise AssertionError(f"expected rejection containing {needle!r}")


def main() -> int:
    validator = load_validator()
    result_path: Path = validator.RESULT_PATH
    original_exists = result_path.exists() or result_path.is_symlink()
    original_bytes = result_path.read_bytes() if result_path.is_file() and not result_path.is_symlink() else None

    temp_root = Path(tempfile.mkdtemp(prefix="memory-os-coherent-authority-negative-"))
    external_result = temp_root / "result.json"
    external_result.write_bytes(original_bytes if original_bytes is not None else b"{}\n")
    parent_link = ROOT / "docs/fixtures/memory-os-operability/.coherent-parent-symlink-negative"
    external_parent = temp_root / "parent"
    external_parent.mkdir()
    (external_parent / "evidence.json").write_text("{}\n", encoding="utf-8")

    try:
        if result_path.exists() or result_path.is_symlink():
            result_path.unlink()
        result_path.symlink_to(external_result)
        expect_fail(validator.main, "symlink component")

        parent_link.symlink_to(external_parent, target_is_directory=True)
        expect_fail(
            lambda: validator.require_repo_regular_file(
                parent_link / "evidence.json", "synthetic parent-symlink authority"
            ),
            "symlink component",
        )
    finally:
        if result_path.exists() or result_path.is_symlink():
            result_path.unlink()
        if original_exists and original_bytes is not None:
            result_path.write_bytes(original_bytes)
        if parent_link.exists() or parent_link.is_symlink():
            parent_link.unlink()
        shutil.rmtree(temp_root, ignore_errors=True)

    print("PASS: coherent recovery authorities reject symlink aliases and parent escapes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
