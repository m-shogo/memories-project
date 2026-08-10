#!/usr/bin/env python3
"""Reject non-canonical or repository-escaping typed admission authority refs."""
from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"

class Fail(RuntimeError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise Fail(message)

def load_validator():
    spec = importlib.util.spec_from_file_location("memory_os_non_resurrection_admission_path_negative", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load typed admission validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def expect_rejected(module: Any, name: str, action: Callable[[], Any]) -> None:
    try:
        action()
    except module.Fail:
        print(f"PASS reject: {name}")
        return
    raise Fail(f"negative case unexpectedly accepted: {name}")

def main() -> int:
    validator = load_validator()
    canonical = "scripts/validate-memory-os-backup-restore-non-resurrection-admission.py"
    accepted = validator.canonical_repo_file_ref(canonical, "negative.canonical")
    require(accepted == ROOT / canonical, "canonical in-repository authority ref did not resolve exactly")
    print("PASS accept: canonical repository-relative authority ref")

    expect_rejected(validator, "absolute in-repository authority ref", lambda: validator.canonical_repo_file_ref(str(ROOT / canonical), "negative.absolute"))
    expect_rejected(validator, "parent traversal authority ref", lambda: validator.canonical_repo_file_ref("scripts/../scripts/validate-memory-os-backup-restore-non-resurrection-admission.py", "negative.parent"))

    with tempfile.TemporaryDirectory(prefix="memory-os-non-resurrection-path-negative-") as tmp:
        outside = Path(tmp) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        link = ROOT / "docs/fixtures/memory-os-operability/.non-resurrection-path-negative-link.json"
        require(not link.exists() and not link.is_symlink(), "temporary negative symlink path already exists")
        try:
            link.symlink_to(outside)
            ref = link.relative_to(ROOT).as_posix()
            expect_rejected(validator, "repo-local symlink escaping repository", lambda: validator.canonical_repo_file_ref(ref, "negative.symlink"))
        finally:
            link.unlink(missing_ok=True)

    print("Memory OS backup/restore non-resurrection contract path negative suite PASS")
    print("absolute authority aliases accepted: false")
    print("parent traversal authority aliases accepted: false")
    print("repository-escaping authority symlinks accepted: false")
    print("canonical authorities mutated: false")
    print("production evidence: false")
    print("production decision: NO_GO")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Fail as exc:
        print(f"BACKUP RESTORE NON-RESURRECTION CONTRACT PATH NEGATIVE FAILED: {exc}")
        raise SystemExit(1)
