#!/usr/bin/env python3
"""Negative coverage for local object restore repository authority containment."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts/validate-memory-os-local-object-version-restore.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_local_object_restore_validator", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load object restore validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expect_fail(call: Callable[[], object], needle: str) -> None:
    try:
        call()
    except Exception as exc:  # validator failure type is dynamically loaded
        if needle not in str(exc):
            raise AssertionError(f"unexpected rejection: {exc}") from exc
        return
    raise AssertionError(f"expected rejection containing {needle!r}")


def create_side_commit() -> str:
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, text=True).strip()
    return subprocess.check_output(
        ["git", "-c", "user.name=memory-os-negative", "-c", "user.email=memory-os-negative@example.invalid",
         "commit-tree", tree, "-m", "synthetic detached object restore source"],
        cwd=ROOT,
        text=True,
    ).strip()


def main() -> int:
    validator = load_validator()
    result_path: Path = validator.RESULT_PATH
    original_exists = result_path.exists() or result_path.is_symlink()
    original_bytes = result_path.read_bytes() if result_path.is_file() and not result_path.is_symlink() else None

    temp_root = Path(tempfile.mkdtemp(prefix="memory-os-object-authority-negative-"))
    external_result = temp_root / "result.json"
    external_result.write_bytes(original_bytes if original_bytes is not None else b"{}\n")
    parent_link = ROOT / "docs/fixtures/memory-os-operability/.object-parent-symlink-negative"
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

        side_commit = create_side_commit()
        if original_bytes is not None:
            result_path.unlink(missing_ok=True)
            result_path.write_bytes(original_bytes)
            result = validator.load(result_path)
            result["commitSha"] = side_commit
            expect_fail(lambda: validator.validate_result(result, None), "not an ancestor")
    finally:
        if result_path.exists() or result_path.is_symlink():
            result_path.unlink()
        if original_exists and original_bytes is not None:
            result_path.write_bytes(original_bytes)
        if parent_link.exists() or parent_link.is_symlink():
            parent_link.unlink()
        shutil.rmtree(temp_root, ignore_errors=True)

    print("PASS: object restore authorities reject symlink escapes and detached source commits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
